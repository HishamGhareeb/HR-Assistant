"""End-to-end request pipeline: Onyx retrieval -> OpenFGA filtering ->
context budgeting -> Claude -> LLM Guard -> schema validation -> audit +
metrics. This is the only place these pieces are wired together -- every
delivery channel (WhatsApp, etc.) just calls `handle_question`.

## Identity flows through, not just user_id

`handle_question` takes a `glue.domain.Identity` (tenant_id + user_id),
verified upstream by `glue.auth` -- not a bare string. `identity.tenant_id`
is threaded into both the Onyx search and the OpenFGA filter (so cross-
tenant documents are dropped before either even considers them, per those
modules' own tenant-scoping) and into the audit event, so a request's
tenant is attached at every stage rather than only at the API boundary.

## Order of operations

Onyx retrieval -> OpenFGA authorization -> context budget (bounds what
goes to Claude) -> Claude -> LLM Guard scan (on Claude's *raw* text,
before any parsing) -> schema validation of the scanner's sanitized
output (`glue.model_response`) -> suggestions. Scanning the raw text
before parsing, and validating the *scanner's* sanitized value rather
than the original model output, means nothing unscanned or unvalidated
ever reaches a client either because it was blocked (sensitive content)
or because it didn't parse (malformed/adversarial output) -- both fail
the same way, into `BLOCKED_RESPONSE`.

## Failure handling

Every external call (Onyx, OpenFGA, Claude) is timeout+retry+circuit-
breaker wrapped (`glue.resilience`); LLM Guard gets a timeout only (a
local scan, not a network dependency worth retrying or breaking on).
A `PipelineError` from any stage is caught once, at the top, and its
`safe_message` (never its `detail`, never a raw exception) becomes the
response -- "fails closed with a safe response" applies uniformly to a
timed-out dependency and to an unexpected bug alike.

One `AuditEvent` and one `Metrics.record_request` call happen exactly
once per call, in a `finally`, regardless of which branch returned or
raised -- including on cancellation, which is never swallowed (see
`glue.resilience` and `glue.observability` for why).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from .audit import AuditLogger
from .claude_client import ClaudeClient
from .context_budget import fit_to_budget
from .domain import DocumentClassification, Identity, Suggestion
from .llm_guard_scan import OutputScanner
from .model_response import ModelResponseValidationError, validate_model_response
from .observability import Metrics, safe_call
from .onyx_client import Document, OnyxClient
from .openfga_client import OpenFgaFilter
from .resilience import (
    CircuitBreaker,
    PipelineError,
    RetryPolicy,
    call_with_retries,
    call_with_timeout,
    current_request_id,
)
from .tracer import Tracer
from .suggestions import SuggestionStore

logger = logging.getLogger(__name__)

NO_INFO_RESPONSE = "I don't have information on that."
BLOCKED_RESPONSE = "That response was flagged by an automated safety check and held for review."
SERVICE_UNAVAILABLE_RESPONSE = "The service is temporarily unavailable. Please try again."

DEFAULT_ONYX_TIMEOUT_SECONDS = 10.0
DEFAULT_OPENFGA_TIMEOUT_SECONDS = 5.0
DEFAULT_CLAUDE_TIMEOUT_SECONDS = 30.0
DEFAULT_GUARD_TIMEOUT_SECONDS = 10.0
DEFAULT_CONTEXT_MAX_TOKENS = 6_000


@dataclass
class PipelineResult:
    answer: str
    suggestions: list[Suggestion]
    blocked: bool


class Pipeline:
    def __init__(
        self,
        onyx: OnyxClient,
        openfga: OpenFgaFilter,
        claude: ClaudeClient,
        guard: OutputScanner,
        tracer: Tracer,
        audit_logger: AuditLogger,
        metrics: Metrics,
        *,
        onyx_timeout_seconds: float = DEFAULT_ONYX_TIMEOUT_SECONDS,
        openfga_timeout_seconds: float = DEFAULT_OPENFGA_TIMEOUT_SECONDS,
        claude_timeout_seconds: float = DEFAULT_CLAUDE_TIMEOUT_SECONDS,
        guard_timeout_seconds: float = DEFAULT_GUARD_TIMEOUT_SECONDS,
        context_max_tokens: int = DEFAULT_CONTEXT_MAX_TOKENS,
        retry_policy: RetryPolicy | None = None,
        suggestion_store: SuggestionStore | None = None,
    ) -> None:
        self._onyx = onyx
        self._openfga = openfga
        self._claude = claude
        self._guard = guard
        self._tracer = tracer
        self._audit_logger = audit_logger
        self.metrics = metrics  # public: glue/app.py's /metrics endpoint reads this
        self._onyx_timeout_seconds = onyx_timeout_seconds
        self._openfga_timeout_seconds = openfga_timeout_seconds
        self._claude_timeout_seconds = claude_timeout_seconds
        self._guard_timeout_seconds = guard_timeout_seconds
        self._context_max_tokens = context_max_tokens
        self._retry_policy = retry_policy or RetryPolicy()
        self._suggestion_store = suggestion_store
        # One breaker per dependency, held for the process lifetime (not
        # per-request) -- that's what lets sustained failure trip it.
        self._onyx_circuit = CircuitBreaker(name="onyx")
        self._openfga_circuit = CircuitBreaker(name="openfga")
        self._claude_circuit = CircuitBreaker(name="claude")

    async def handle_question(self, identity: Identity, question: str) -> PipelineResult:
        request_id = current_request_id()
        trace = safe_call(lambda: self._tracer.trace_request(), component="langfuse")

        retrieval_count = 0
        authorized_count = 0
        suggestion_count = 0
        model_outcome = "error"
        scanner_outcome = "not_run"
        error_class: str | None = None
        answer = SERVICE_UNAVAILABLE_RESPONSE
        suggestions: list[Suggestion] = []
        blocked = False

        try:
            allowed_classifications = await self._allowed_classifications(identity)
            if trace is not None:
                safe_call(
                    lambda: trace.span(
                        name="pre-retrieval-access",
                        output={"allowed_classifications": [c.value for c in allowed_classifications]},
                    ),
                    component="langfuse",
                )
            if not allowed_classifications:
                model_outcome = "no_info"
                answer = NO_INFO_RESPONSE
                if trace is not None:
                    safe_call(
                        lambda: trace.span(
                            name="result",
                            output={"model_outcome": model_outcome, "authorized_count": 0, "blocked": False},
                        ),
                        component="langfuse",
                    )
                return PipelineResult(answer=answer, suggestions=[], blocked=False)

            candidates = await self._retrieve(question, identity.tenant_id, allowed_classifications)
            retrieval_count = len(candidates)
            if trace is not None:
                safe_call(
                    lambda: trace.span(name="onyx-retrieval", output={"candidate_count": retrieval_count}),
                    component="langfuse",
                )

            authorized = await self._authorize(identity.user_id, candidates, identity.tenant_id)
            authorized_count = len(authorized)
            if trace is not None:
                safe_call(
                    lambda: trace.span(name="openfga-filter", output={"authorized_count": authorized_count}),
                    component="langfuse",
                )

            if not authorized:
                model_outcome = "no_info"
                answer = NO_INFO_RESPONSE
                if trace is not None:
                    safe_call(
                        lambda: trace.span(
                            name="result",
                            output={"model_outcome": model_outcome, "authorized_count": 0, "blocked": False},
                        ),
                        component="langfuse",
                    )
                return PipelineResult(answer=answer, suggestions=[], blocked=False)

            budget = fit_to_budget([doc.chunk for doc in authorized], max_tokens=self._context_max_tokens)

            raw_output = await self._ask_claude(question, budget.kept)

            # Scan the raw text before any parsing -- content safety is
            # checked before structure is ever trusted.
            sanitized_output, is_valid = await self._scan(question, raw_output)
            scanner_outcome = "passed" if is_valid else "blocked"
            if trace is not None:
                safe_call(lambda: trace.span(name="llm-guard-scan", output={"is_valid": is_valid}), component="langfuse")

            if not is_valid:
                model_outcome = "blocked"
                blocked = True
                answer = BLOCKED_RESPONSE
                if trace is not None:
                    safe_call(lambda: trace.generation(name="claude-answer", output={"blocked": True}), component="langfuse")
                    safe_call(
                        lambda: trace.span(name="result", output={"answer": answer, "blocked": True}),
                        component="langfuse",
                    )
                return PipelineResult(answer=answer, suggestions=[], blocked=True)

            # Validate the scanner's sanitized value, never Claude's raw
            # output -- a scanner that redacts still has to produce
            # something that parses and fits the schema, or we fail
            # closed here too rather than deliver a half-sanitized blob.
            try:
                validated = validate_model_response(sanitized_output)
            except ModelResponseValidationError as exc:
                model_outcome = "blocked"
                blocked = True
                answer = BLOCKED_RESPONSE
                logger.warning("model_response_validation_failed request_id=%s detail=%s", request_id, exc)
                if trace is not None:
                    safe_call(lambda: trace.generation(name="claude-answer", output={"blocked": True}), component="langfuse")
                    safe_call(
                        lambda: trace.span(name="result", output={"answer": answer, "blocked": True}),
                        component="langfuse",
                    )
                return PipelineResult(answer=answer, suggestions=[], blocked=True)

            suggestions = [
                Suggestion(
                    tenant_id=identity.tenant_id,
                    category=s.category,
                    reasoning=s.reasoning,
                    record_reference=s.record_reference,
                    created_at=datetime.now(timezone.utc),
                )
                for s in validated.suggestions
            ]
            if self._suggestion_store is not None:
                for suggestion in suggestions:
                    self._suggestion_store.create(suggestion)
            suggestion_count = len(suggestions)
            model_outcome = "answered"
            answer = validated.answer
            if trace is not None:
                safe_call(
                    lambda: trace.generation(
                        name="claude-answer",
                        output={
                            "answered": True,
                            "suggestion_count": suggestion_count,
                            "suggestions": [
                                {"category": s.category, "status": s.status.value}
                                for s in suggestions
                            ],
                        },
                    ),
                    component="langfuse",
                )
                safe_call(
                    lambda: trace.span(
                        name="result",
                        output={"model_outcome": model_outcome, "suggestion_count": suggestion_count, "blocked": False},
                    ),
                    component="langfuse",
                )
            return PipelineResult(answer=answer, suggestions=suggestions, blocked=False)

        except asyncio.CancelledError:
            error_class = "CancelledError"
            raise
        except PipelineError as exc:
            model_outcome = "error"
            error_class = type(exc).__name__
            answer = exc.safe_message
            logger.warning(
                "pipeline_stage_failed request_id=%s error_class=%s detail=%s", request_id, error_class, exc.detail
            )
            return PipelineResult(answer=answer, suggestions=[], blocked=False)
        except Exception as exc:  # noqa: BLE001 -- top-level safety net, must never leak internals to a client
            model_outcome = "error"
            error_class = type(exc).__name__
            logger.exception("pipeline_unexpected_failure request_id=%s", request_id)
            return PipelineResult(answer=SERVICE_UNAVAILABLE_RESPONSE, suggestions=[], blocked=False)
        finally:
            self._audit_logger.record(
                request_id=request_id,
                tenant_id=identity.tenant_id,
                user_id=identity.user_id,
                retrieval_count=retrieval_count,
                authorized_count=authorized_count,
                model_outcome=model_outcome,
                scanner_outcome=scanner_outcome,
                suggestion_count=suggestion_count,
                error_class=error_class,
            )
            self.metrics.record_request(
                retrieval_count=retrieval_count,
                authorized_count=authorized_count,
                model_outcome=model_outcome,
                suggestion_count=suggestion_count,
                scanner_blocked=scanner_outcome == "blocked",
                error_class=error_class,
            )

    async def _allowed_classifications(self, identity: Identity) -> tuple[DocumentClassification, ...]:
        try:
            return await call_with_timeout(
                self._openfga.allowed_classifications(identity.user_id, identity.tenant_id),
                timeout_seconds=self._openfga_timeout_seconds,
                stage="pre-retrieval-access",
            )
        except Exception:
            logger.exception(
                "pre_retrieval_access_failed user_id=%s tenant_id=%s -- denying all",
                identity.user_id,
                identity.tenant_id,
            )
            return ()

    async def _retrieve(
        self,
        question: str,
        tenant_id: str,
        allowed_classifications: tuple[DocumentClassification, ...],
    ) -> list[Document]:
        async def attempt() -> list[Document]:
            return await call_with_timeout(
                self._onyx.search(question, tenant_id=tenant_id, allowed_classifications=allowed_classifications),
                timeout_seconds=self._onyx_timeout_seconds,
                stage="onyx-retrieval",
            )

        return await self._onyx_circuit.call(
            lambda: call_with_retries(attempt, stage="onyx-retrieval", policy=self._retry_policy)
        )

    async def _authorize(self, user_id: str, documents: list[Document], tenant_id: str) -> list[Document]:
        # OpenFgaFilter.filter_authorized already fails closed internally
        # (returns [] rather than raising on a whole-batch failure -- see
        # glue/openfga_client.py) -- this wrapper mainly adds a bounded
        # wall-clock timeout on top of that existing guarantee.
        async def attempt() -> list[Document]:
            return await call_with_timeout(
                self._openfga.filter_authorized(user_id, documents, tenant_id=tenant_id),
                timeout_seconds=self._openfga_timeout_seconds,
                stage="openfga-filter",
            )

        return await self._openfga_circuit.call(
            lambda: call_with_retries(attempt, stage="openfga-filter", policy=self._retry_policy)
        )

    async def _ask_claude(self, question: str, context_chunks: list[str]) -> str:
        async def attempt() -> str:
            return await call_with_timeout(
                asyncio.to_thread(self._claude.complete, question, context_chunks),
                timeout_seconds=self._claude_timeout_seconds,
                stage="claude-answer",
            )

        return await self._claude_circuit.call(
            lambda: call_with_retries(attempt, stage="claude-answer", policy=self._retry_policy)
        )

    async def _scan(self, question: str, output: str) -> tuple[str, bool]:
        return await call_with_timeout(
            asyncio.to_thread(self._guard.scan, question, output),
            timeout_seconds=self._guard_timeout_seconds,
            stage="llm-guard-scan",
        )
