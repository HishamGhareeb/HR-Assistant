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
Onyx retrieval -> OpenFGA document filter -> Claude -> LLM Guard
                                               |
                                               v
                                      answer + suggestions

Every stage ------------------------------------------------> Langfuse
```

Frappe HR remains the intended system of record. Suggestions are review items; they
never mutate Frappe data.

## Trust boundaries

1. The public gateway must authenticate the caller. `X-User-ID` is currently only an
   internal handoff and must not be trusted from the public internet.
2. Retrieval is not authorization. OpenFGA is mandatory before model context is built.
3. Retrieved text is untrusted data and may contain prompt injection.
4. Model output is untrusted until the output scanner passes it. Raw output is not
   sent to Langfuse before that scan. The trace never contains a raw question or
   user identifier; it contains only operational counts/status and, on success,
   the scanner-sanitized answer and suggestions. With incomplete Langfuse
   credentials, tracing is a local no-op.
5. Suggestions require a human decision and a separate, audited workflow.

## Gaps before production

- Implement and contract-test the Onyx search adapter.
- Add signed authentication, tenant isolation, user provisioning, and role mapping.
- Sync Frappe HR records to retrieval and authorization tuples reliably.
- Replace per-document authorization checks with a bounded or batched approach.
- Add timeouts, retries, circuit breakers, structured errors, and request IDs.
- Add persistent audit events and retention controls independent of model tracing.
- Add a review inbox for suggestions and explicit approval/rejection history.
- Add an admin UI, employee chat UI, WhatsApp adapter, deployment manifests,
  observability, backup/restore, security tests, and customer onboarding.
