"""Onyx retrieval adapter.

Talks to a self-hosted Onyx (https://github.com/onyx-dot-app/onyx) instance's
admin search API. The endpoint, auth scheme, and response shape below are
pinned against Onyx tag **v4.4.7** (verified by reading
``backend/onyx/server/query_and_chat/query_backend.py`` and
``.../models.py`` at that tag) -- see ``docs/ONYX_ADAPTER.md`` for the full
rationale and the one open gap: this has not yet been exercised against a
live running Onyx instance, so the mapping is contract-correct but
integration-unconfirmed until Stage 1 brings one up.

## Endpoint

    POST {ONYX_API_URL}/admin/search
    Authorization: Bearer <ONYX_API_KEY>
    {"query": "<question text>", "filters": {"document_set": ["tenant:<id>"]}}

This requires an API key belonging to a curator or admin role -- Onyx's
plain per-user search API only offers full chat/answer generation (which we
don't want; Claude does the answering), not retrieval-only search. Using the
admin endpoint scoped to a tenant-specific document set is intentional
defense-in-depth, not the authorization boundary: OpenFGA remains the actual
per-user authorization gate downstream of this client (see
``docs/ARCHITECTURE.md`` trust boundary #2). This adapter never makes an
authorization decision -- at most it narrows retrieval to one tenant's
document set when it's told which tenant is asking.

## Response

    {"documents": [{"document_id": str, "semantic_identifier": str,
                     "blurb": str, "source_type": str,
                     "updated_at": "<ISO 8601>" | null,
                     "metadata": {...}, ...}]}

``metadata`` must carry ``tenant_id`` and ``record_type`` (one of
``glue.domain.DocumentType``) for every ingested document -- that tagging is
the responsibility of the Frappe -> Onyx sync. A document missing either
field, carrying an unrecognized ``record_type``, or (when the caller passed
a ``tenant_id``) tagged with a different tenant, is dropped rather than
guessed at: see ``glue.domain`` on why there is no such thing as
tenant-less document identity.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel, ValidationError

from .domain import Citation, Document as CanonicalDocument, DocumentType

logger = logging.getLogger(__name__)

ONYX_PINNED_VERSION = "v4.4.7"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RESULTS = 25


class OnyxAdapterError(RuntimeError):
    """Onyx was unreachable, timed out, or returned a response that doesn't
    match the pinned response contract at all (as opposed to a single
    malformed document, which is dropped rather than raised)."""


@dataclass
class Document:
    """Retrieval result handed to the pipeline / OpenFGA filter.

    Kept as the existing lightweight shape (object_type/object_id/chunk)
    that callers already depend on, with canonical metadata added as
    optional fields so this stays a strict superset -- existing 3-positional-
    argument construction (as in tests/test_pipeline.py) keeps working.
    Call `.to_canonical()` to get the fully-validated `glue.domain.Document`
    contract once a caller is ready to require it (tracked for the
    authentication/tenant-isolation work).
    """

    object_type: str
    object_id: str
    chunk: str
    tenant_id: str | None = None
    source: str = "onyx"
    retrieved_at: datetime | None = None

    def to_canonical(self) -> CanonicalDocument:
        if self.tenant_id is None or self.retrieved_at is None:
            raise ValueError("tenant_id and retrieved_at are required to build a canonical Document")
        citation = Citation(
            source=self.source,
            object_type=DocumentType(self.object_type),
            object_id=self.object_id,
            tenant_id=self.tenant_id,
            retrieved_at=self.retrieved_at,
        )
        return CanonicalDocument(citation=citation, chunk=self.chunk)


class _SearchDocResponse(BaseModel):
    document_id: str
    semantic_identifier: str
    blurb: str
    source_type: str
    metadata: dict[str, str | list[str]] = {}
    updated_at: str | None = None


class _AdminSearchResponse(BaseModel):
    documents: list[_SearchDocResponse]


class OnyxClient:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_results: int = DEFAULT_MAX_RESULTS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_url or not api_url.strip():
            raise ValueError("api_url must not be blank")
        if not api_key or not api_key.strip():
            raise ValueError("api_key must not be blank -- the admin search endpoint requires one")
        self._api_url = api_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._timeout_seconds = timeout_seconds
        self._max_results = max_results
        # Overridable so contract tests can replay fixture responses through
        # httpx.MockTransport instead of opening a real connection, while
        # exercising the exact same request/response handling code path.
        self._transport = transport

    async def search(
        self,
        question: str,
        *,
        tenant_id: str | None = None,
    ) -> list[Document]:
        """Retrieve candidate documents for `question`.

        When `tenant_id` is given, the Onyx query itself is scoped to that
        tenant's document set (`document_set: ["tenant:<id>"]`) and any
        returned document tagged with a *different* tenant is dropped as a
        defense-in-depth check against a misconfigured index. `tenant_id`
        is optional only because it isn't threaded through the pipeline's
        caller yet; every returned `Document` still carries its own
        `tenant_id` from the response, and any document with no tenant tag
        at all is always dropped, never defaulted.
        """
        payload: dict = {"query": question}
        if tenant_id is not None:
            if not tenant_id.strip():
                raise ValueError("tenant_id must not be blank when provided")
            payload["filters"] = {"document_set": [f"tenant:{tenant_id.strip()}"]}

        parsed = await self._post_search(payload)

        documents: list[Document] = []
        skipped = 0
        for raw in parsed.documents[: self._max_results]:
            document = self._to_document(raw, expected_tenant_id=tenant_id)
            if document is None:
                skipped += 1
                continue
            documents.append(document)

        if skipped:
            logger.warning(
                "onyx_search_dropped_documents tenant_id=%s skipped=%d kept=%d",
                tenant_id,
                skipped,
                len(documents),
            )
        return documents

    async def _post_search(self, payload: dict) -> _AdminSearchResponse:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, transport=self._transport
            ) as client:
                response = await client.post(
                    f"{self._api_url}/admin/search",
                    headers=self._headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise OnyxAdapterError(f"Onyx search timed out after {self._timeout_seconds}s") from exc
        except httpx.HTTPError as exc:
            raise OnyxAdapterError(f"Onyx search request failed: {exc}") from exc

        if response.status_code != 200:
            raise OnyxAdapterError(
                f"Onyx search returned HTTP {response.status_code}: {response.text[:500]}"
            )

        try:
            return _AdminSearchResponse.model_validate_json(response.content)
        except ValidationError as exc:
            raise OnyxAdapterError(
                f"Onyx search response did not match the expected contract: {exc}"
            ) from exc

    def _to_document(self, raw: _SearchDocResponse, expected_tenant_id: str | None) -> Document | None:
        doc_tenant = raw.metadata.get("tenant_id")
        if not isinstance(doc_tenant, str) or not doc_tenant.strip():
            return None
        doc_tenant = doc_tenant.strip()
        if expected_tenant_id is not None and doc_tenant != expected_tenant_id:
            return None

        record_type = raw.metadata.get("record_type")
        if not isinstance(record_type, str):
            return None
        try:
            object_type = DocumentType(record_type)
        except ValueError:
            return None

        if not raw.blurb.strip():
            return None

        return Document(
            object_type=object_type.value,
            object_id=raw.document_id,
            chunk=raw.blurb,
            tenant_id=doc_tenant,
            source="onyx",
            retrieved_at=_parse_timestamp(raw.updated_at),
        )


def _parse_timestamp(value: str | None) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)
