"""Unit + repeatable contract tests for the Onyx adapter.

The contract tests never touch a live Onyx instance -- they replay fixture
responses shaped exactly like the pinned v4.4.7 admin search API (see
glue/onyx_client.py's module docstring) through httpx.MockTransport, so
they're deterministic and don't need network access or a running service.
"""
from __future__ import annotations

import json

import httpx
import pytest

from glue.domain import DocumentClassification
from glue.onyx_client import OnyxAdapterError, OnyxClient


def build_client(handler, **kwargs) -> OnyxClient:
    """Build a client wired to a fixture HTTP handler via httpx's own
    MockTransport, so tests exercise the real request/response handling
    code path (auth header, URL, error mapping) with no network access."""
    return OnyxClient(
        api_url="https://onyx.internal",
        api_key="onyx_test_key",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def search_doc(
    document_id="doc-1",
    record_type="leave_record",
    tenant_id="acme",
    blurb="Sarah has 5 days of leave.",
    classification="internal",
):
    return {
        "document_id": document_id,
        "chunk_ind": 0,
        "semantic_identifier": document_id,
        "blurb": blurb,
        "source_type": "file",
        "boost": 0,
        "hidden": False,
        "metadata": {"tenant_id": tenant_id, "record_type": record_type, "classification": classification},
        "match_highlights": [],
        "updated_at": "2026-01-01T00:00:00Z",
    }


# --- request shape --------------------------------------------------------


@pytest.mark.asyncio
async def test_sends_bearer_auth_and_query():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"documents": []})

    client = build_client(handler)
    await client.search("how much leave do I have?")

    assert captured["auth"] == "Bearer onyx_test_key"
    assert captured["body"]["query"] == "how much leave do I have?"
    assert "filters" not in captured["body"]


@pytest.mark.asyncio
async def test_tenant_id_adds_document_set_filter():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"documents": []})

    client = build_client(handler)
    await client.search("question", tenant_id="acme")

    assert captured["body"]["filters"]["document_set"] == ["tenant:acme"]
    assert captured["body"]["filters"]["metadata"]["tenant_id"] == ["acme"]


@pytest.mark.asyncio
async def test_allowed_classifications_are_sent_as_metadata_filter():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"documents": []})

    client = build_client(handler)
    await client.search(
        "question",
        tenant_id="acme",
        allowed_classifications=[DocumentClassification.PUBLIC, DocumentClassification.INTERNAL],
    )

    assert captured["body"]["filters"]["metadata"] == {
        "tenant_id": ["acme"],
        "classification": ["public", "internal"],
    }


@pytest.mark.asyncio
async def test_blank_tenant_id_is_rejected():
    client = build_client(lambda request: httpx.Response(200, json={"documents": []}))
    with pytest.raises(ValueError):
        await client.search("question", tenant_id="   ")


def test_constructor_rejects_blank_api_key():
    with pytest.raises(ValueError):
        OnyxClient(api_url="https://onyx.internal", api_key="")


def test_constructor_rejects_blank_api_url():
    with pytest.raises(ValueError):
        OnyxClient(api_url="  ", api_key="key")


# --- response mapping ------------------------------------------------------


@pytest.mark.asyncio
async def test_maps_canonical_document_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"documents": [search_doc()]})

    client = build_client(handler)
    documents = await client.search("question", tenant_id="acme")

    assert len(documents) == 1
    doc = documents[0]
    assert doc.object_type == "leave_record"
    assert doc.object_id == "doc-1"
    assert doc.chunk == "Sarah has 5 days of leave."
    assert doc.tenant_id == "acme"
    assert doc.source == "onyx"
    assert doc.retrieved_at is not None
    assert doc.classification is DocumentClassification.INTERNAL


@pytest.mark.asyncio
async def test_document_round_trips_to_canonical_contract():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"documents": [search_doc()]})

    client = build_client(handler)
    [doc] = await client.search("question", tenant_id="acme")
    canonical = doc.to_canonical()

    assert canonical.tenant_id == "acme"
    assert canonical.object_id == "doc-1"


@pytest.mark.asyncio
async def test_drops_document_missing_tenant_metadata():
    raw = search_doc()
    del raw["metadata"]["tenant_id"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"documents": [raw]})

    client = build_client(handler)
    documents = await client.search("question")
    assert documents == []


@pytest.mark.asyncio
async def test_drops_document_with_unknown_record_type():
    raw = search_doc(record_type="not_a_real_type")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"documents": [raw]})

    client = build_client(handler)
    documents = await client.search("question")
    assert documents == []


@pytest.mark.asyncio
async def test_drops_document_missing_classification_metadata():
    raw = search_doc()
    del raw["metadata"]["classification"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"documents": [raw]})

    client = build_client(handler)
    documents = await client.search("question", tenant_id="acme")
    assert documents == []


@pytest.mark.asyncio
async def test_drops_document_outside_allowed_classification_mask():
    raw = search_doc(classification="hr_only")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"documents": [raw]})

    client = build_client(handler)
    documents = await client.search(
        "question",
        tenant_id="acme",
        allowed_classifications=[DocumentClassification.PUBLIC, DocumentClassification.INTERNAL],
    )
    assert documents == []


@pytest.mark.asyncio
async def test_drops_document_from_a_different_tenant():
    raw = search_doc(tenant_id="globex")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"documents": [raw]})

    client = build_client(handler)
    documents = await client.search("question", tenant_id="acme")
    assert documents == []


@pytest.mark.asyncio
async def test_drops_document_with_blank_blurb():
    raw = search_doc(blurb="   ")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"documents": [raw]})

    client = build_client(handler)
    documents = await client.search("question")
    assert documents == []


@pytest.mark.asyncio
async def test_one_bad_document_does_not_drop_good_ones():
    good = search_doc(document_id="doc-good")
    bad = search_doc(document_id="doc-bad", record_type="garbage")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"documents": [good, bad]})

    client = build_client(handler)
    documents = await client.search("question")
    assert [d.object_id for d in documents] == ["doc-good"]


@pytest.mark.asyncio
async def test_results_are_bounded_by_max_results():
    docs = [search_doc(document_id=f"doc-{i}") for i in range(10)]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"documents": docs})

    client = build_client(handler, max_results=3)
    documents = await client.search("question")
    assert len(documents) == 3


# --- transport / contract failures -----------------------------------------


@pytest.mark.asyncio
async def test_non_200_response_raises_adapter_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    client = build_client(handler)
    with pytest.raises(OnyxAdapterError):
        await client.search("question")


@pytest.mark.asyncio
async def test_malformed_response_body_raises_adapter_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    client = build_client(handler)
    with pytest.raises(OnyxAdapterError):
        await client.search("question")


@pytest.mark.asyncio
async def test_transport_error_raises_adapter_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = build_client(handler)
    with pytest.raises(OnyxAdapterError):
        await client.search("question")
