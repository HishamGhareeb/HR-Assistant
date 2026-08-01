# HR Assistant — Definitive Architecture & Builder Handoff

## 1. Purpose and Product Direction

`HR-Assistant` is a Python/FastAPI service for a secure, read-only, human-in-the-loop HR assistant.

Its current responsibilities are:

- Answer employee HR questions using tenant-scoped, authorized retrieval context.
- Generate reviewable HR suggestions.
- Provide a tenant-scoped HR review inbox.
- Record approval, rejection, or dismissal decisions.
- Synchronize synthetic Frappe-shaped records into Onyx and OpenFGA.
- Produce privacy-preserving audit and operational telemetry.

The target product is a sellable, secure, multi-tenant HRMS + AI platform supporting:

- Employee HR Q&A.
- HR administrator review workflows.
- Secure retrieval-augmented generation.
- Strong tenant isolation.
- Auditable AI behavior.
- Employee and HR administration interfaces.
- Deterministic Bahrain-first payroll and country-law rule packs.
- Future attendance, leave, benefits, onboarding, billing, and entitlement modules.

The repository currently implements a secure AI-assistant core, not a complete HRMS. In particular, there is currently **no relational application database or ORM**.

This handoff reflects the supplied repository context, including the stacked HIS-21 suggestion-review work and HIS-22 HR-admin ingestion/access-control work. Builders must verify their merged branch state before relying on those features in a release.

---

## 2. Current Implemented Architecture

### 2.1 System responsibilities

| Component | Current responsibility |
|---|---|
| FastAPI application | HTTP API, authentication dependencies, route orchestration |
| Frappe HR | Intended external HR system of record |
| Onyx | External retrieval/vector-search layer |
| OpenFGA | Tenant roles and document-level authorization graph |
| Anthropic Claude | Model completion provider |
| LLM Guard | Scans raw model output before parsing or delivery |
| JSONL stores | Local append-only audit and suggestion persistence |
| Langfuse | Optional metadata-only tracing |
| Prometheus | Aggregate operational metrics |

Frappe HR remains external. The application does not contain a Frappe write client in its suggestion or admin-control workflows.

### 2.2 Technology stack

| Layer | Current implementation |
|---|---|
| Language/runtime | Python `>=3.12` |
| Web framework | FastAPI |
| ASGI server | Uvicorn |
| Package/build system | `uv`, Hatchling, `uv.lock` |
| Validation/contracts | Pydantic v2 |
| HTTP client | HTTPX |
| Authentication | Signed JWT verification through PyJWT cryptography extras |
| Authorization | OpenFGA SDK and `openfga/model.fga` |
| Retrieval/RAG | Onyx admin-search endpoint |
| Model provider | Anthropic Claude through the `anthropic` SDK |
| Output safety | `llm-guard` Sensitive output scanner |
| Observability | Optional Langfuse tracing and Prometheus metrics |
| Local runtime | Dockerfile and `compose.yaml` |
| Tests | Pytest and pytest-asyncio |

Major dependencies in `pyproject.toml` are:

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

### 2.3 Runtime configuration

Configuration is environment-driven through `glue.config.Config`.

Required configuration:

- `ANTHROPIC_API_KEY`
- `ONYX_API_URL`
- `ONYX_API_KEY`
- `OPENFGA_API_URL`
- `OPENFGA_STORE_ID`
- `AUTH_ISSUER`
- `AUTH_AUDIENCE`
- `AUDIT_PRIVACY_KEY`

Optional or conditional configuration:

- `CLAUDE_MODEL`, defaulting to `claude-sonnet-4-6`
- `OPENFGA_MODEL_ID`
- `AUTH_JWKS_URL` or `AUTH_STATIC_KEYS_JSON`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST`
- `AUDIT_LOG_PATH`, defaulting to `.tmp/audit.jsonl`
- `SUGGESTION_STORE_PATH`, defaulting to `.tmp/suggestions.jsonl`
- `HR_REVIEWERS_JSON`, a tenant-keyed reviewer map
- `HR_ADMINS_JSON`, a tenant-keyed administrator map

### 2.4 Local deployment

- The Dockerfile builds a Python 3.12 runtime image using `uv sync --locked`.
- `compose.yaml` runs local OpenFGA and an optional API profile.
- Local OpenFGA ports are bound to loopback only.
- The API container is read-only.
- `/tmp` is mounted as `tmpfs`.
- The API container uses `no-new-privileges`.

These are local-development controls, not a complete production deployment architecture.

---

## 3. Current Data and Domain Model

### 3.1 Database and persistence status

There is currently **no relational application database or ORM**:

- No Prisma schema.
- No SQL migrations.
- No SQLAlchemy or TypeORM entities.
- No persistent relational application models.
- No database row-level security.
- No durable tenant, customer, user, subscription, payroll, attendance, or leave-balance tables.

Current persistence is:

| State | Implementation | Durability and limitations |
|---|---|---|
| Audit events | `HashChainedJsonlAuditSink` | Append-only and hash-chained; tamper-evident, not WORM or tamper-proof |
| Suggestions | `JsonlSuggestionStore` | Append-only local application state; unsuitable for multi-instance production |
| Admin controls | `InMemoryAdminControlStore` | Process-local and lost on restart |
| Frappe sync checkpoints | `InMemoryCheckpointStore` | Process-local and lost on restart |
| Retrieval documents | Onyx | External system; not owned by this repository |
| Authorization tuples | OpenFGA | External authorization store |

A production application persistence layer has not yet been implemented.

### 3.2 Core domain contracts

Primary models live in `glue/domain.py`.

| Contract | Fields or values | Important rules |
|---|---|---|
| `Identity` | `tenant_id`, `user_id` | Frozen Pydantic model; strips and rejects blank identifiers |
| `DocumentType` | `employee_record`, `leave_record`, `performance_record`, `salary_record`, `policy_document` | Must remain synchronized with `openfga/model.fga` |
| `DocumentClassification` | `public`, `internal`, `manager_only`, `hr_only`, `system_confidential` | `public` is tenant-public only |
| `Citation` | `source`, `object_type`, `object_id`, `tenant_id`, `retrieved_at` | Stable source pointer for a retrieved chunk |
| `Document` | `citation`, `chunk`, `classification` | Tenant, type, and object ID delegate to the citation |
| `Suggestion` | `suggestion_id`, `tenant_id`, `category`, `reasoning`, `record_reference`, `status`, `created_at`, `decided_at`, `decided_by` | Enforces decision-state consistency |

`Document` exposes the following derived relationships:

- `Document.tenant_id` delegates to `citation.tenant_id`.
- `Document.object_type` delegates to `citation.object_type`.
- `Document.object_id` delegates to `citation.object_id`.

Suggestion invariants:

- A `pending` suggestion must not have `decided_at` or `decided_by`.
- An `approved`, `rejected`, or `dismissed` suggestion must have both.
- A suggestion decision records a review outcome only.
- AI suggestion approval must not mutate Frappe or any HR source system.

Tenant guard:

```python
require_same_tenant(*items, tenant_id=...)
```

This raises `CrossTenantError` when an `Identity`, `Document`, `Citation`, or `Suggestion` belongs to another tenant.

### 3.3 Document classification semantics

| Classification | Intended clearance |
|---|---|
| `public` | Available to authorized users inside the authenticated tenant |
| `internal` | Tenant-internal employee access |
| `manager_only` | Manager-or-higher access according to the role mask and object authorization |
| `hr_only` | HR administrator access |
| `system_confidential` | System-administrator classification |

`public` means **tenant-public only**. It never means global, anonymous, or cross-tenant visibility.

### 3.4 OpenFGA authorization model

The current authorization schema is `openfga/model.fga`.

Types:

- `user`
- `tenant`
- `department`
- `employee_record`
- `leave_record`
- `performance_record`
- `salary_record`
- `policy_document`

Tenant relations:

- `employee: [user]`
- `manager: [user]`
- `hr_admin: [user]`
- `system_admin: [user]`

Department relations:

- `member: [user]`
- `manager: [user]`

#### Record visibility

| Object type | Relations | Effective viewer rule |
|---|---|---|
| `employee_record` | `owner`, `department`, `hr_admin` | Owner, HR administrator, or manager from the related department |
| `leave_record` | `owner`, `department`, `hr_admin` | Owner, HR administrator, or manager from the related department |
| `performance_record` | `owner`, `department`, `hr_admin` | Owner, HR administrator, or manager from the related department |
| `salary_record` | `owner`, `hr_admin` | Owner or HR administrator only |
| `policy_document` | `viewer: [user, user:*]` | Tenant-scoped policy visibility |

Managers do not receive department-derived salary-record access.

### 3.5 Role-to-classification mapping

`OpenFgaFilter.allowed_classifications(user_id, tenant_id)` checks relations on `tenant:<tenant_id>`.

| Tenant role | Allowed classifications |
|---|---|
| `employee` | `public`, `internal` |
| `manager` | `public`, `internal`, `manager_only` |
| `hr_admin` | `public`, `internal`, `manager_only`, `hr_only` |
| `system_admin` | `system_confidential` |

If role resolution fails, the pipeline returns no allowed classifications and stops before Onyx retrieval and the model call.

### 3.6 OpenFGA tenant isolation convention

The implementation uses one shared OpenFGA store and model. Tenant isolation is represented through namespaced object identifiers:

```text
<object_type>:<tenant_id>__<local_id>
```

Examples:

```text
leave_record:acme__sarah_leave
leave_record:globex__sarah_leave
department:acme__engineering
```

`glue.openfga_client.scoped_object_id()` constructs these identifiers.

This is an application-level convention. The OpenFGA relation graph cannot independently prevent a tuple-writing defect from applying the wrong tenant prefix. Tuple writers must therefore enforce tenant invariants. A future relational database with row-level security can provide an additional persistence-level backstop, but it does not replace correct OpenFGA tuple construction.

### 3.7 Frappe-shaped synchronization model

`glue/frappe_sync.py` maps synthetic Frappe-shaped records into:

1. Onyx indexed documents.
2. OpenFGA tuples.
3. Sync checkpoint and reconciliation state.

`FrappeRecord` contains:

- `doctype`
- `name`
- `tenant_id`
- `fields`
- `deleted`

#### Exact doctype mapping

| Frappe doctype | Document type | Classification | OpenFGA tuple behavior |
|---|---|---|---|
| `Employee` | `employee_record` | `internal` | Department `member`; department `manager` when `reports_to` exists |
| `Department` | None | None | No document or tuples |
| `Leave Application` | `leave_record` | `internal` | `owner`, `department`, `hr_admin` |
| `Appraisal` | `performance_record` | `manager_only` | `owner`, `department`, `hr_admin` |
| `Salary Slip` | `salary_record` | `hr_only` | `owner` and `hr_admin` only |
| `HR Policy` | `policy_document` | `public` | `viewer` for `user:*` on the tenant-scoped policy object |

`SyncEngine.sync_all(tenant_id, records)` enforces:

- Every record in a sync run must match the run tenant.
- Unsupported or malformed records produce per-record failures.
- Deleted records retract indexed documents and OpenFGA tuples.
- Failed records do not advance their checkpoints.
- Retry remains possible after individual record failures.

`map_record(record, config)` is intended to remain pure and deterministic:

- Unsupported doctypes raise `FrappeMappingError`.
- Missing required fields raise `FrappeMappingError`.
- `Department` produces no document or tuples.
- Other supported doctypes follow the table above.

Sync idempotency uses a content hash over the mapped document and tuples:

- Unchanged records produce no external writes.
- Changed records update changed document or tuple state.
- Deleted records retract document and tuple state.
- Failed records do not advance checkpoints.

This is a synthetic synchronization boundary. It is not a complete production Frappe connector or bidirectional HRMS integration.

### 3.8 Suggestion review model

`glue/suggestions.py` defines:

- `StaticHrReviewAuthorizer`
- `SuggestionDecision`
- `StoredSuggestion`
- `InMemorySuggestionStore`
- `JsonlSuggestionStore`

Relationships and rules:

- Suggestions are keyed by `(tenant_id, suggestion_id)`.
- Reviewer authorization is tenant-scoped through `HR_REVIEWERS_JSON`.
- Decision history is append-only at the store/service boundary.
- Repeating the same decision by the same reviewer is idempotent.
- Attempting a different decision after completion raises a conflict.
- All lookups and decisions are tenant-scoped.
- Approval never applies the suggestion to Frappe or another HR source system.

### 3.9 HR administrator control model

`glue/admin_controls.py` defines:

- `TenantRole`
- `StaticHrAdminAuthorizer`
- `AccessRoleAssignment`
- `AdminRecordFailure`
- `SyncRunSummary`
- `SourceStatus`
- `InMemoryAdminControlStore`

Relationships:

- HR administrator authorization is tenant-scoped through `HR_ADMINS_JSON`.
- Role assignments are keyed by `(tenant_id, user_id)`.
- Source status is keyed by `(tenant_id, source_id)`.
- Sync runs are tenant-filtered and listed newest-first.
- Synthetic resync and revoke operations reuse `SyncEngine`.
- The admin-control store has no Frappe write client.
- Tests track `frappe_mutation_attempts = 0`.

### 3.10 HRMS entities not implemented

The following are not currently implemented as durable application entities:

- Tenant and customer accounts.
- Production user and role records.
- Employee master records.
- Payroll.
- Bahrain payroll or country-law rule packs.
- Attendance.
- Time clock or timesheets.
- Leave balances.
- Benefits.
- Subscription and billing plans.
- Feature entitlements.

Some related concepts appear only as Frappe-shaped source records or retrieval document categories. They are not first-class application tables.

---

## 4. API and Module Boundaries

### 4.1 FastAPI application boundary

The main entrypoint is:

```text
glue.app:app
```

The application is constructed by `create_app(...)`.

Current dependency-injection boundaries are:

- `pipeline: Pipeline`
- `verifier: TokenVerifier`
- `suggestion_store: SuggestionStore`
- `review_authorizer: HrReviewAuthorizer`
- `admin_store: AdminControlStore`
- `admin_authorizer: HrAdminAuthorizer`
- `sync_engine: SyncEngine`

New durable implementations should be introduced behind these or equivalent protocols rather than embedded in route handlers.

### 4.2 Exact route table

| Method | Route | Authentication/authorization | Service boundary | Purpose |
|---|---|---|---|---|
| `GET` | `/health` | None | None | Process health |
| `GET` | `/metrics` | None | `Pipeline.metrics.render()` | Prometheus exposition |
| `POST` | `/v1/questions` | Signed bearer JWT | `Pipeline.handle_question(identity, question)` | Employee HR Q&A using authorized RAG |
| `GET` | `/v1/hr/suggestions` | JWT and tenant HR reviewer | `SuggestionStore.list(tenant_id, status)` | List tenant suggestions |
| `GET` | `/v1/hr/suggestions/{suggestion_id}` | JWT and tenant HR reviewer | `SuggestionStore.get(tenant_id, suggestion_id)` | Retrieve one suggestion |
| `POST` | `/v1/hr/suggestions/{suggestion_id}/decision` | JWT and tenant HR reviewer | `SuggestionStore.decide(...)` | Approve, reject, or dismiss |
| `GET` | `/v1/hr/admin/sources` | JWT and tenant HR administrator | `AdminControlStore.list_sources(tenant_id)` | Retrieve source and sync status |
| `GET` | `/v1/hr/admin/sync/runs` | JWT and tenant HR administrator | `AdminControlStore.list_runs(tenant_id)` | List sync-run history |
| `POST` | `/v1/hr/admin/sync/resync` | JWT and tenant HR administrator | `AdminControlStore.synthetic_resync(..., SyncEngine)` | Run synthetic resync |
| `POST` | `/v1/hr/admin/sync/revoke` | JWT and tenant HR administrator | `AdminControlStore.synthetic_revoke(..., SyncEngine)` | Run synthetic deletion/revoke |
| `GET` | `/v1/hr/admin/access/roles` | JWT and tenant HR administrator | `AdminControlStore.list_role_assignments(tenant_id)` | List tenant role assignments |
| `PUT` | `/v1/hr/admin/access/roles/{user_id}` | JWT and tenant HR administrator | `AdminControlStore.set_role_assignment(...)` | Set a tenant-scoped role assignment |

No payroll, attendance, onboarding, billing, tenant-management, policy-upload, employee-profile, or source-system mutation APIs are currently implemented.

### 4.3 Authentication boundary

`glue/auth.py` implements signed JWT validation.

Request flow:

1. The request supplies `Authorization: Bearer <JWT>`.
2. `TokenVerifier.verify_async()` validates:
   - Signature using a key resolved by `kid`.
   - `exp`.
   - `iss`.
   - `aud`.
   - Tenant claim, defaulting to `tenant_id`.
   - User claim, defaulting to `sub`.
3. `build_identity_dependency(verifier)` creates `Identity(tenant_id, user_id)`.
4. The signed identity is propagated into retrieval, authorization, audit, suggestion, and admin-control workflows.

Verification keys come from either:

- `AUTH_STATIC_KEYS_JSON`, or
- A JWKS endpoint configured through `AUTH_JWKS_URL`.

Legacy access based only on `X-User-ID` is rejected by tests and is not trusted.

The tenant must always come from the verified identity, never from a request-body tenant field.

### 4.4 Authorization boundary

Authorization has two distinct stages.

#### Stage 1: Pre-retrieval classification authorization

`OpenFgaFilter.allowed_classifications(user_id, tenant_id)` resolves the caller’s classification mask before Onyx is queried.

If the call fails or returns no allowed classifications:

- No Onyx request is made.
- No model request is made.
- The system fails closed.

#### Stage 2: Document-level authorization

After Onyx returns candidates, `OpenFgaFilter.filter_authorized(...)`:

- Drops documents without a tenant.
- Drops documents whose tenant differs from the authenticated tenant.
- Batch-checks the `viewer` relation against tenant-scoped OpenFGA object IDs.
- Returns an empty authorized set if OpenFGA fails.

Authorization must happen both **before retrieval** and **before LLM context construction**. Tenant/classification filters reduce the retrieval scope; document-level authorization determines which returned chunks may enter model context.

### 4.5 Pipeline boundary

`glue/pipeline.py` orchestrates:

1. Pre-retrieval classification authorization.
2. Tenant- and classification-filtered Onyx search.
3. Document-level OpenFGA authorization.
4. Context-budget trimming.
5. Claude completion.
6. LLM Guard scanning.
7. Model-response validation.
8. Suggestion persistence.
9. Audit emission.
10. Aggregate metric emission.

`PipelineResult` contains:

- `answer`
- `suggestions`
- `blocked`

Failure behavior:

| Condition | Required behavior |
|---|---|
| No allowed classifications | Do not call Onyx or the model |
| OpenFGA role resolution fails | Fail closed |
| No authorized documents | Do not call the model |
| Document authorization fails | Fail closed to no authorized documents |
| Onyx dependency fails | Return a safe no-information response |
| Claude dependency fails | Return a safe no-information response |
| Output scanner blocks | Return a safe blocked response |
| Model response is malformed | Return a safe no-information response |

### 4.6 Retrieval boundary

`glue/onyx_client.py` calls:

```http
POST {ONYX_API_URL}/admin/search
Authorization: Bearer <ONYX_API_KEY>
```

The request payload includes:

```text
query
filters.document_set = ["tenant:<tenant_id>"]
filters.metadata.tenant_id = [tenant_id]
filters.metadata.classification = [allowed classifications]
```

Returned documents must include:

- `metadata.tenant_id`
- `metadata.record_type`
- `metadata.classification`
- A nonblank `blurb`

Invalid, tenant-less, or tenant-mismatched results are dropped client-side.

The Onyx contract is tested against a pinned response shape but has not yet been verified against a production Onyx instance.

### 4.7 Indexing boundary

`glue/onyx_indexer.py` is the write-side adapter used by the Frappe synchronization flow.

It:

- Upserts document text and metadata.
- Deletes indexed documents when source records are deleted.
- Does not decide authorization.
- Remains separate from the retrieval client.

### 4.8 Model and output-safety boundary

`glue/claude_client.py` wraps the Anthropic client.

Raw model output is considered untrusted:

1. Claude returns raw output.
2. LLM Guard scans the raw output before application parsing.
3. Only scanner-approved output is passed to `glue.model_response`.
4. The structured response is validated.
5. Validated suggestion data is converted into `glue.domain.Suggestion`.

The LLM may summarize authorized information or propose reviewable suggestions. It must not compute authoritative payroll, legal entitlement, tax, contribution, or compliance results.

### 4.9 Audit and observability boundary

`AuditLogger.record(...)` records bounded metadata:

- Request ID.
- Tenant ID.
- Tenant-scoped actor HMAC pseudonym.
- Retrieval and authorization counts.
- Model and scanner outcomes.
- Suggestion count.
- Error class.

It must not record:

- Raw questions.
- Raw answers.
- Retrieved source chunks.
- Raw employee identifiers.
- Suggestion content.
- Exception messages.
- Stack traces.
- Payroll or HR-sensitive source payloads.

Audit and tracing must remain **metadata-only**.

Langfuse is optional and must remain metadata-only. Prometheus metrics must remain aggregate-only and avoid user- or request-level labels.

---

## 5. State Machines and Business Logic

### 5.1 Question-answering flow

```text
Authenticated identity
    ↓
Resolve tenant-role classification mask
    ↓
Tenant/classification-filtered retrieval
    ↓
Document-level OpenFGA authorization
    ↓
Authorized context-budget trimming
    ↓
Claude completion
    ↓
LLM Guard scan
    ↓
Structured response validation
    ↓
Suggestion persistence
    ↓
Metadata-only audit and aggregate metrics
```

Detailed rules:

1. Start with a verified `Identity` and question.
2. Resolve the classification mask using OpenFGA.
3. Stop if no classifications are authorized.
4. Query Onyx using tenant and classification filters.
5. Authorize returned documents individually through OpenFGA.
6. Stop if no authorized documents remain.
7. Fit only authorized chunks into the context budget.
8. Call Claude with the question and authorized context.
9. Scan raw model output.
10. Return a blocked response if the scanner blocks.
11. Validate scanner-approved structured output.
12. Persist valid suggestions when a suggestion store is configured.
13. Emit audit and metrics exactly once.

### 5.2 Suggestion lifecycle

States:

```text
pending → approved
pending → rejected
pending → dismissed
```

There are no transitions out of `approved`, `rejected`, or `dismissed`.

Decision data includes:

- `decision_id`
- `suggestion_id`
- `tenant_id`
- `decided_by`
- `decided_at`
- `action`
- Optional `note`

Rules:

- Every suggestion starts as `pending`.
- Only `approved`, `rejected`, and `dismissed` are valid decision actions.
- Repeating the same decision by the same reviewer is idempotent.
- A different decision after completion raises `SuggestionTransitionError`.
- Decisions and lookups are tenant-scoped.
- Decision history is append-only at the service layer.
- AI suggestion approval must not mutate Frappe or any HR source system.

Any future source-system action must be a separate, explicitly designed workflow with its own authorization, validation, audit, idempotency, and rollback model. It must not be silently attached to suggestion approval.

### 5.3 HR admin synthetic sync state

Actions:

- `synthetic_resync`
- `synthetic_revoke`

`SyncRunSummary` captures:

- Run ID.
- Tenant ID.
- Source ID.
- Action.
- Status.
- Created, updated, deleted, and unchanged counts.
- Failed records.
- Start and finish timestamps.

`SourceStatus` captures the latest run, action, and status for a tenant/source pair.

Rules:

- Admin APIs require tenant-scoped HR administrator authorization.
- Tenant ID comes from the signed identity.
- Resync accepts Frappe-shaped records and rewrites them to the authenticated tenant.
- Revoke creates a caller-tenant `FrappeRecord(deleted=True)`.
- Failures are visible and retryable.
- Admin controls do not mutate Frappe HR.

### 5.4 Resilience state machines

`glue/resilience.py` provides:

- Timeouts through `call_with_timeout`.
- Bounded retries through `call_with_retries`.
- Request-ID context binding.
- Structured safe errors.
- Circuit-breaker states:
  - `closed`
  - `open`
  - `half_open`

Cancellation is intentionally not swallowed or retried.

### 5.5 Audit hash chain

`HashChainedJsonlAuditSink` writes each event with:

- The previous record hash.
- The current record hash.
- The event payload.

This makes local audit data tamper-evident, not tamper-proof. Production still requires WORM or equivalently controlled append-only storage.

---

## 6. Non-Negotiable Engineering Invariants

Every pull request must preserve these rules:

1. **Authenticate before all business logic.**

2. **Resolve the tenant from the signed identity, never from the request body.**

3. **Authorize before retrieval and before LLM context construction.** Pre-retrieval classification authorization and post-retrieval document authorization are both required.

4. **`public` is tenant-public only.** It is never global or cross-tenant.

5. **Fail closed.** Authorization failures, missing classification masks, tenant mismatches, and empty authorized-document sets must stop before the model call.

6. **AI suggestion approval must not mutate Frappe or any HR source system.** Approval records a human decision only.

7. **Payroll and compliance calculations must be deterministic code, not LLM-derived.** This includes salaries, leave entitlements, taxes, contributions, statutory benefits, effective-date rules, and country-law calculations.

8. **Audit and tracing must remain metadata-only.** Raw prompts, answers, chunks, employee identifiers, suggestion content, and sensitive exception data must not enter logs, traces, or metrics.

9. **Durable persistence must remain behind protocols or interfaces.** Do not bind route handlers directly to PostgreSQL, JSONL, or another storage implementation.

10. **External systems must use deterministic fakes in ordinary automated tests.** Tests should not depend on live Onyx, OpenFGA, Frappe, Claude, or IdP state.

11. **Every persisted or retrieved object must carry enforceable tenant context.**

12. **Onyx filtering does not replace OpenFGA authorization, and OpenFGA does not replace tenant validation.** Both controls are required.

13. **Model output remains untrusted until it has passed output scanning and structured validation.**

---

## 7. Known Gaps and Technical Debt

### 7.1 Persistence

- No production relational database.
- No ORM or migrations.
- No tenant/customer tables.
- No durable application user or role records.
- No subscription, payroll, attendance, or leave-balance tables.
- No database row-level security.
- Suggestion persistence is unsuitable for multi-instance operation.
- Admin state and checkpoints are process-local.
- Audit JSONL is not WORM.

### 7.2 Multi-tenancy

Current tenant controls exist in:

- Mandatory tenant-bearing Pydantic contracts.
- `require_same_tenant`.
- OpenFGA object-ID namespacing.
- Onyx document-set and metadata filters.
- Tenant-scoped reviewer and administrator maps.

Missing controls include:

- Database-level row-level security.
- Tenant-aware durable adapters.
- Production tenant provisioning.
- Tenant-scoped backup, restore, export, and deletion.
- Automated tuple-writer validation against incorrect tenant prefixes.

### 7.3 Authentication and authorization

- `HR_REVIEWERS_JSON` and `HR_ADMINS_JSON` are static development configuration.
- Admin role assignments do not write OpenFGA tuples.
- No production user lifecycle exists.
- No SSO or SCIM integration.
- JWKS behavior is structurally tested but not verified with a selected live identity provider.
- Manager hierarchy ingestion exists only through synthetic Frappe mapping.

### 7.4 Retrieval and RAG

- No verified live Onyx integration test.
- Production behavior of the Onyx admin-search endpoint is unverified.
- Rate limits and empty-index behavior are unverified.
- No customer-facing policy upload pipeline.
- No complete application-owned chunking or embedding pipeline beyond current sync/indexer contracts.
- No adversarial prompt-injection suite.
- No PII redaction or tokenization boundary before external model calls.

### 7.5 HRMS product surface

Not implemented:

- Payroll engine.
- Bahrain payroll and country-law rule packs.
- Attendance and time clock.
- Timesheets.
- Leave-balance calculations.
- Benefits.
- Employee self-service profile data.
- Manager approval workflows outside suggestion review.
- Employee web chat.
- HR administrator UI.
- WhatsApp adapter.
- Tenant onboarding portal.
- Billing, subscriptions, and metering.
- Feature flags and entitlements.

### 7.6 Compliance and audit

- No production WORM audit store.
- No implemented DPA workflow.
- No retention or deletion workflow.
- No legal hold.
- No tenant-scoped compliance export.
- No dedicated explainability store beyond citations, counts, and statuses.
- No provider-boundary PII redaction/tokenization.

### 7.7 Infrastructure and operations

- No production deployment manifests beyond Dockerfile and local Compose.
- No database backup or restore.
- No disaster-recovery design.
- No SLO or support runbooks.
- No regional deployment or data-residency controls.
- No production secret-management integration.

### 7.8 Documentation debt

- Some older documentation still describes historical ticket sequencing.
- `docs/PIPELINE_RELIABILITY.md` reportedly says resilience modules are not wired even though the current pipeline uses resilience wrappers.
- The README still references Stage 0/scaffolding and future Promptfoo tests that are not present.
- No checked-in OpenAPI export or generated client SDK exists.
- The integration state of stacked HIS-21 and HIS-22 work must be confirmed and normalized.

---

## 8. Testing Status

### 8.1 Strong current coverage

Tests currently cover:

- FastAPI authentication and route behavior.
- JWT verification and invalid-token rejection.
- Domain contract validation.
- Tenant mismatch rejection.
- Onyx request and response contracts.
- OpenFGA classification masks and document filtering.
- Frappe mapping, idempotency, and retry behavior.
- Suggestion-review lifecycle.
- Pipeline fail-closed behavior.
- Audit privacy and hash-chain verification.
- Metrics and tracing no-op behavior.
- CI and container configuration.

### 8.2 Missing test coverage

Still required:

- Live Onyx integration tests.
- Deployed OpenFGA provisioning smoke tests.
- Live IdP/JWKS integration tests.
- Browser tests once interfaces exist.
- Multi-process persistence and concurrency tests.
- PII redaction/provider-boundary tests.
- Prompt-injection and RAG adversarial tests.
- Payroll and statutory calculation tests.
- Country-law effective-date and historical-version tests.
- Database RLS and cross-tenant penetration tests.

---

## 9. Prioritized Backlog

### P0 — Production data and tenant foundation

1. Introduce a relational persistence layer behind existing protocols.
2. Add migrations and database lifecycle management.
3. Add database-level tenant isolation using PostgreSQL RLS or an equivalent control.
4. Replace JSONL suggestion state, in-memory admin state, and in-memory checkpoints with durable adapters.
5. Replace static reviewer/admin maps with tenant provisioning and role management.
6. Connect role assignment changes to correctly namespaced OpenFGA tuple management.

No detailed database schema is defined by the current repository. Schema design must be proposed and reviewed rather than inferred as already implemented.

### P1 — Trust, privacy, and compliance

1. Add PII redaction or tokenization before model-provider calls.
2. Introduce production append-only or WORM audit storage.
3. Implement tenant-aware retention, deletion, legal-hold, and compliance-export workflows.
4. Add prompt-injection and data-exfiltration adversarial tests.
5. Validate metadata-only behavior across logs, traces, metrics, and failure paths.

### P2 — Live integration verification

1. Validate Onyx authentication, rate limits, indexing, deletion, and empty-index behavior.
2. Add a deployed OpenFGA provisioning smoke test.
3. Verify JWKS behavior against the selected identity provider.
4. Add tenant-provisioning and tuple-writing integration tests.
5. Add multi-process concurrency and durability tests after database introduction.

### P3 — Deterministic HRMS foundation

1. Design a versioned, deterministic Bahrain-first payroll and country-law rule-pack architecture.
2. Define explicit effective-date behavior for statutory rules.
3. Add deterministic payroll and compliance test fixtures.
4. Add attendance, time-clock, timesheet, and leave-balance modules.
5. Add benefits and employee self-service data.
6. Keep all authoritative calculations outside the LLM.

The current repository contains no payroll or country-law implementation. Builders must not treat the backlog description as an existing schema or API contract.

### P4 — Product interfaces and commercialization

1. Employee web chat.
2. HR suggestion and administration UI.
3. Tenant onboarding and administration portal.
4. Billing, subscriptions, metering, and entitlements.
5. Manager workflows outside AI suggestion review.
6. WhatsApp adapter.
7. Production deployment, backups, disaster recovery, SLOs, and support runbooks.

---

## 10. Recommended Next Pull Requests

### PR 1 — Durable suggestion and admin persistence foundation

Introduce database infrastructure and protocol-backed durable adapters for the existing suggestion, admin-control, and sync-checkpoint boundaries. Include migrations, transaction behavior, concurrency tests, and explicit confirmation that route handlers remain storage-agnostic.

Do not introduce speculative payroll or attendance tables in this PR.

### PR 2 — Database tenant isolation

Add tenant-aware database access and PostgreSQL RLS or an equivalent database-level control. Test cross-tenant reads and writes using adversarial cases. Ensure tenant context originates from the signed identity.

### PR 3 — Provisioning and OpenFGA role synchronization

Replace static `HR_REVIEWERS_JSON` and `HR_ADMINS_JSON` maps with a durable tenant provisioning and role-management flow. Make role changes write correctly namespaced OpenFGA tuples, with idempotency and reconciliation tests.

### PR 4 — Provider-boundary privacy controls

Add PII redaction or tokenization immediately before external model calls. Preserve citations and authorization context without exposing unnecessary employee data. Verify that logs, traces, metrics, and error paths remain metadata-only.

### PR 5 — Production audit storage

Add a protocol-backed append-only or WORM audit sink with access controls and verification tooling. Retain the metadata-only event contract. Define retention, deletion-exception, legal-hold, and tenant-export boundaries without logging content.

### Subsequent recommended work

- Add live Onyx, OpenFGA, and IdP verification.
- Add prompt-injection and exfiltration testing.
- Normalize outdated architecture and reliability documentation.
- Export the OpenAPI specification after current API contracts stabilize.
- Design the deterministic Bahrain-first payroll/rule-pack architecture.
- Build employee and HR administration interfaces only after durable tenancy and API boundaries are stable.

---

## 11. Builder Acceptance Checklist

Before merging any change, confirm:

- The authenticated tenant comes from a verified token.
- No request-body tenant can override identity context.
- Authorization occurs before retrieval.
- Document authorization occurs before context construction.
- `public` remains tenant-public only.
- Cross-tenant documents are rejected.
- OpenFGA failures stop the model path.
- No unauthorized or unscanned content reaches the LLM response parser.
- Suggestion approval does not write to Frappe or another HR system.
- Payroll and compliance logic, if introduced, is deterministic and version-tested.
- Audit, traces, and metrics contain metadata only.
- New persistence is accessed through protocols.
- External dependencies have deterministic test doubles.
- Failure and retry behavior is explicit.
- Documentation states clearly whether a feature is implemented, partial, synthetic, or planned.

---

## 12. First 5 PRs to Build Next

1. **Add relational persistence behind protocols** for suggestions, admin controls, and sync checkpoints.
2. **Add database-level tenant isolation** with RLS and cross-tenant security tests.
3. **Implement durable tenant provisioning and OpenFGA role synchronization**, replacing static JSON role maps.
4. **Add PII redaction/tokenization at the model-provider boundary** with privacy regression tests.
5. **Move audit events to production append-only/WORM storage** while preserving the metadata-only contract.