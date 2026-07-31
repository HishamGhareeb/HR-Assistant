# Audit and observability

## Audit records

`glue.audit` records one minimal event after a pipeline request completes or fails.
An event contains a request ID, tenant ID, a tenant-scoped HMAC pseudonym for the
actor, stage counts, enum outcomes, suggestion count, and an error *class* only.
It never has fields for the question, answer, source text, raw employee ID,
suggestion content, exception message, or stack trace.

Use one durable random `privacy_key` per environment. Losing it prevents future
correlation with earlier actor references; rotating it intentionally starts a new
correlation epoch. Do not place the key in the repository or application logs.

`HashChainedJsonlAuditSink` is a small local implementation for development and
tests. It appends hash-linked JSON lines and detects local edits, removal, or
reordering. It is tamper-evident, not a compliance-grade immutable store: a
privileged writer could replace the file and rebuild the chain. Production must
send the same `AuditSink` interface to an access-controlled append-only/WORM
store, with an independently retained checkpoint of the latest hash.

## Retention and access

Set retention with the customer DPA and applicable employment/privacy law; the
application must not choose a blanket retention period. Restrict read access to
named compliance and security roles, log every export, encrypt durable storage,
and regularly verify the stored hash chain. Support tenant-scoped retention and
legal-hold policies in the future persistence adapter.

## Operational telemetry

`glue.observability.safe_call` and `safe_call_async` make tracing optional:
failure of Langfuse or another telemetry service returns `None` and cannot fail a
user request. Cancellation still propagates. `Metrics` exports aggregate
candidate/authorization counts and outcome counters without a request-ID or user
label, avoiding high-cardinality and personal-data leakage. Correlate individual
requests through the audit event and structured log request ID, not metrics.

Pipeline integration should create one audit event in a `finally` path after
normalizing outcomes, and should call `Metrics.record_request` with counts only.
It must not pass question text, model output, document chunks, or suggestions to
either component.
