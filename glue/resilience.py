"""Failure-safe wrappers for calls to external dependencies (Onyx,
OpenFGA, Claude, LLM Guard, Langfuse) and structured, client-safe error
reporting for the pipeline.

## Structured errors, no leaked internals

`PipelineError` and its subclasses carry two messages: `safe_message`
(what a client may ever see -- generic, no internals) and `detail`
(logged only, may contain the real exception text). Nothing in this
module ever puts a raw exception, stack trace, or dependency error string
where a client response could reach it -- see `glue.pipeline`'s handling
of these (once wired in) for where that boundary actually is.

## Request IDs

`current_request_id()` reads a contextvar, generating one on first use
within a task if none was set. Since it's a `contextvars.ContextVar`, it
propagates automatically through `await` calls within the same task
(that's what contextvars are for) without needing to be threaded through
every function signature by hand -- set it once per incoming request
(e.g. in a FastAPI middleware or the first pipeline call) and every
`PipelineError` raised downstream in that task picks it up.

## Cancellation

`call_with_retries` and `CircuitBreaker.call` both re-raise
`asyncio.CancelledError` immediately rather than treating it as a
retryable failure -- a classic bug in retry loops is catching a bare
`Exception` and accidentally swallowing cancellation, which breaks
upstream request-cancellation propagation (e.g. a client disconnecting
should actually stop the in-flight Claude call, not get silently retried
into a timeout).
"""
from __future__ import annotations

import asyncio
import contextvars
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


def new_request_id() -> str:
    return uuid.uuid4().hex


def current_request_id() -> str:
    """The request ID for the current task, generating and storing one on
    first access if none has been set yet."""
    request_id = _request_id_var.get()
    if request_id is None:
        request_id = new_request_id()
        _request_id_var.set(request_id)
    return request_id


def bind_request_id(request_id: str | None = None) -> str:
    """Explicitly set the request ID for the current task (e.g. from an
    inbound X-Request-ID header) instead of generating one. Returns the
    bound ID."""
    request_id = request_id or new_request_id()
    _request_id_var.set(request_id)
    return request_id


class PipelineError(Exception):
    """Base class for a failure at one pipeline stage.

    `safe_message` is written to be shown to a client as-is: generic,
    no dependency names, no exception text, no retrieved document
    content. `detail` is for logs only.
    """

    def __init__(self, safe_message: str, *, detail: str | None = None, request_id: str | None = None) -> None:
        super().__init__(safe_message)
        self.safe_message = safe_message
        self.detail = detail if detail is not None else safe_message
        self.request_id = request_id or current_request_id()

    def __str__(self) -> str:  # pragma: no cover -- logging convenience
        return f"[{self.request_id}] {self.safe_message} ({self.detail})"


class StageTimeoutError(PipelineError):
    pass


class DependencyUnavailableError(PipelineError):
    pass


class CircuitOpenError(PipelineError):
    pass


# --- timeout -------------------------------------------------------------


async def call_with_timeout(awaitable: Awaitable[T], *, timeout_seconds: float, stage: str) -> T:
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise StageTimeoutError(
            "The request took too long to process.",
            detail=f"{stage} exceeded {timeout_seconds}s timeout",
        ) from exc


# --- bounded retries -------------------------------------------------------


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.2
    max_delay_seconds: float = 2.0
    jitter: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

    def delay_for(self, attempt: int) -> float:
        """Exponential backoff for the delay *before* retry number
        `attempt` (1-indexed: the delay before the 2nd overall try is
        `delay_for(1)`)."""
        delay = min(self.max_delay_seconds, self.base_delay_seconds * (2 ** (attempt - 1)))
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay


async def call_with_retries(
    func: Callable[[], Awaitable[T]],
    *,
    stage: str,
    policy: RetryPolicy | None = None,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    policy = policy or RetryPolicy()
    last_exc: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await func()
        except asyncio.CancelledError:
            raise
        except retry_on as exc:  # noqa: PERF203 -- retry loop, intentional
            last_exc = exc
            if attempt == policy.max_attempts:
                break
            logger.warning("%s attempt %d/%d failed, retrying: %s", stage, attempt, policy.max_attempts, exc)
            await sleep(policy.delay_for(attempt))
    raise DependencyUnavailableError(
        "The service is temporarily unavailable. Please try again.",
        detail=f"{stage} failed after {policy.max_attempts} attempts: {last_exc}",
    ) from last_exc


# --- circuit breaker -----------------------------------------------------


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Stops calling a dependency that's already failing repeatedly,
    instead of piling up more timed-out/failed requests against it.

    - CLOSED: calls go through normally; `failure_threshold` consecutive
      failures trips it OPEN.
    - OPEN: calls are rejected immediately (`CircuitOpenError`, no call
      attempted) until `reset_timeout_seconds` has passed.
    - HALF_OPEN: the next call after the reset timeout is allowed through
      as a probe. Success closes the circuit; failure reopens it (and
      restarts the reset timeout).
    """

    def __init__(
        self,
        *,
        name: str,
        failure_threshold: int = 5,
        reset_timeout_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        self._name = name
        self._failure_threshold = failure_threshold
        self._reset_timeout_seconds = reset_timeout_seconds
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        if self._state is CircuitState.OPEN and self._opened_at is not None:
            if self._clock() - self._opened_at >= self._reset_timeout_seconds:
                return CircuitState.HALF_OPEN
        return self._state

    async def call(self, func: Callable[[], Awaitable[T]]) -> T:
        state = self.state
        if state is CircuitState.OPEN:
            raise CircuitOpenError(
                "The service is temporarily unavailable. Please try again.",
                detail=f"circuit '{self._name}' is open",
            )

        try:
            result = await func()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._record_failure(was_probe=state is CircuitState.HALF_OPEN)
            raise DependencyUnavailableError(
                "The service is temporarily unavailable. Please try again.",
                detail=f"circuit '{self._name}' call failed: {exc}",
            ) from exc

        self._record_success()
        return result

    def _record_success(self) -> None:
        self._consecutive_failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = None

    def _record_failure(self, *, was_probe: bool = False) -> None:
        self._consecutive_failures += 1
        if was_probe or self._consecutive_failures >= self._failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = self._clock()
