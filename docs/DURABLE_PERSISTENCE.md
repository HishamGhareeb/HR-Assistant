# Durable Persistence Track

The current product is moving from local/synthetic persistence toward a production tenant-isolated data foundation.

This document records the transition path so storage work does not leak into route handlers or weaken the security model.

## Current persistence layers

| State | Current implementation | Production status |
|---|---|---|
| Suggestion review inbox | In-memory, JSONL, and SQLite protocol-compatible stores | SQLite is durable for local/single-node use; PostgreSQL/RLS remains the production target |
| Admin controls | In-memory store | Transitional |
| Frappe sync checkpoints | In-memory store | Transitional |
| Audit events | Hash-chained JSONL | Tamper-evident local sink, not WORM |
| Authorization tuples | OpenFGA | External authorization store |
| Retrieval documents | Onyx | External retrieval system |

## First durable slice

`glue.sqlite_suggestions.SqliteSuggestionStore` adds a durable implementation behind the existing `SuggestionStore` protocol.

It preserves:

- tenant-scoped primary keys;
- immutable terminal suggestion decisions;
- idempotent repeated same decisions;
- append-style decision history;
- no Frappe write path;
- no route-handler storage coupling.

It is intentionally not the final production database layer. It is a low-risk bridge that proves the store contract can survive process restarts before the PostgreSQL/RLS implementation lands.

## Production target

The production persistence target is PostgreSQL with database-level tenant isolation, including:

- tenant/customer tables;
- durable users and roles;
- suggestion and decision tables;
- admin-control and sync-run tables;
- row-level security policies;
- migration tooling;
- backup/restore procedures;
- tenant export/deletion boundaries.

SQLite does not provide production multi-tenant isolation. It must not be treated as the SaaS storage architecture.

## Non-negotiable persistence rules

- Route handlers must depend on protocols/interfaces, not concrete database drivers.
- Tenant ID must come from signed identity or trusted provisioning context.
- Same-looking IDs in different tenants must remain separate records.
- Decision history must not be mutated after commit.
- Suggestion approval must not mutate Frappe HR or any source system.
- Audit/tracing remains metadata-only and separate from application state.
