# Domain contracts

`glue/domain.py` defines the typed contracts shared across the API,
retrieval, authorization, audit, and UI boundaries: `Identity`, `Citation`,
`Document`, `Suggestion`, and `SuggestionStatus`. See the module docstrings
for the reasoning behind each field; the two constraints worth calling out
here are tenant scoping and the suggestion lifecycle.

## Tenant scoping

Every contract that can cross a trust boundary carries a mandatory
`tenant_id` (directly, or via `Document.tenant_id` -> `Citation.tenant_id`).
There is no tenant-less state, because `openfga/model.fga` scopes every
relation by data ownership within a tenant, not by global user identity.

Call `require_same_tenant(*items, tenant_id=...)` at every boundary that
mixes the caller's identity with retrieved or stored data -- for example,
after Onyx retrieval and before the OpenFGA filter, or when loading a
suggestion for review. It raises `CrossTenantError` the moment any item's
`tenant_id` doesn't match the caller's, so a bug can't silently leak one
tenant's data into another tenant's request.

## Suggestion lifecycle

`SuggestionStatus` is explicit: `pending`, `approved`, `rejected`,
`dismissed`. A suggestion is never auto-applied (see the read-only trust
boundary in `ARCHITECTURE.md`), so the contract itself enforces that:

- `approved` / `rejected` suggestions must have both `decided_at` and
  `decided_by` set -- a decision always has a timestamp and an owner.
- `pending` / `dismissed` suggestions must **not** have either set -- no
  decision has been recorded yet.

## Status

This module is the contract layer only. Wiring it into `glue/onyx_client.py`,
`glue/openfga_client.py`, `glue/claude_client.py`, `glue/pipeline.py`, and
`glue/app.py` is deliberately left to the tickets that own those adapters
(Onyx retrieval, OpenFGA authorization, authentication/tenant isolation) so
this change doesn't collide with in-flight work on the API foundation.
