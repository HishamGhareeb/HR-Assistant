# Pipeline reliability

Three standalone modules, each covering one slice of this ticket's
acceptance criteria. None of them are wired into `glue/pipeline.py` yet —
see "Status" below.

## `glue/resilience.py` — timeouts, retries, circuit breaker, structured errors, request IDs

- **`call_with_timeout(awaitable, timeout_seconds, stage)`** — wraps
  `asyncio.wait_for`; raises `StageTimeoutError` (a `PipelineError`) on
  expiry rather than letting a bare `asyncio.TimeoutError` propagate.
- **`call_with_retries(func, stage, policy, retry_on)`** — bounded retries
  with exponential backoff + jitter (`RetryPolicy`, default 3 attempts).
  Raises `DependencyUnavailableError` after the last attempt fails.
  **Never retries `asyncio.CancelledError`** — a retry loop that catches a
  bare `Exception` and swallows cancellation is a classic bug; this
  re-raises it immediately so an upstream cancellation (e.g. a client
  disconnecting) actually stops the call instead of getting retried into
  a timeout.
- **`CircuitBreaker`** — stops calling a dependency that's already failing
  repeatedly instead of piling up more failed/timed-out requests against
  it. `CLOSED` → (`failure_threshold` consecutive failures) → `OPEN` →
  (`reset_timeout_seconds` elapsed) → `HALF_OPEN` (one probe call
  allowed) → success closes it / failure reopens it immediately. Also
  never treats cancellation as a failure.
- **`PipelineError`** (base for the above) carries `safe_message` (what a
  client may ever see — generic, no dependency names or exception text)
  separately from `detail` (logs only) and a `request_id`.
- **Request IDs**: `current_request_id()` reads a `contextvars.ContextVar`,
  generating one on first access within a task if unset — since
  contextvars propagate through `await` automatically within a task, this
  doesn't need to be threaded through every function signature by hand.
  `bind_request_id(id)` sets it explicitly (e.g. from an inbound
  `X-Request-ID` header). Every `PipelineError` raised in that task picks
  up the same ID, which is what ties a client-visible failure back to
  full detail in the logs.
- **Cancellation propagation**: covered by the two "never retries
  cancellation" points above — Python's `asyncio` cancellation is
  already cooperative and propagates through `await` chains on its own;
  the risk this module specifically guards against is retry/circuit logic
  accidentally absorbing it.

## `glue/model_response.py` — JSON/schema validation with safe fallback

Claude is instructed to return `{"answer": str, "suggestions": [...]}`
(`glue/claude_client.py`'s `SYSTEM_PROMPT`), but per `docs/ARCHITECTURE.md`
trust boundary #4 ("Model output is untrusted until the output scanner
passes it"), that response is still untrusted as far as this codebase's
own contracts go. `validate_model_response(raw_text)`:

- Parses JSON, rejects non-object top-level values
- Validates against `ModelResponsePayload` (bounded `answer` length,
  bounded suggestion count and field lengths — a length bound doubles as
  a cheap guard against a runaway or adversarial response)
- Raises `ModelResponseValidationError` on any failure

**Safe fallback is the caller's responsibility, by design**: this module
validates and raises; it doesn't decide what a malformed response should
degrade to, because that's `glue/pipeline.py`'s call (it already has a
`NO_INFO_RESPONSE` / `BLOCKED_RESPONSE` pattern for exactly this kind of
decision) — see "Status" below for why the wiring isn't in this PR.

## `glue/context_budget.py` — context and token budgets

`fit_to_budget(chunks, max_tokens, chars_per_token=4)` keeps retrieved
document chunks (assumed most-relevant-first, per retrieval ranking) up
to an approximate token budget before they're assembled into Claude's
context. No offline tokenizer for Claude's models is available locally,
and counting via the Anthropic API would mean a network call just to
decide how much context to send — so this is a **conservative
character-based approximation**, documented as such, not an exact count.

Stops at the first chunk that would overflow the budget rather than
skipping it to see if a smaller, less-relevant one later still fits (that
would reorder relevance by chunk size, which is worse). Always keeps at
least the first chunk even if it alone exceeds the budget — sending one
oversized-but-most-relevant chunk beats sending no context at all.

## Tests

`tests/test_resilience.py` (20), `tests/test_model_response.py` (12),
`tests/test_context_budget.py` (7) — covering timeout, malformed model
output (invalid JSON, wrong shape, oversized fields, wrong types),
scanner-adjacent validation gaps, and dependency outage (retry exhaustion,
circuit open/half-open/closed transitions, cancellation not swallowed by
either), per this ticket's acceptance criteria. All use fake clocks/no-op
sleep — no real waiting, no live dependency needed.

## Status

None of these three modules are wired into `glue/pipeline.py` or
`glue/claude_client.py` in this PR. Both files have in-flight changes from
the API-foundation ticket (HIS-11) at the time this was written — wiring
timeouts/retries/circuit-breakers around the Onyx/OpenFGA/Claude/LLM Guard
calls, and routing `validate_model_response`'s failures into the
pipeline's existing `NO_INFO_RESPONSE`/`BLOCKED_RESPONSE` fallback
pattern, would mean editing the same lines HIS-11 is actively changing.
Same reasoning as `docs/DOMAIN_CONTRACTS.md`, `docs/ONYX_ADAPTER.md`, and
`docs/AUTHENTICATION.md` — each of those modules is complete and tested
standalone, ready to be wired in as a focused follow-up once HIS-11
merges.
