# HR Assistant architecture

## Current system

The assistant is deliberately read-only. A delivery channel sends an authenticated
employee question to the HTTP API. The pipeline retrieves candidate HR content,
filters every candidate through OpenFGA, sends only authorized text to the language
model, scans the generated answer for sensitive output, and records safe lifecycle
metadata in Langfuse when tracing is explicitly configured.

```text
Channel / UI
    |
    v
FastAPI (/v1/questions)
    |
    v
OpenFGA tenant role mask -> Onyx filtered retrieval -> OpenFGA document filter -> Claude -> LLM Guard
                                                                                 |
                                                                                 v
                                                                        answer + suggestions

Every stage ------------------------------------------------> Langfuse
```

RAL HRMS remains the intended system of record. Suggestions are review items; they
are persisted to the HR review inbox and never mutate RAL HRMS data.

## Trust boundaries

1. The public gateway must authenticate the caller. `X-User-ID` is currently only an
   internal handoff and must not be trusted from the public internet.
2. Retrieval is not authorization. OpenFGA is mandatory before model context is built.
   The pipeline also resolves a tenant-scoped classification mask before Onyx
   search, so HR-only/manager-only material is not even requested unless the
   caller has that tenant role. `PUBLIC` means public within that authenticated
   tenant only; it is never global or cross-tenant.
3. Retrieved text is untrusted data and may contain prompt injection.
4. Model output is untrusted until the output scanner passes it. Raw output is not
   sent to Langfuse before that scan. The trace never contains a raw question or
   user identifier; it contains only operational counts/status. Successful
   answer traces record suggestion count/category/status metadata only, not raw
   answer text, suggestion reasoning, record references, or document chunks. With
   incomplete Langfuse credentials, tracing is a local no-op.
5. Suggestions require a human decision in the review inbox. Approval records
   the reviewer decision and immutable decision history; it does not apply the
   suggestion to RAL HRMS or any HR source system.
6. HR admin ingestion controls are synthetic/read-only. Resync/revoke endpoints
   operate through `glue.hr_source_sync.SyncEngine` and never mutate RAL HRMS.

## Gaps before production

- Replace static/dev role mappings with production user provisioning and admin controls.
- Add persistent audit retention controls independent of model tracing.
- Add an admin UI, employee chat UI, WhatsApp adapter, deployment manifests,
  observability, backup/restore, security tests, and customer onboarding.
