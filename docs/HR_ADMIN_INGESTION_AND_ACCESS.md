# HR admin ingestion and access controls

HIS-22 adds tenant-scoped HR admin controls around ingestion, sync
visibility, and access mapping. These controls are still read-only with
respect to Frappe HR: they can run the synthetic sync engine against
operator-supplied records or a synthetic deletion marker, but they do not
call any Frappe mutation API.

## Classification model

Every indexed document carries:

- `tenant_id`
- `record_type`
- `classification`

Supported classifications are:

- `public` — public inside the authenticated tenant only; never global and
  never visible across tenants.
- `internal` — visible only after the caller is known to be a tenant
  employee/manager/HR admin and the document-specific OpenFGA check passes.
- `manager_only` — retrievable only for tenant managers/HR admins before
  document-specific OpenFGA checks.
- `hr_only` — retrievable only for tenant HR admins before document-specific
  OpenFGA checks.
- `system_confidential` — reserved for tenant system-admin workflows.

The current synthetic Frappe mapping tags HR policies as `public`,
employee and leave records as `internal`, appraisals as `manager_only`, and
salary slips as `hr_only`.

## Pre-retrieval authorization flow

The request path is:

1. Verify the signed bearer token into `Identity(tenant_id, user_id)`.
2. Ask OpenFGA for the caller's tenant-scoped retrieval mask on
   `tenant:<tenant_id>`.
3. If that check/list fails or returns no classifications, return the
   standard no-information response. Onyx is not called and the LLM is not
   called.
4. Query Onyx with metadata filters for `tenant_id` and the allowed
   classifications.
5. Run document-level OpenFGA checks over the returned candidates.
6. If no documents remain, return no information without an LLM call.

This is defense in depth: Onyx narrows candidates by tenant/classification,
but OpenFGA remains the authorization boundary.

## Admin API

All admin endpoints require a signed token and `HR_ADMINS_JSON`, a
tenant-keyed map such as:

```json
{"acme": ["hr-1"]}
```

A user listed under one tenant has no access to another tenant.

- `GET /v1/hr/admin/sources`
- `GET /v1/hr/admin/sync/runs`
- `POST /v1/hr/admin/sync/resync`
- `POST /v1/hr/admin/sync/revoke`
- `GET /v1/hr/admin/access/roles`
- `PUT /v1/hr/admin/access/roles/{user_id}`

`resync` accepts synthetic Frappe-shaped records. The server sets their
tenant from the signed identity, ignoring any cross-tenant input. `revoke`
creates a synthetic `FrappeRecord(deleted=True)` for the caller's tenant.
Both produce a sync run summary with created/updated/deleted/unchanged
counts and per-record failures so operators can see retryable failures.

Role assignments are tenant-scoped operator state for access-management
visibility. They do not create a global admin/reviewer bypass and do not
write OpenFGA tuples by themselves; HIS-23 can connect this to real
provisioning once tenant onboarding is defined.

## Audit and privacy boundary

Pipeline audit events remain metadata-only: request ID, tenant ID,
tenant-scoped actor pseudonym, counts, enum outcomes, suggestion count, and
error class. They do not store raw question text, document chunks, policy
content, model output, or suggestion content.

Admin sync run summaries may include doctype/name/source IDs and failure
reason strings for operator troubleshooting. They must not include raw
document text, policy content, question text, chunks, or model output.

## Compatibility notes

- HIS-23 can replace the static/admin in-memory role surfaces with durable
  tenant onboarding and OpenFGA tuple provisioning without changing the
  request pipeline contract.
- HIS-39 analytics should consume only aggregate run/status metadata and
  audit-safe counts, not raw HR content or model text.
