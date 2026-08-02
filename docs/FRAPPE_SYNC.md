# Frappe HR sync

`glue/frappe_sync.py` is the deterministic path from a Frappe HR record to
(a) an Onyx retrieval document and (b) the OpenFGA tuples that record
should contribute — kept in step idempotently as records are created,
changed, and deleted.

**Scope**: synthetic data only, per this ticket's acceptance criteria. A
real Frappe REST/webhook source is out of scope here; it would only need
to produce the same `FrappeRecord` shape this module already consumes —
see "Real Frappe integration" below for exactly what that means.

## Shape

- `FrappeRecord(doctype, name, tenant_id, fields, deleted)` — the generic
  stand-in for "one row Frappe's API returned for one doctype."
- `map_record(record, config) -> MappingResult` — a **pure function**: one
  record in, one optional `IndexedDocumentRef` + a tuple of
  `FgaTupleRef`s out. It never talks to Onyx/OpenFGA/a checkpoint store,
  which is what makes "what does this Frappe record mean" trivially unit
  testable in isolation from "how do we apply that idempotently."
- `SyncEngine.sync_all(tenant_id, records) -> ReconciliationReport` —
  applies mapping results: diffs each record's current mapping against a
  `CheckpointStore`, upserts/deletes only what changed, and reports
  created/updated/deleted/unchanged/failed counts.

## Supported doctypes

| Frappe doctype     | Retrieval document    | Tuples contributed                                                                 |
|---------------------|------------------------|--------------------------------------------------------------------------------------|
| `Employee`           | `employee_record`      | `member` on `department`; `manager` on `department` if `reports_to` is set          |
| `Department`         | *(none)*                | *(none — referenced by other doctypes, doesn't own tuples itself)*                  |
| `Leave Application`  | `leave_record`          | `owner`; `department`; `hr_admin` (per `SyncConfig.hr_admin_user_ids`)              |
| `Appraisal`          | `performance_record`    | `owner`; `department`; `hr_admin`                                                    |
| `Salary Slip`        | `salary_record`         | `owner`; `hr_admin` — **no** `department` tuple, matching `salary_record` having no `manager from department` relation in `openfga/model.fga` by design |
| `HR Policy`          | `policy_document`       | `user:*` `viewer` (public within the tenant)                                        |

HIS-22 adds a required `classification` metadata value to every indexed
document. Current defaults are: employees and leave records are `internal`,
appraisals are `manager_only`, salary slips are `hr_only`, and HR policies are
tenant-public `public`. The pipeline resolves a tenant-scoped OpenFGA role mask
before Onyx search, passes those allowed classifications as an explicit Onyx
metadata filter, and still runs returned documents through the document-level
OpenFGA viewer check before any chunk reaches the LLM.

`SyncConfig.hr_admin_user_ids` is sync-run configuration, not a Frappe
field — Frappe doesn't tag "who is HR admin" per record, so treating it as
a synthetic field would misrepresent where that data actually comes from.

## Classification metadata

Every indexed document also includes `classification` metadata for the
pre-retrieval Onyx filter:

- `Employee` and `Leave Application` -> `internal`
- `Appraisal` -> `manager_only`
- `Salary Slip` -> `hr_only`
- `HR Policy` -> `public`

`public` is tenant-public only. It is always indexed with the same
`tenant_id` metadata and never means cross-tenant or global visibility.

A record whose doctype isn't in this table, or that's missing a field its
doctype requires (e.g. an `Employee` with no `user_id`), raises
`FrappeMappingError` for that one record — `SyncEngine` catches this per
record and reports it as a failure rather than guessing a default that
could reference the wrong user or tenant.

## Idempotency

Each record's last-synced state is a `SyncCheckpoint` (content hash +
which document ID and which exact scoped tuples were written), kept in a
`CheckpointStore`. On each `sync_record`:

- **Unchanged** (`existing.content_hash == new_hash`): no calls to Onyx or
  OpenFGA at all.
- **New or changed**: upsert the document (or delete it if the mapping no
  longer produces one), then diff `existing.tuples` against the newly
  computed tuple set and issue only the deletes/writes for what actually
  changed — e.g. an employee moving departments retracts the old
  `department` tuple and adds the new one, it doesn't touch `owner`.
- **Deleted** (`record.deleted=True`): delete the checkpointed document
  and tuples, then drop the checkpoint. Deleting an already-deleted (no
  checkpoint) record is a no-op, not an error.

The default `InMemoryCheckpointStore` is process-local — fine for a single
sync run/process. A deployment with concurrent or distributed sync workers
would implement `CheckpointStore` against persistent storage instead;
nothing in `SyncEngine` assumes in-memory.

## Retryable checkpoints and reconciliation report

If `document_index.upsert()` or `tuple_writer.write_tuples()`/
`.delete_tuples()` raises for a record, `SyncEngine` catches it, records a
`RecordFailure(doctype, name, reason)` on the `ReconciliationReport`, and
— critically — **does not update that record's checkpoint**. The next
`sync_all()` run sees the same stale-or-missing checkpoint and retries
exactly that record from scratch; nothing else in the batch is affected
(`test_one_failed_record_does_not_block_the_rest_of_the_batch`,
`test_failed_record_does_not_advance_checkpoint_and_is_retried`).

`ReconciliationReport` (`tenant_id`, `started_at`/`finished_at`, and
`created`/`updated`/`deleted`/`unchanged` counts plus the `failed` list)
is the artifact an operator or a scheduled sync job would log/alert on.

## Deletion promptness

"Deleted/revoked records disappear from retrieval and access promptly" is
enforced structurally, not by a background sweep: a `FrappeRecord` with
`deleted=True` is processed synchronously in the same `sync_all()` call
that observes the deletion — there's no separate "reconcile deletions"
pass to fall behind or be skipped. A real Frappe source needs to surface
deletions/revocations (e.g. a Frappe "on_trash" hook or a status field
flip) as a `FrappeRecord(deleted=True)` for this to hold in practice; that
wiring is part of "Real Frappe integration" below, not this module.

## Real Frappe integration (not in this ticket)

Everything above operates on the generic `FrappeRecord` shape. Wiring a
real Frappe HR instance in means building a source that:

1. Polls or receives webhooks for the six doctypes above (Frappe's REST
   API returns exactly `doctype` + `name` + field dict already).
2. Maps Frappe's `user_id`/`reports_to`/`department` link fields to the
   same field names this module expects (`user_id`, `department`,
   `reports_to`, `employee_user_id`).
3. Emits a `FrappeRecord(deleted=True)` on delete/on_trash/status-revoked,
   not just on create/update.

No change to `map_record` or `SyncEngine` should be required — that's the
point of keeping `FrappeRecord` a plain, source-agnostic shape.
