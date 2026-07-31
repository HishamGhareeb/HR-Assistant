"""Onyx ingestion adapter: push/retract documents so the Frappe -> Onyx
sync (glue/frappe_sync.py) has somewhere to write. This is a separate
client from glue/onyx_client.py (retrieval) because Onyx models "search
for documents" and "push documents into the index" as two entirely
different APIs, both pinned against the same Onyx **v4.4.7** tag used in
docs/ONYX_ADAPTER.md:

- backend/onyx/server/onyx_api/ingestion.py -- route definitions
- backend/onyx/server/onyx_api/models.py -- `IngestionDocument` / `IngestionResult`
- backend/onyx/connectors/models.py -- `DocumentBase`, `TextSection`, `DocumentSource`

## Endpoints

    POST   {ONYX_API_URL}/onyx-api/ingestion
    DELETE {ONYX_API_URL}/onyx-api/ingestion/{document_id}
    Authorization: Bearer <ONYX_API_KEY>   (curator/admin role, same as onyx_client.py)

Upsert body:

    {"document": {"id": "<document_id>", "source": "ingestion_api",
                   "semantic_identifier": "...",
                   "sections": [{"type": "text", "text": "..."}],
                   "metadata": {"tenant_id": "...", "record_type": "..."}}}

`cc_pair_id` is deliberately omitted so Onyx falls back to its default
ingestion connector-credential pair -- provisioning a *non-default* one is
an Onyx-admin operational step out of scope here.

`metadata` carries the same `tenant_id` / `record_type` keys that
`glue/onyx_client.py` requires on the way back out, so a document indexed
by this client is guaranteed retrievable and taggable by that one -- see
`docs/FRAPPE_SYNC.md`.

## Known gap

Not yet exercised against a live Onyx instance -- same caveat as
`glue/onyx_client.py`. Re-verify alongside it.
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

ONYX_PINNED_VERSION = "v4.4.7"
DEFAULT_TIMEOUT_SECONDS = 10.0


class OnyxIndexerError(RuntimeError):
    """Onyx was unreachable, timed out, or rejected an ingestion request."""


class OnyxIndexer:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_url or not api_url.strip():
            raise ValueError("api_url must not be blank")
        if not api_key or not api_key.strip():
            raise ValueError("api_key must not be blank -- the ingestion endpoint requires one")
        self._api_url = api_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def upsert(
        self,
        *,
        document_id: str,
        semantic_identifier: str,
        text: str,
        metadata: dict[str, str],
    ) -> bool:
        """Create or update a document. Returns True if it already existed
        (an update), False if this created it -- mirrors Onyx's own
        `IngestionResult.already_existed`."""
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        if not text.strip():
            raise ValueError("text must not be blank")

        payload = {
            "document": {
                "id": document_id,
                "source": "ingestion_api",
                "semantic_identifier": semantic_identifier,
                "sections": [{"type": "text", "text": text}],
                "metadata": metadata,
            }
        }

        async with httpx.AsyncClient(timeout=self._timeout_seconds, transport=self._transport) as client:
            try:
                response = await client.post(
                    f"{self._api_url}/onyx-api/ingestion", headers=self._headers, json=payload
                )
            except httpx.TimeoutException as exc:
                raise OnyxIndexerError(f"Onyx ingestion timed out after {self._timeout_seconds}s") from exc
            except httpx.HTTPError as exc:
                raise OnyxIndexerError(f"Onyx ingestion request failed: {exc}") from exc

        if response.status_code != 200:
            raise OnyxIndexerError(
                f"Onyx ingestion returned HTTP {response.status_code}: {response.text[:500]}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise OnyxIndexerError(f"Onyx ingestion response was not valid JSON: {exc}") from exc

        if "already_existed" not in body:
            raise OnyxIndexerError(
                f"Onyx ingestion response did not match the expected contract: {body!r}"
            )
        return bool(body["already_existed"])

    async def delete(self, document_id: str) -> None:
        """Retract a document. Idempotent: deleting a document that's
        already gone (Onyx returns 404) is treated as success, not an
        error -- a retry after a partial sync failure must not blow up on
        a delete it already completed."""
        if not document_id.strip():
            raise ValueError("document_id must not be blank")

        async with httpx.AsyncClient(timeout=self._timeout_seconds, transport=self._transport) as client:
            try:
                response = await client.delete(
                    f"{self._api_url}/onyx-api/ingestion/{document_id}", headers=self._headers
                )
            except httpx.TimeoutException as exc:
                raise OnyxIndexerError(f"Onyx delete timed out after {self._timeout_seconds}s") from exc
            except httpx.HTTPError as exc:
                raise OnyxIndexerError(f"Onyx delete request failed: {exc}") from exc

        if response.status_code == 404:
            return
        if response.status_code not in (200, 204):
            raise OnyxIndexerError(
                f"Onyx delete returned HTTP {response.status_code}: {response.text[:500]}"
            )
