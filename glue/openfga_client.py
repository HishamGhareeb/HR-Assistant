"""OpenFGA authorization filtering: given a user and a list of candidate
documents, keep only the ones the user is an authorized viewer of. This is
the actual access-control enforcement point -- nothing downstream of this
should be trusted to re-derive permissions.

## Tenant scoping

OpenFGA object identifiers here are namespaced by tenant:
``"<object_type>:<tenant_id>__<object_id>"`` (see `scoped_object_id` below).
There is one shared store/model rather than one store per tenant, so this
namespacing is what actually prevents two tenants' record IDs from ever
colliding -- ``leave_record:acme__sarah_leave`` and
``leave_record:globex__sarah_leave`` are unrelated objects to OpenFGA even
if both tenants happen to name an employee "sarah". Every tuple written by
the Frappe -> OpenFGA sync (department membership, ownership, hr_admin,
etc.) must use this same convention or a document silently becomes
unreachable (fails closed, but for the wrong reason -- worth getting
right). See `docs/OPENFGA_PROVISIONING.md`.

A `Document` with no `tenant_id` (or, when the caller supplies one, a
`tenant_id` that doesn't match it) is dropped before OpenFGA is even
called -- see `glue.domain` on why there's no such thing as tenant-less
document identity.

## Bounded fan-out

`filter_authorized` uses OpenFGA's `batch_check` API instead of firing one
unbounded `check` call per document: the SDK internally chunks the batch
(`max_batch_size`, default 50 checks/request) and bounds request
concurrency with a semaphore (`max_parallel_requests`, default 10) rather
than opening one connection per document. A large candidate set can no
longer fan out into hundreds of simultaneous requests against OpenFGA.

## Fail-closed

Two failure modes, two closed-by-default behaviors:

- A single check inside the batch errors (e.g. a malformed tuple): the SDK
  itself sets `allowed=False` for that item when it carries an error and no
  explicit `allowed` value -- that document is excluded, nothing else in
  the batch is affected.
- The whole `batch_check` call fails (OpenFGA unreachable, timeout, auth
  failure): caught here and treated as "authorize nothing" -- the pipeline
  sees an empty authorized list and returns the standard no-information
  response, never partial or unfiltered results.
"""
from __future__ import annotations

import logging

from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.models import ClientBatchCheckItem, ClientBatchCheckRequest, ClientTuple

from .onyx_client import Document

logger = logging.getLogger(__name__)

DEFAULT_MAX_PARALLEL_REQUESTS = 10
DEFAULT_MAX_BATCH_SIZE = 50


def scoped_object_id(object_type: str, tenant_id: str, object_id: str) -> str:
    """Build the tenant-namespaced OpenFGA object identifier for a record.

    `__` is used rather than `:` or `#` as the tenant/id separator so this
    can never be mistaken for OpenFGA's own `type:id` or `type:id#relation`
    (userset) syntax -- it's a plain opaque string as far as OpenFGA is
    concerned.
    """
    return f"{object_type}:{tenant_id}__{object_id}"


class OpenFgaFilter:
    def __init__(
        self,
        api_url: str,
        store_id: str,
        model_id: str = "",
        max_parallel_requests: int = DEFAULT_MAX_PARALLEL_REQUESTS,
        max_batch_size: int = DEFAULT_MAX_BATCH_SIZE,
    ) -> None:
        self._config = ClientConfiguration(
            api_url=api_url,
            store_id=store_id,
            authorization_model_id=model_id or None,
        )
        self._batch_options = {
            "max_parallel_requests": max_parallel_requests,
            "max_batch_size": max_batch_size,
        }

    def _open_client(self) -> OpenFgaClient:
        """Isolated for tests to override with a fake client -- everything
        else about `filter_authorized` runs unmodified against it."""
        return OpenFgaClient(self._config)

    async def filter_authorized(
        self,
        user_id: str,
        documents: list[Document],
        *,
        tenant_id: str | None = None,
    ) -> list[Document]:
        """Keep only documents `user_id` is an authorized viewer of.

        `tenant_id`, when given, is the caller's authenticated tenant:
        every document is required to already carry a matching
        `document.tenant_id` (from the retrieval adapter) or it's dropped
        before OpenFGA is consulted at all. `tenant_id` is optional only
        because it isn't threaded through the pipeline's caller yet -- a
        document is *always* required to carry its own tenant_id; there is
        no path where a tenant-less object gets checked or returned.
        """
        scoped: list[tuple[str, Document]] = []
        dropped_tenantless = 0
        for document in documents:
            if not document.tenant_id:
                dropped_tenantless += 1
                continue
            if tenant_id is not None and document.tenant_id != tenant_id:
                dropped_tenantless += 1
                continue
            object_id = scoped_object_id(document.object_type, document.tenant_id, document.object_id)
            scoped.append((object_id, document))

        if dropped_tenantless:
            logger.warning(
                "openfga_dropped_documents_without_matching_tenant tenant_id=%s dropped=%d",
                tenant_id,
                dropped_tenantless,
            )

        if not scoped:
            return []

        checks = [
            ClientBatchCheckItem(
                user=f"user:{user_id}",
                relation="viewer",
                object=object_id,
                correlation_id=str(index),
            )
            for index, (object_id, _document) in enumerate(scoped)
        ]

        try:
            async with self._open_client() as client:
                response = await client.batch_check(
                    ClientBatchCheckRequest(checks=checks),
                    options=self._batch_options,
                )
        except Exception:
            logger.exception(
                "openfga_batch_check_failed user_id=%s candidate_count=%d -- denying all",
                user_id,
                len(scoped),
            )
            return []

        allowed_correlation_ids = {
            result.correlation_id for result in response.result if result.allowed
        }
        return [
            document
            for index, (_object_id, document) in enumerate(scoped)
            if str(index) in allowed_correlation_ids
        ]


class OpenFgaTupleWriter:
    """Write-path counterpart to `OpenFgaFilter`, used by the Frappe sync
    (`glue/frappe_sync.py`) to keep tuples in step with Frappe. Deletes
    tolerate a tuple that's already gone -- OpenFGA's delete errors on a
    missing tuple, but a sync retry after a partial failure must be able
    to re-issue the same delete without that turning into a hard error."""

    def __init__(self, api_url: str, store_id: str, model_id: str = "") -> None:
        self._config = ClientConfiguration(
            api_url=api_url,
            store_id=store_id,
            authorization_model_id=model_id or None,
        )

    def _open_client(self) -> OpenFgaClient:
        return OpenFgaClient(self._config)

    async def write_tuples(self, tuples: list[tuple[str, str, str]]) -> None:
        if not tuples:
            return
        async with self._open_client() as client:
            await client.write_tuples(
                [ClientTuple(user=user, relation=relation, object=object_id) for user, relation, object_id in tuples]
            )

    async def delete_tuples(self, tuples: list[tuple[str, str, str]]) -> None:
        if not tuples:
            return
        async with self._open_client() as client:
            for user, relation, object_id in tuples:
                try:
                    await client.delete_tuples([ClientTuple(user=user, relation=relation, object=object_id)])
                except Exception as exc:
                    message = str(exc).lower()
                    if "not found" in message or "no such" in message or "does not exist" in message:
                        continue
                    raise
