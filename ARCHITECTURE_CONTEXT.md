# Architecture Context — Sellable HRMS + AI Platform

This document is an AI-architect ingestion context for the current `HR-Assistant`
repository state. It reflects the code in this worktree, including the stacked
HIS-21 suggestion review work and HIS-22 HR admin ingestion/access-control work.

## 1. Executive Summary & Tech Stack

### Executive summary

`HR-Assistant` is a Python/FastAPI service for a read-only, human-in-the-loop HR
assistant. The service answers employee HR questions using authorized retrieval
context and creates reviewable HR suggestions. It deliberately does not mutate
RAL HRMS or any source HRMS. Human HR users review suggestions through a
tenant-scoped inbox; approval/rejection/dismissal records a decision only.

The current architecture is a secure core rather than a complete HRMS product.
It has no relational application database or ORM yet. Durable state is currently
limited to append-only JSONL files for audit and suggestion review state, plus
external systems:

- RAL HRMS is the intended system of record.
- Onyx is the retrieval/vector search layer.
- OpenFGA is the authorization graph.
- Claude is the model provider.
- LLM Guard scans model output before response parsing/delivery.
- Langfuse tracing is optional and metadata-only.
- Prometheus metrics are aggregate-only.

### Core stack

| Layer | Current implementation |
|---|---|
| Language/runtime | Python `>=3.12` |
| Web framework | FastAPI |
| ASGI server | Uvicorn |
| Package/build | `uv`, Hatchling, `uv.lock` |
| Validation/contracts | Pydantic v2 |
| HTTP client | HTTPX |
| Auth | JWT verification via PyJWT cryptography extras |
| Authorization | OpenFGA SDK + `openfga/model.fga` |
| Retrieval/RAG | Onyx admin search endpoint |
| Model provider | Anthropic Claude via `anthropic` SDK |
| Output safety | `llm-guard` Sensitive output scanner |
| Observability | Langfuse optional tracing, Prometheus client metrics |
| Local runtime | Dockerfile, `compose.yaml` for local OpenFGA + API profile |
| Tests | Pytest + pytest-asyncio |

### Major dependencies from `pyproject.toml`

- `fastapi`
- `uvicorn[standard]`
- `pydantic`
- `anthropic`
- `httpx`
- `openfga-sdk`
- `pyjwt[crypto]`
- `llm-guard`
- `langfuse`
- `prometheus-client`
- `python-dotenv`
- `pyyaml`

### Runtime services and configuration

Configuration is environment-driven through `glue.config.Config`.

Required:

- `ANTHROPIC_API_KEY`
- `ONYX_API_URL`
- `ONYX_API_KEY`
- `OPENFGA_API_URL`
- `OPENFGA_STORE_ID`
- `AUTH_ISSUER`
- `AUTH_AUDIENCE`
- `AUDIT_PRIVACY_KEY`

Optional or conditional:

- `CLAUDE_MODEL` defaults to `claude-sonnet-4-6`
- `OPENFGA_MODEL_ID`
- `AUTH_JWKS_URL` or `AUTH_STATIC_KEYS_JSON`
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
- `AUDIT_LOG_PATH`, default `.tmp/audit.jsonl`
- `SUGGESTION_STORE_PATH`, default `.tmp/suggestions.jsonl`
- `HR_REVIEWERS_JSON`, tenant-keyed reviewer map
- `HR_ADMINS_JSON`, tenant-keyed admin map

### Local deployment

- `Dockerfile` builds a Python 3.12 runtime image using `uv sync --locked`.
- `compose.yaml` runs local OpenFGA and an optional API profile.
- Local OpenFGA ports are bound to loopback only.
- API container is read-only with `/tmp` mounted as tmpfs and `no-new-privileges`.

## 2. Data Architecture & Domain Model

### Current database/ORM status

There is currently no application database schema in the repository:

- No Prisma schema.
- No SQL migrations.
- No SQLAlchemy/TypeORM entities.
- No persistent relational database models.

Current persistence is intentionally lightweight:

| State | Implementation | Notes |
|---|---|---|
| Audit events | `HashChainedJsonlAuditSink` | Append-only JSONL, hash-chained, tamper-evident but not WORM/tamper-proof. |
| Suggestions | `JsonlSuggestionStore` | Append-only JSONL application state for review inbox. |
| Admin controls | `InMemoryAdminControlStore` | Process-local operator state; not durable. |
| RAL HRMS sync checkpoints | `InMemoryCheckpointStore` | Process-local checkpointing for synthetic sync. |
| Retrieval documents | Onyx | External search/vector layer, not owned by this repo. |
| Authorization tuples | OpenFGA | External authorization store/model. |

Production still needs a real application persistence layer for tenants,
customers, user provisioning, admin state, billing, payroll, attendance,
retention, and durable sync checkpoints.

### Domain contracts

Primary domain models live in `glue/domain.py`.

#### `Identity`

Authenticated caller contract:

- `tenant_id: str`
- `user_id: str`

Properties:

- Pydantic frozen model.
- Strips and rejects blank tenant/user IDs.
- Produced by signed-token verification before downstream work.

#### `DocumentType`

Recognized authorization/retrieval object types:

- `employee_record`
- `leave_record`
- `performance_record`
- `salary_record`
- `policy_document`

These must stay synchronized with `openfga/model.fga`.

#### `DocumentClassification`

Pre-retrieval clearance tier:

- `public`
- `internal`
- `manager_only`
- `hr_only`
- `system_confidential`

Critical meaning:

`public` means public within the authenticated tenant only. It never means
globally visible or cross-tenant visible.

#### `Citation`

Stable source pointer for a retrieved chunk:

- `source`
- `object_type: DocumentType`
- `object_id`
- `tenant_id`
- `retrieved_at`

#### `Document`

Canonical retrieved-context contract:

- `citation: Citation`
- `chunk`
- `classification: DocumentClassification`

Derived relationship fields:

- `Document.tenant_id` delegates to `citation.tenant_id`
- `Document.object_type` delegates to `citation.object_type`
- `Document.object_id` delegates to `citation.object_id`

#### `Suggestion`

Reviewable HR suggestion:

- `suggestion_id`
- `tenant_id`
- `category`
- `reasoning`
- `record_reference`
- `status`
- `created_at`
- `decided_at`
- `decided_by`

State invariant:

- `pending` must not have `decided_at` or `decided_by`.
- `approved`, `rejected`, and `dismissed` must have `decided_at` and
  `decided_by`.
- Suggestions never mutate RAL HRMS or HR source systems.

#### Tenant guard

`require_same_tenant(*items, tenant_id=...)` raises `CrossTenantError` if any
`Identity`, `Document`, `Citation`, or `Suggestion` belongs to a different
tenant.

### Authorization model

`openfga/model.fga` is the current authorization schema.

#### Types

- `user`
- `tenant`
- `department`
- `employee_record`
- `leave_record`
- `performance_record`
- `salary_record`
- `policy_document`

#### Tenant-level roles

`tenant` relations:

- `employee: [user]`
- `manager: [user]`
- `hr_admin: [user]`
- `system_admin: [user]`

These relations drive the pre-retrieval classification mask.

#### Department relations

`department` relations:

- `member: [user]`
- `manager: [user]`

Departments grant manager visibility on some record types through OpenFGA
relation traversal.

#### Record visibility

`employee_record`, `leave_record`, and `performance_record`:

- `owner: [user]`
- `department: [department]`
- `hr_admin: [user]`
- `viewer = owner or hr_admin or manager from department`

`salary_record`:

- `owner: [user]`
- `hr_admin: [user]`
- `viewer = owner or hr_admin`
- No manager-from-department access by design.

`policy_document`:

- `viewer: [user, user:*]`
- Public policy visibility is still tenant-scoped by object ID and Onyx metadata.

### OpenFGA tenant isolation convention

One shared OpenFGA store/model is used across tenants. Isolation is enforced by
object ID namespacing:

```text
<object_type>:<tenant_id>__<local_id>
```

Examples:

- `leave_record:acme__sarah_leave`
- `leave_record:globex__sarah_leave`
- `department:acme__engineering`

`glue.openfga_client.scoped_object_id()` builds these IDs.

Known limitation:

The relation graph cannot prevent a tuple-writing bug that writes the wrong
tenant prefix. Tuple writers must preserve tenant invariants at sync/provisioning
time.

### RAL HRMS sync model

`glue/hr_source_sync.py` maps synthetic HR-source-shaped records to:

1. Onyx indexed documents.
2. OpenFGA tuples.
3. Sync checkpoint/reconciliation state.

#### Input shape: `HrSourceRecord`

- `doctype`
- `name`
- `tenant_id`
- `fields`
- `deleted`

#### Supported doctypes and mapping

| HR source record type | Document type | Classification | OpenFGA tuples |
|---|---|---|---|
| `Employee` | `employee_record` | `internal` | Department `member`; department `manager` if `reports_to` exists |
| `Department` | none | none | none |
| `Leave Application` | `leave_record` | `internal` | `owner`, `department`, `hr_admin` |
| `Appraisal` | `performance_record` | `manager_only` | `owner`, `department`, `hr_admin` |
| `Salary Slip` | `salary_record` | `hr_only` | `owner`, `hr_admin` only |
| `HR Policy` | `policy_document` | `public` | `viewer` for `user:*` on the tenant-scoped policy object |

`SyncEngine.sync_all(tenant_id, records)` enforces:

- All records in a sync run must match the run tenant.
- Unsupported/malformed records produce per-record failures.
- Deleted records retract indexed documents and tuples.
- Failed records do not advance checkpoints, making retries possible.

### Suggestion review store

`glue/suggestions.py` defines:

- `StaticHrReviewAuthorizer`
- `SuggestionDecision`
- `StoredSuggestion`
- `InMemorySuggestionStore`
- `JsonlSuggestionStore`

Key relationships:

- Suggestions are keyed by `(tenant_id, suggestion_id)`.
- Reviewer authorization is tenant-scoped via `HR_REVIEWERS_JSON`.
- Decision history is append-only at the store/service layer.
- Repeating the same decision by the same reviewer is idempotent.
- Changing an already-decided suggestion raises a conflict.

### HR admin control state

`glue/admin_controls.py` defines:

- `TenantRole`
- `StaticHrAdminAuthorizer`
- `AccessRoleAssignment`
- `AdminRecordFailure`
- `SyncRunSummary`
- `SourceStatus`
- `InMemoryAdminControlStore`

Relationships:

- HR admin authorization is tenant-scoped via `HR_ADMINS_JSON`.
- Role assignments are stored by `(tenant_id, user_id)`.
- Source status is stored by `(tenant_id, source_id)`.
- Sync runs are tenant-filtered and listed newest-first.
- Synthetic resync/revoke uses the existing `SyncEngine`.
- The admin control store contains no RAL HRMS write client and tracks
  `RAL HRMS_mutation_attempts = 0` in tests.

### Payroll, attendance, and other HRMS entities

These are not implemented as application entities yet:

- Payroll
- Attendance
- Time clock / timesheets
- Benefits
- Leave balances
- Employee master records as durable app tables
- Tenant/customer subscriptions
- Billing plans
- Country-law rule packs

Some source-shaped concepts exist only as synthetic RAL HRMS records or retrieval
document categories. They are not durable first-class database tables in this
repo yet.

## 3. API & Module Boundaries

### FastAPI application boundary

Main entrypoint:

- `glue.app:app`
- Constructed by `create_app(...)`

Dependency injection points:

- `pipeline: Pipeline`
- `verifier: TokenVerifier`
- `suggestion_store: SuggestionStore`
- `review_authorizer: HrReviewAuthorizer`
- `admin_store: AdminControlStore`
- `admin_authorizer: HrAdminAuthorizer`
- `sync_engine: SyncEngine`

### API routes

| Method | Route | Auth | Service boundary | Purpose |
|---|---|---|---|---|
| `GET` | `/health` | none | none | Liveness/readiness of process. |
| `GET` | `/metrics` | none | `Pipeline.metrics.render()` | Prometheus exposition. |
| `POST` | `/v1/questions` | signed bearer JWT | `Pipeline.handle_question(identity, question)` | Employee HR Q&A with authorized RAG. |
| `GET` | `/v1/hr/suggestions` | JWT + HR reviewer | `SuggestionStore.list(tenant_id, status)` | List tenant suggestions. |
| `GET` | `/v1/hr/suggestions/{suggestion_id}` | JWT + HR reviewer | `SuggestionStore.get(tenant_id, suggestion_id)` | View one suggestion. |
| `POST` | `/v1/hr/suggestions/{suggestion_id}/decision` | JWT + HR reviewer | `SuggestionStore.decide(...)` | Approve/reject/dismiss. |
| `GET` | `/v1/hr/admin/sources` | JWT + HR admin | `AdminControlStore.list_sources(tenant_id)` | Source/sync status. |
| `GET` | `/v1/hr/admin/sync/runs` | JWT + HR admin | `AdminControlStore.list_runs(tenant_id)` | Sync run history. |
| `POST` | `/v1/hr/admin/sync/resync` | JWT + HR admin | `AdminControlStore.synthetic_resync(..., SyncEngine)` | Synthetic resync of HR-source-shaped records. |
| `POST` | `/v1/hr/admin/sync/revoke` | JWT + HR admin | `AdminControlStore.synthetic_revoke(..., SyncEngine)` | Synthetic deletion/revoke marker. |
| `GET` | `/v1/hr/admin/access/roles` | JWT + HR admin | `AdminControlStore.list_role_assignments(tenant_id)` | List tenant role mappings. |
| `PUT` | `/v1/hr/admin/access/roles/{user_id}` | JWT + HR admin | `AdminControlStore.set_role_assignment(...)` | Set tenant-scoped role assignment. |

### Authentication flow

`glue/auth.py` implements signed JWT validation.

Flow:

1. HTTP request supplies `Authorization: Bearer <JWT>`.
2. `TokenVerifier.verify_async()` validates:
   - signature against key resolved by `kid`
   - `exp`
   - `iss`
   - `aud`
   - tenant claim, default `tenant_id`
   - user claim, default `sub`
3. `build_identity_dependency(verifier)` returns `Identity(tenant_id, user_id)`.
4. `Identity` is threaded into retrieval, authorization, audit, suggestions, and
   admin controls.

Key sources:

- Static public key map through `AUTH_STATIC_KEYS_JSON`.
- JWKS endpoint through `AUTH_JWKS_URL`.

Old `X-User-ID`-only access is rejected by tests and is not trusted.

### RBAC / authorization implementation

The repository uses two authorization layers:

#### 1. Tenant-role pre-retrieval mask

`OpenFgaFilter.allowed_classifications(user_id, tenant_id)` checks role
relations on `tenant:<tenant_id>`.

Mapping:

| OpenFGA tenant role | Allowed classifications |
|---|---|
| employee | `public`, `internal` |
| manager | `public`, `internal`, `manager_only` |
| hr_admin | `public`, `internal`, `manager_only`, `hr_only` |
| system_admin | `system_confidential` |

If the OpenFGA call fails, the pipeline denies all classifications and stops
before Onyx and before the LLM.

#### 2. Document-level OpenFGA filter

After Onyx returns candidates, `OpenFgaFilter.filter_authorized(user_id,
documents, tenant_id=...)`:

- Drops tenant-less documents.
- Drops documents whose tenant does not match the caller.
- Batch-checks `viewer` on the tenant-scoped OpenFGA object IDs.
- Fails closed to an empty authorized list on OpenFGA failure.

### Pipeline module boundary

`glue/pipeline.py` orchestrates:

1. Pre-retrieval classification mask.
2. Tenant/classification-filtered Onyx search.
3. Document-level OpenFGA authorization.
4. Context budget trimming.
5. Claude completion.
6. LLM Guard output scan.
7. Model response validation.
8. Suggestion persistence.
9. Audit event emission.
10. Aggregate metrics emission.

`PipelineResult`:

- `answer`
- `suggestions`
- `blocked`

Failure modes:

- No allowed classifications: no Onyx call, no LLM call.
- No authorized documents: no LLM call.
- OpenFGA failure: fail closed.
- Onyx/Claude dependency failure: safe no-info response.
- Scanner block: safe blocked response.
- Malformed model output: safe no-info response.

### Retrieval boundary

`glue/onyx_client.py` calls:

```http
POST {ONYX_API_URL}/admin/search
Authorization: Bearer <ONYX_API_KEY>
```

Payload includes:

- `query`
- `filters.document_set = ["tenant:<tenant_id>"]`
- `filters.metadata.tenant_id = [tenant_id]`
- `filters.metadata.classification = [allowed classifications]`

Returned documents must include:

- `metadata.tenant_id`
- `metadata.record_type`
- `metadata.classification`
- nonblank `blurb`

Invalid/mismatched documents are dropped client-side.

### Indexing boundary

`glue/onyx_indexer.py` is the write-side adapter used by RAL HRMS sync to upsert
or delete indexed documents. It is separate from retrieval. It writes Onyx
document text and metadata; it does not decide authorization.

### Model boundary

`glue/claude_client.py` wraps Anthropic. The pipeline treats raw model output as
untrusted:

- Raw output goes to LLM Guard before JSON parsing.
- The scanner-approved output is validated by `glue.model_response`.
- Parsed suggestions are converted into `glue.domain.Suggestion`.

### Audit and observability boundary

`AuditLogger.record(...)` writes bounded metadata only:

- request ID
- tenant ID
- tenant-scoped actor HMAC pseudonym
- retrieval/authorization counts
- model/scanner outcomes
- suggestion count
- error class

It never records:

- raw question
- raw answer
- source chunks
- raw employee ID
- suggestion content
- exception messages or stack traces

Langfuse tracing is optional and should stay metadata-only. Prometheus metrics
are aggregate-only and avoid user/request labels.

## 4. Current Business Logic & State Machines

### Question-answering flow

Stateful flow in `Pipeline.handle_question`:

1. Start with `Identity(tenant_id, user_id)` and a question.
2. Resolve allowed classification mask from OpenFGA tenant roles.
3. If no mask, return no-info without retrieval/model call.
4. Search Onyx with tenant + classification filters.
5. Batch-check document-level `viewer` permission in OpenFGA.
6. If no authorized documents remain, return no-info without model call.
7. Fit authorized chunks to context budget.
8. Call Claude with question + authorized context.
9. Scan raw output with LLM Guard.
10. If scanner blocks, return blocked response.
11. Validate scanner-approved JSON response.
12. Persist suggestions when a suggestion store is configured.
13. Emit audit and metrics exactly once.

### Suggestion lifecycle state machine

Suggestion statuses:

- `pending`
- `approved`
- `rejected`
- `dismissed`

Transitions:

```text
pending -> approved
pending -> rejected
pending -> dismissed
```

Rules:

- Suggestions begin as `pending`.
- Only approved/rejected/dismissed are valid decision actions.
- A decision records `decision_id`, `suggestion_id`, `tenant_id`,
  `decided_by`, `decided_at`, `action`, and optional `note`.
- Repeating the same decision by the same reviewer is idempotent.
- Changing an already decided suggestion raises `SuggestionTransitionError`.
- Store lookups are tenant-scoped.
- Decision history is append-only at the service layer.
- A decision never applies data to RAL HRMS.

### HR admin synthetic sync state

Admin sync actions:

- `synthetic_resync`
- `synthetic_revoke`

`SyncRunSummary` captures:

- run ID
- tenant ID
- source ID
- action
- status
- created/updated/deleted/unchanged counts
- failed records
- start/finish timestamps

`SourceStatus` captures the last run/action/status for a tenant/source.

Rules:

- Admin APIs require tenant-scoped HR admin authorization.
- The server derives tenant ID from the signed identity, not request body.
- Resync accepts HR-source-shaped records but rewrites them to the caller tenant.
- Revoke creates a `HrSourceRecord(deleted=True)` for the caller tenant.
- Admin controls do not mutate RAL HRMS.
- Failures are visible and retryable.

### RAL HRMS sync mapping rules

`map_record(record, config)` is pure and deterministic:

- Unsupported doctypes raise `HrSourceMappingError`.
- Missing required fields raise `HrSourceMappingError`.
- `Department` creates no document/tuples.
- `Employee` creates employee document and department membership/manager tuples.
- `Leave Application` creates leave document and owner/department/hr_admin tuples.
- `Appraisal` creates performance document and owner/department/hr_admin tuples.
- `Salary Slip` creates salary document and owner/hr_admin tuples only.
- `HR Policy` creates policy document and tenant-public viewer tuple.

`SyncEngine` idempotency:

- Uses content hash over document + tuples.
- Unchanged records produce no external writes.
- Changed records update only changed document/tuple state.
- Deleted records retract indexed document and tuples.
- Failed records do not advance checkpoint.

### Resilience state machines

`glue/resilience.py` defines:

- timeouts via `call_with_timeout`
- bounded retries via `call_with_retries`
- request ID context binding
- structured safe errors
- circuit breaker states:
  - `closed`
  - `open`
  - `half_open`

Cancellation is intentionally not swallowed or retried.

### Audit hash chain

`HashChainedJsonlAuditSink` writes each event with:

- previous hash
- current record hash
- event payload

This is tamper-evident, not tamper-proof. Production still needs WORM or
append-only storage with access controls.

## 5. Known Gaps, Debt & Unimplemented Features

### Persistence and database gaps

- No production relational database exists yet.
- No tenant/customer tables exist yet.
- No user, role, subscription, payroll, attendance, or leave-balance tables.
- No ORM, migrations, RLS policies, or database-level isolation.
- Suggestion JSONL state is not a durable multi-instance production store.
- Admin control state is in-memory only.
- RAL HRMS sync checkpoints are in-memory only.
- Audit JSONL is tamper-evident but not WORM/tamper-proof.

### Multi-tenancy gaps

Current isolation exists at:

- Pydantic contracts with mandatory tenant IDs.
- `require_same_tenant`.
- OpenFGA object ID namespacing.
- Onyx tenant metadata filters.
- tenant-scoped reviewer/admin maps.

Missing for production:

- Database-level row-level security.
- Tenant-aware durable persistence adapters.
- Tenant provisioning/onboarding.
- Tenant-scoped backups/exports.
- Automated validation that tuple writers cannot mis-prefix tenant objects.

### Auth/RBAC gaps

- `HR_REVIEWERS_JSON` and `HR_ADMINS_JSON` are static/dev configuration.
- Admin role assignments do not yet write OpenFGA tuples.
- No SSO/SCIM integration.
- JWKS resolver is structurally tested but not verified against a chosen live IdP.
- No production user lifecycle/provisioning workflow.
- No manager hierarchy ingestion beyond synthetic RAL HRMS mapping.

### Retrieval/RAG gaps

- Onyx integration is contract-tested against pinned source shape but not yet
  verified against a live Onyx instance.
- Onyx admin-search endpoint is used for retrieval; production must validate
  runtime auth behavior, rate limits, and empty-index behavior.
- No full policy upload pipeline from customer UI.
- No chunking/embedding ownership pipeline beyond RAL HRMS sync/indexer contracts.
- No prompt-injection adversarial suite is currently present in the repo despite
  README mentioning promptfoo as a future test area.

### HRMS product gaps

Missing business modules:

- Payroll engine.
- Bahrain payroll/country-law rule packs.
- Attendance/time-clock.
- Leave balance calculations.
- Benefits.
- Employee self-service profile data.
- Manager approvals outside the suggestion review workflow.
- Employee web chat UI.
- HR admin UI.
- WhatsApp adapter.
- Customer onboarding/admin portal.
- Billing/subscriptions/metering.
- Feature flags/entitlements.

### Compliance and audit gaps

- No production WORM audit storage.
- No DPA/retention/deletion workflow implementation.
- No legal hold.
- No tenant-scoped compliance export.
- No explainable AI metadata store beyond current citations/counts/status fields.
- No PII redaction/tokenization boundary before external model provider calls.

### Infrastructure gaps

- No production database.
- No production deployment manifests beyond Dockerfile/local compose.
- No backup/restore.
- No disaster recovery.
- No SLO/support runbooks.
- No regional deployment/data residency controls.
- No secret-management integration.

### Testing gaps and current coverage

Strong current test coverage exists for:

- FastAPI auth and route behavior.
- JWT verification and invalid-token rejection.
- domain contract validation.
- tenant mismatch rejection.
- Onyx request/response contract.
- OpenFGA filtering and pre-retrieval masks.
- RAL HRMS sync mapping/idempotency/failure retry.
- suggestion review lifecycle.
- pipeline fail-closed behavior.
- audit privacy and hash-chain verification.
- metrics/tracing no-op behavior.
- CI/container configuration.

Still missing:

- Live Onyx integration test.
- Live OpenFGA provisioning smoke test in a deployed environment.
- Live IdP/JWKS test.
- Browser/UI tests because no UI exists.
- Multi-process persistence/concurrency tests.
- Payroll/legal calculation tests.
- Country-law effective-date tests.
- PII redaction/provider-boundary tests.
- Adversarial prompt injection suite.

### Code/documentation debt

- Some older docs still describe past ticket sequencing/status and should be
  normalized after HIS-21/HIS-22 merge.
- `docs/PIPELINE_RELIABILITY.md` still says standalone reliability modules are
  not wired, while the current pipeline does use resilience wrappers; update or
  replace this doc after the stacked PRs land.
- README still references Stage 0/scaffolding and future Promptfoo tests that are
  not present in the tracked file list.
- API docs are mostly Markdown and tests; no OpenAPI export/client SDK is checked
  in.

## Architect Notes

### Safe extension pattern

When adding new features, preserve these invariants:

1. Authenticate before all business logic.
2. Resolve tenant from signed identity, never request body.
3. Authorize before retrieval and before model context construction.
4. Keep `public` tenant-scoped.
5. Keep payroll/compliance calculations deterministic, not LLM-derived.
6. Keep source-system mutations out of AI suggestion approval.
7. Keep audit/tracing metadata-only.
8. Use deterministic fakes in tests for external systems.
9. Add durable storage behind protocols/interfaces rather than hard-coding
   persistence into route handlers.

### Recommended next architecture moves

1. Merge HIS-21 and HIS-22, then retarget stacked branches cleanly.
2. Add a durable database design for tenants, users, roles, admin state,
   suggestions, sync checkpoints, billing/metering, and audit/export indexes.
3. Introduce PostgreSQL RLS or equivalent database-level tenant isolation.
4. Replace static JSON role maps with tenant onboarding/provisioning flows.
5. Add PII redaction/provider-boundary middleware before model calls.
6. Add deterministic Bahrain-first payroll/country-law rule-pack architecture.
7. Add production audit/WORM storage and retention policies.
8. Add employee/HR admin UI surfaces once API contracts stabilize.
