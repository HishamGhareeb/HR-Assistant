"""Observability baseline: a safety wrapper that guarantees Langfuse (or
any other optional tracing/telemetry call) can never break a request,
structured logging that always carries the current request ID, and a
small Prometheus metrics registry.

## Langfuse is optional and cannot break requests

`glue/tracer.py`'s `Tracer.trace_request` calls out to Langfuse
unconditionally today -- if Langfuse is unreachable, misconfigured, or
just slow, that currently has no guard between it and the rest of
`Pipeline.handle_question`. `safe_call` / `safe_call_async` are the guard:
they run a side-effecting callable, catch and log anything it raises (an
exception *class* only -- see `glue/audit.py` on why never a message or
stack trace beyond the log), and return `None` instead of propagating.
Wrapping every Langfuse call site in `glue/tracer.py` with this is the
follow-up wiring step -- see `docs/AUDIT_AND_OBSERVABILITY.md`.

`asyncio.CancelledError` is never swallowed here either, same reasoning
as `glue/resilience.py`: a tracing call being cancelled along with the
request it was tracing is correct behavior, not a tracing failure to log
and ignore.

## Structured logs carry request IDs

`log_event` emits one structured (JSON-serializable `extra`) log line,
always including `request_id` from `glue.resilience.current_request_id()`
unless the caller overrides it -- so a log line and the `AuditEvent` /
`PipelineError` for the same request can always be correlated.

## Metrics

A minimal `Metrics` wrapper around `prometheus_client` with the counters/
histogram this pipeline's stages actually need. Deliberately no
request-ID label on any metric: request IDs are per-request-unique, and a
Prometheus label with unbounded cardinality (one time series per request)
will eventually take a metrics backend down -- correlation to a specific
request belongs in logs (via `log_event`) and `AuditEvent`, not metrics.
`render()` returns the exposition-format bytes a `/metrics` endpoint would
return; wiring an actual endpoint is `glue/app.py`'s job (deferred, see
docs).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest

from .resilience import current_request_id

logger = logging.getLogger(__name__)

T = TypeVar("T")


def safe_call(func: Callable[[], T], *, component: str) -> T | None:
    """Run a synchronous optional side effect (e.g. a Langfuse call).
    Returns the result, or None (and logs) if it raised."""
    try:
        return func()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # Do not send exception text or a traceback to telemetry/log sinks:
        # dependency messages can contain request content or identifiers.
        logger.error(
            "optional_component_failed component=%s error_class=%s request_id=%s",
            component,
            type(exc).__name__,
            current_request_id(),
        )
        return None


async def safe_call_async(func: Callable[[], Awaitable[T]], *, component: str) -> T | None:
    try:
        return await func()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error(
            "optional_component_failed component=%s error_class=%s request_id=%s",
            component,
            type(exc).__name__,
            current_request_id(),
        )
        return None


def log_event(level: int, message: str, *, request_id: str | None = None, **fields: object) -> None:
    """Structured log line: `message` plus `fields` as `extra`, always
    including `request_id` (from the current task's contextvar unless
    explicitly overridden)."""
    logger.log(level, message, extra={"request_id": request_id or current_request_id(), **fields})


class Metrics:
    """One registry per process (or per test, via a fresh `CollectorRegistry`
    -- prometheus_client's default global registry can't be reused
    cleanly across tests since metric names must be unique per registry)."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self.registry = registry or CollectorRegistry()

        self.retrieval_count = Histogram(
            "hr_assistant_retrieval_candidates",
            "Number of candidate documents returned by retrieval per request",
            registry=self.registry,
        )
        self.authorized_count = Histogram(
            "hr_assistant_authorized_documents",
            "Number of documents that survived authorization per request",
            registry=self.registry,
        )
        self.requests_total = Counter(
            "hr_assistant_requests_total",
            "Total completed requests by model outcome",
            ["model_outcome"],
            registry=self.registry,
        )
        self.scanner_blocks_total = Counter(
            "hr_assistant_scanner_blocks_total",
            "Total responses withheld by the output scanner",
            registry=self.registry,
        )
        self.errors_total = Counter(
            "hr_assistant_errors_total",
            "Total request failures by error class",
            ["error_class"],
            registry=self.registry,
        )
        self.suggestions_total = Counter(
            "hr_assistant_suggestions_total",
            "Total suggestions raised for review",
            registry=self.registry,
        )

    def record_request(
        self,
        *,
        retrieval_count: int,
        authorized_count: int,
        model_outcome: str,
        suggestion_count: int = 0,
        scanner_blocked: bool = False,
        error_class: str | None = None,
    ) -> None:
        self.retrieval_count.observe(retrieval_count)
        self.authorized_count.observe(authorized_count)
        self.requests_total.labels(model_outcome=model_outcome).inc()
        if scanner_blocked:
            self.scanner_blocks_total.inc()
        if suggestion_count:
            self.suggestions_total.inc(suggestion_count)
        if error_class:
            self.errors_total.labels(error_class=error_class).inc()

    def render(self) -> tuple[bytes, str]:
        """Exposition-format body and content-type for a `/metrics`
        endpoint (wiring the endpoint itself is `glue/app.py`'s job)."""
        return generate_latest(self.registry), CONTENT_TYPE_LATEST
