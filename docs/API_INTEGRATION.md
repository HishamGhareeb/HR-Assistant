# Wiring HIS-12–HIS-18 into the request path

This ticket connects the standalone modules built in HIS-12 through
HIS-18 to the actual `/v1/questions` request path (`glue/app.py`,
`glue/pipeline.py`), on top of the runnable API foundation from HIS-11.
No module listed below was reimplemented — this is wiring, plus the
smaller edits (`glue/claude_client.py`, `glue/config.py`) needed to make
the wiring possible.

## Request flow

```
Authorization: Bearer <JWT>
    |
    v
glue.auth.TokenVerifier          (HIS-16) --> glue.domain.Identity
    |
    v
Pipeline.handle_question(identity, question)
    |
    +-> OnyxClient.search(question, tenant_id=identity.tenant_id)     (HIS-13)
    |
    +-> OpenFgaFilter.filter_authorized(user_id, docs, tenant_id=...) (HIS-14)
    |
    +-> fit_to_budget(chunks, max_tokens=...)                         (HIS-17)
    |
    +-> ClaudeClient.complete(question, chunks)  -> raw text
    |
    +-> OutputScanner.scan(question, raw_text)   -> sanitized, is_valid
    |
    +-> validate_model_response(sanitized)                            (HIS-17)
    |
    +-> AuditLogger.record(...)  +  Metrics.record_request(...)       (HIS-18)
    |
    v
QuestionResponse
```

## HR suggestion review flow

Generated suggestions are persisted after the answer payload passes
authorization, output scanning, and schema validation. HR review endpoints
reuse the same signed bearer-token identity, authorize the caller as a
tenant-scoped reviewer, and only then read or change inbox state:

```
Authorization: Bearer <JWT>
    |
    v
glue.auth.TokenVerifier -> Identity(tenant_id, user_id)
    |
    v
StaticHrReviewAuthorizer       (tenant-scoped reviewer map)
    |
    v
JsonlSuggestionStore           (list/view/approve/reject/dismiss)
```

Approval, rejection, and dismissal append immutable decision-history
records. They do not call Frappe and do not mutate HR source systems.

Every external call in that chain (Onyx, OpenFGA, Claude) is wrapped with
`call_with_timeout` + `call_with_retries` + a per-dependency
`CircuitBreaker` (HIS-17); the LLM Guard scan gets a timeout only (a local
call, not worth retrying/breaking on). The whole thing is wrapped in one
`try/except/finally` in `Pipeline.handle_question`: any `PipelineError`
(from a timed-out/exhausted/circuit-open dependency) surfaces its
`safe_message` — never its `detail`, never a raw exception — as the
response, and the `finally` block emits exactly one audit event and one
`Metrics.record_request` call regardless of which branch ran, including
on `asyncio.CancelledError` (never swallowed — see `glue/resilience.py`).

## What changed in each file

- **`glue/auth.py`, `glue/domain.py`, `glue/onyx_client.py`,
  `glue/openfga_client.py`, `glue/resilience.py`, `glue/model_response.py`,
  `glue/context_budget.py`, `glue/audit.py`, `glue/observability.py`**:
  unchanged. Consumed as-is.
- **`glue/claude_client.py`**: `ClaudeClient.answer()` (which parsed
  Claude's JSON internally, unvalidated) is replaced by
  `ClaudeClient.complete()`, returning the **raw** response text. Parsing
  and schema validation now happen in exactly one place —
  `glue.model_response.validate_model_response`, called from the
  pipeline on the *scanner's sanitized output*, not on Claude's raw text.
  This file had no in-flight HIS-11 changes, so editing it didn't
  conflict with anything.
- **`glue/config.py`**: adds `AUTH_ISSUER` / `AUTH_AUDIENCE` /
  `AUTH_JWKS_URL` / `AUTH_STATIC_KEYS_JSON` (auth) and
  `AUDIT_PRIVACY_KEY` / `AUDIT_LOG_PATH` (audit). `ONYX_API_KEY` changes
  from optional to required — `OnyxClient` has required it since HIS-13
  (the admin search endpoint needs one); the old default `""` would have
  failed at `OnyxClient.__init__` instead of at config load, which is a
  worse failure mode for a missing-config problem.
- **`glue/pipeline.py`**: `Pipeline.__init__` takes `audit_logger`,
  `metrics`, and per-stage timeout/retry config in addition to the
  original five dependencies. `handle_question(identity, question)`
  replaces `handle_question(user_id, question)` — `Identity` carries
  `tenant_id` through retrieval and authorization instead of a bare
  string.
- **`glue/app.py`**: `authenticated_user` (the `X-User-ID` header
  dependency) is replaced by `get_identity`, which lazily builds (and
  caches on `app.state`, mirroring the existing `get_pipeline` pattern)
  a `TokenVerifier` from config and calls
  `glue.auth.build_identity_dependency` — the actual token-parsing/401
  logic still lives in `glue/auth.py`, not duplicated here. Adds a
  `bind_request_id` middleware (echoes `X-Request-ID`, generating one if
  absent) and a `GET /metrics` endpoint exposing `Pipeline.metrics`.

## Why this is a separate PR stacked after HIS-18, not a rebase onto HIS-11

HIS-11 (`hisham0ghareeb/his-11-stabilize-runnable-api-foundation`) had not
merged to `main` at the time this was written, but its commit was already
reachable in the shared git history (git refs are shared across worktrees
regardless of filesystem permissions on a given worktree's working
directory). This branch cherry-picks that commit on top of the HIS-12–18
stack rather than waiting — same effect as a rebase, without needing
HIS-11's PR to land first. `glue/requirements.txt` /
`glue/requirements-dev.txt` (deleted by HIS-11 in favor of
`pyproject.toml` + `uv.lock`) is the one file that actually conflicted;
resolved by taking the deletion and folding the dependencies added across
HIS-14/16/18 (`pyyaml`, `pyjwt[crypto]`, `prometheus-client`; `pydantic`,
`httpx`, `openfga-sdk` were already present) into `pyproject.toml`, then
regenerating `uv.lock`.

## Testing

- `tests/test_pipeline.py`: rewritten for the new `Identity`-based
  signature and dependency injection. Covers identity threading to
  Onyx/OpenFGA, the happy path, no-authorized-documents, **cross-tenant
  document rejection** (using the real `OpenFgaFilter`, not a fake — a
  document tagged for a different tenant than the caller never reaches
  Claude), **OpenFGA failure denying all** and failing closed, malformed/
  incomplete Claude JSON failing closed, scanner-block failing closed,
  that the scanner sees Claude's raw text before any parsing and the
  pipeline delivers the *scanner's* sanitized value, **audit privacy**
  (question/answer/user-identifying text never appears in the serialized
  audit event, only its HMAC pseudonym), exactly-once audit emission
  (including on an unexpected non-`PipelineError` exception), retry
  behavior on a flaky dependency, context-budget enforcement before
  Claude, and that Claude/the scanner run off the event loop thread.
- `tests/test_app.py`: rewritten for signed bearer auth. Covers missing
  `Authorization` header, the **old `X-User-ID` header alone no longer
  working**, a token forged with an unrelated private key being rejected,
  a valid token's tenant/user reaching the pipeline unchanged, request-ID
  generation and passthrough, the `/metrics` endpoint, and the service
  degrading to 503 (not a crash) when either the pipeline's or the auth
  verifier's configuration is missing.
- One pre-existing cross-test issue fixed along the way: `asyncio.Task`
  copies its creating context, so a `request_id` bound by an unrelated
  test elsewhere in the suite (`tests/test_observability.py` binding a
  non-UUID value) could leak into `tests/test_pipeline.py` once
  `glue/audit.py`'s strict `request_id` pattern started actually
  validating it. Fixed with an autouse fixture that binds a fresh valid
  ID before each pipeline test.
