from __future__ import annotations

import json

import httpx
import pytest

from glue.onyx_indexer import OnyxIndexer, OnyxIndexerError


def build_indexer(handler, **kwargs) -> OnyxIndexer:
    return OnyxIndexer(
        api_url="https://onyx.internal",
        api_key="onyx_test_key",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_upsert_sends_expected_payload_and_auth():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"document_id": "doc-1", "already_existed": False})

    indexer = build_indexer(handler)
    already_existed = await indexer.upsert(
        document_id="doc-1",
        semantic_identifier="Leave application: LA-1",
        text="Annual leave application, status: approved.",
        metadata={"tenant_id": "acme", "record_type": "leave_record"},
    )

    assert already_existed is False
    assert captured["method"] == "POST"
    assert captured["url"] == "https://onyx.internal/onyx-api/ingestion"
    assert captured["auth"] == "Bearer onyx_test_key"
    body = captured["body"]["document"]
    assert body["id"] == "doc-1"
    assert body["source"] == "ingestion_api"
    assert body["sections"] == [{"type": "text", "text": "Annual leave application, status: approved."}]
    assert body["metadata"] == {"tenant_id": "acme", "record_type": "leave_record"}


@pytest.mark.asyncio
async def test_upsert_reports_already_existed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"document_id": "doc-1", "already_existed": True})

    indexer = build_indexer(handler)
    already_existed = await indexer.upsert(
        document_id="doc-1", semantic_identifier="x", text="text", metadata={}
    )
    assert already_existed is True


@pytest.mark.asyncio
async def test_upsert_rejects_blank_text():
    indexer = build_indexer(lambda request: httpx.Response(200, json={"already_existed": False}))
    with pytest.raises(ValueError):
        await indexer.upsert(document_id="doc-1", semantic_identifier="x", text="   ", metadata={})


@pytest.mark.asyncio
async def test_upsert_non_200_raises_indexer_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    indexer = build_indexer(handler)
    with pytest.raises(OnyxIndexerError):
        await indexer.upsert(document_id="doc-1", semantic_identifier="x", text="text", metadata={})


@pytest.mark.asyncio
async def test_upsert_malformed_response_raises_indexer_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    indexer = build_indexer(handler)
    with pytest.raises(OnyxIndexerError):
        await indexer.upsert(document_id="doc-1", semantic_identifier="x", text="text", metadata={})


@pytest.mark.asyncio
async def test_delete_sends_expected_request():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        return httpx.Response(204)

    indexer = build_indexer(handler)
    await indexer.delete("doc-1")

    assert captured["method"] == "DELETE"
    assert captured["url"] == "https://onyx.internal/onyx-api/ingestion/doc-1"


@pytest.mark.asyncio
async def test_delete_treats_404_as_success():
    indexer = build_indexer(lambda request: httpx.Response(404))
    await indexer.delete("doc-1")  # must not raise


@pytest.mark.asyncio
async def test_delete_non_404_error_raises_indexer_error():
    indexer = build_indexer(lambda request: httpx.Response(500, text="boom"))
    with pytest.raises(OnyxIndexerError):
        await indexer.delete("doc-1")


@pytest.mark.asyncio
async def test_transport_failure_raises_indexer_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    indexer = build_indexer(handler)
    with pytest.raises(OnyxIndexerError):
        await indexer.upsert(document_id="doc-1", semantic_identifier="x", text="text", metadata={})


def test_constructor_rejects_blank_api_key():
    with pytest.raises(ValueError):
        OnyxIndexer(api_url="https://onyx.internal", api_key="")
