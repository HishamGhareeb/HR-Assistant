# Onyx retrieval adapter

`glue/onyx_client.py` implements the real HTTP call the previous stub
deliberately left as `NotImplementedError`. This documents the endpoint,
auth, response shape, and the one gap left before it's fully trustworthy.

## Pinned version

**v4.4.7** of [onyx-dot-app/onyx](https://github.com/onyx-dot-app/onyx) — the
latest stable (non-beta, non-cloud) tag at the time this was written. The
endpoint, auth scheme, and response shape below were read directly from that
tag's source:

- `backend/onyx/server/query_and_chat/query_backend.py` — route definitions
- `backend/onyx/server/query_and_chat/models.py` — `AdminSearchRequest` / `AdminSearchResponse`
- `backend/onyx/context/search/models.py` — `SearchDoc`, `BaseFilters`
- `backend/onyx/auth/api_key.py`, `backend/onyx/auth/utils.py` — bearer-token auth
- `backend/onyx/configs/app_configs.py` — `APP_API_PREFIX` (empty by default)

## Endpoint

```
POST {ONYX_API_URL}/admin/search
Authorization: Bearer <ONYX_API_KEY>

{
  "query": "<question text>",
  "filters": {
    "document_set": ["tenant:<tenant_id>"],
    "metadata": {
      "tenant_id": ["<tenant_id>"],
      "classification": ["public", "internal"]
    }
  }
}
```

Onyx's plain per-user search API (`/query/*`) only exposes tag lookup and
full chat/answer generation — there is no retrieval-only endpoint for a
regular user role. We don't want Onyx generating the answer anyway (Claude
does that, over authorized context only), so the adapter uses the **admin
search** endpoint instead, which requires an API key with the curator or
admin role.

This is a deliberate defense-in-depth choice, not a shortcut around
authorization: OpenFGA remains the actual per-user authorization gate
downstream of this client (`docs/ARCHITECTURE.md`, trust boundary #2). The
adapter never decides who is allowed to see what — at most, when it's told
which tenant is asking, it narrows the underlying Onyx query to that
tenant's document set (`document_set: ["tenant:<id>"]`) and the caller's
pre-authorized classification mask so one tenant's data, or one clearance
tier's data, is less likely to even be considered as a retrieval candidate
for another tenant's question.

Onyx does not accept a client-supplied result-count parameter on this
endpoint (`NUM_RETURNED_HITS` is a fixed server-side config) — the adapter
applies its own `max_results` truncation client-side as a second bound.

## Response mapping

```json
{"documents": [{
  "document_id": "...", "semantic_identifier": "...", "blurb": "...",
  "source_type": "...", "updated_at": "2026-01-01T00:00:00Z",
  "metadata": {"tenant_id": "...", "record_type": "...", "classification": "..."}
}]}
```

Every returned document is mapped into `glue.onyx_client.Document`
(`object_type`, `object_id`, `chunk`, `tenant_id`, `source`, `retrieved_at`,
`classification`) and can be upgraded to the fully-validated
`glue.domain.Document` / `Citation` contract via `.to_canonical()`.

Onyx's own `source_type` field is *its* connector taxonomy (confluence,
web, file, ...) and is intentionally **not** used as our `object_type`.
Instead, the adapter requires `metadata.record_type` to already be one of
`glue.domain.DocumentType` (`employee_record`, `leave_record`,
`performance_record`, `salary_record`, `policy_document`) — tagging
documents with that metadata at ingestion time is the responsibility of the
Frappe → Onyx sync. Same for `metadata.tenant_id` and
`metadata.classification`.

Classifications are tenant-scoped. `public` means visible to authenticated
users inside that tenant, never globally visible across customer tenants.

A document is **dropped** (not raised, not defaulted) when:

- `metadata.tenant_id` is missing, blank, or (when the caller passed a
  `tenant_id`) doesn't match it
- `metadata.record_type` is missing or isn't a recognized `DocumentType`
- `metadata.classification` is missing, unknown, or outside the
  pre-authorized classification mask passed by the pipeline
- `blurb` is blank

Dropped documents are counted and logged (`onyx_search_dropped_documents`)
rather than silently swallowed, so a sync bug that stops tagging metadata
shows up as a retrieval count anomaly instead of a silent capacity loss.
See `glue/domain.py` for why tenant-less document identity isn't allowed to
exist at all in this codebase.

A response that fails validation entirely (wrong top-level shape, HTTP
error, timeout, connection failure) raises `OnyxAdapterError` — it fails
loudly rather than returning an empty result set that would read as "no
information available" to an employee.

## Testing

`tests/test_onyx_client.py` is a repeatable contract test suite: it drives
the real `OnyxClient` request/response code path through
`httpx.MockTransport` with fixture payloads shaped exactly like the pinned
schema above, so it runs with no network access and no live Onyx instance,
and will catch a drift between this file and its own docstring.

## Known gap

**This has not been run against a live Onyx instance.** The mapping above
is contract-correct against the pinned source, but Onyx's actual runtime
behavior (auth failure codes, empty-index responses, rate limiting) is
unconfirmed until Stage 1 brings a real instance up and Frappe HR data is
indexed into it. Re-verify this file against that point release when that
happens, and update `ONYX_PINNED_VERSION` if the deployed version differs.
