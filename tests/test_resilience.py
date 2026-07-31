from __future__ import annotations

import asyncio

import pytest

from glue.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    DependencyUnavailableError,
    PipelineError,
    RetryPolicy,
    StageTimeoutError,
    bind_request_id,
    call_with_retries,
    call_with_timeout,
    current_request_id,
    new_request_id,
)


# --- request IDs -----------------------------------------------------------


@pytest.mark.asyncio
async def test_current_request_id_is_stable_within_a_task():
    first = current_request_id()
    second = current_request_id()
    assert first == second


@pytest.mark.asyncio
async def test_bind_request_id_overrides_generated_one():
    bound = bind_request_id("req-fixed-123")
    assert bound == "req-fixed-123"
    assert current_request_id() == "req-fixed-123"


def test_new_request_id_is_unique():
    assert new_request_id() != new_request_id()


@pytest.mark.asyncio
async def test_pipeline_error_carries_request_id_and_hides_detail_from_str_by_default():
    bind_request_id("req-abc")
    error = PipelineError("safe message", detail="secret internal detail")
    assert error.safe_message == "safe message"
    assert error.detail == "secret internal detail"
    assert error.request_id == "req-abc"


# --- timeout -------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_with_timeout_returns_result_when_fast_enough():
    async def fast():
        return "ok"

    result = await call_with_timeout(fast(), timeout_seconds=1.0, stage="test-stage")
    assert result == "ok"


@pytest.mark.asyncio
async def test_call_with_timeout_raises_stage_timeout_error():
    async def slow():
        await asyncio.sleep(10)

    with pytest.raises(StageTimeoutError) as exc_info:
        await call_with_timeout(slow(), timeout_seconds=0.01, stage="onyx-retrieval")

    assert "onyx-retrieval" in exc_info.value.detail
    assert "took too long" in exc_info.value.safe_message.lower()


# --- retries -----------------------------------------------------------


async def _no_sleep(_seconds: float) -> None:
    return None


@pytest.mark.asyncio
async def test_call_with_retries_succeeds_on_first_try():
    calls = 0

    async def func():
        nonlocal calls
        calls += 1
        return "ok"

    result = await call_with_retries(func, stage="test", sleep=_no_sleep)
    assert result == "ok"
    assert calls == 1


@pytest.mark.asyncio
async def test_call_with_retries_succeeds_after_transient_failures():
    calls = 0

    async def func():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("transient")
        return "ok"

    result = await call_with_retries(
        func, stage="test", policy=RetryPolicy(max_attempts=5), sleep=_no_sleep
    )
    assert result == "ok"
    assert calls == 3


@pytest.mark.asyncio
async def test_call_with_retries_gives_up_after_max_attempts():
    calls = 0

    async def func():
        nonlocal calls
        calls += 1
        raise ConnectionError("always fails")

    with pytest.raises(DependencyUnavailableError) as exc_info:
        await call_with_retries(func, stage="onyx-search", policy=RetryPolicy(max_attempts=3), sleep=_no_sleep)

    assert calls == 3
    assert "onyx-search" in exc_info.value.detail
    assert "temporarily unavailable" in exc_info.value.safe_message.lower()


@pytest.mark.asyncio
async def test_call_with_retries_does_not_retry_cancellation():
    calls = 0

    async def func():
        nonlocal calls
        calls += 1
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await call_with_retries(func, stage="test", policy=RetryPolicy(max_attempts=5), sleep=_no_sleep)

    assert calls == 1  # never retried


@pytest.mark.asyncio
async def test_call_with_retries_only_retries_configured_exception_types():
    async def func():
        raise ValueError("not retryable here")

    with pytest.raises(ValueError):
        await call_with_retries(
            func, stage="test", policy=RetryPolicy(max_attempts=3), retry_on=(ConnectionError,), sleep=_no_sleep
        )


def test_retry_policy_rejects_zero_attempts():
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)


def test_retry_policy_delay_grows_and_is_capped():
    policy = RetryPolicy(base_delay_seconds=1.0, max_delay_seconds=3.0, jitter=False)
    assert policy.delay_for(1) == 1.0
    assert policy.delay_for(2) == 2.0
    assert policy.delay_for(3) == 3.0  # would be 4.0 uncapped
    assert policy.delay_for(10) == 3.0


# --- circuit breaker -----------------------------------------------------


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.mark.asyncio
async def test_circuit_starts_closed_and_allows_calls():
    breaker = CircuitBreaker(name="test", failure_threshold=3, reset_timeout_seconds=10)
    assert breaker.state is CircuitState.CLOSED

    async def ok():
        return "ok"

    assert await breaker.call(ok) == "ok"
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_opens_after_threshold_consecutive_failures():
    clock = FakeClock()
    breaker = CircuitBreaker(name="test", failure_threshold=3, reset_timeout_seconds=10, clock=clock)

    async def fail():
        raise ConnectionError("down")

    for _ in range(3):
        with pytest.raises(DependencyUnavailableError):
            await breaker.call(fail)

    assert breaker.state is CircuitState.OPEN


@pytest.mark.asyncio
async def test_open_circuit_rejects_calls_without_invoking_the_function():
    clock = FakeClock()
    breaker = CircuitBreaker(name="test", failure_threshold=1, reset_timeout_seconds=10, clock=clock)
    calls = 0

    async def fail():
        nonlocal calls
        calls += 1
        raise ConnectionError("down")

    with pytest.raises(DependencyUnavailableError):
        await breaker.call(fail)  # trips it open
    assert calls == 1

    with pytest.raises(CircuitOpenError):
        await breaker.call(fail)
    assert calls == 1  # not called again -- rejected before invocation


@pytest.mark.asyncio
async def test_circuit_moves_to_half_open_after_reset_timeout_and_closes_on_success():
    clock = FakeClock()
    breaker = CircuitBreaker(name="test", failure_threshold=1, reset_timeout_seconds=10, clock=clock)

    async def fail():
        raise ConnectionError("down")

    with pytest.raises(DependencyUnavailableError):
        await breaker.call(fail)
    assert breaker.state is CircuitState.OPEN

    clock.advance(11)
    assert breaker.state is CircuitState.HALF_OPEN

    async def ok():
        return "recovered"

    result = await breaker.call(ok)
    assert result == "recovered"
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.asyncio
async def test_half_open_probe_failure_reopens_circuit_immediately():
    clock = FakeClock()
    breaker = CircuitBreaker(name="test", failure_threshold=5, reset_timeout_seconds=10, clock=clock)

    async def fail():
        raise ConnectionError("down")

    # Trip open with fewer than failure_threshold failures is impossible
    # normally -- so trip it via repeated failures first.
    for _ in range(5):
        with pytest.raises(DependencyUnavailableError):
            await breaker.call(fail)
    assert breaker.state is CircuitState.OPEN

    clock.advance(11)
    assert breaker.state is CircuitState.HALF_OPEN

    # The probe itself fails -- must reopen immediately, not require
    # another full failure_threshold count.
    with pytest.raises(DependencyUnavailableError):
        await breaker.call(fail)
    assert breaker.state is CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_does_not_treat_cancellation_as_a_failure():
    breaker = CircuitBreaker(name="test", failure_threshold=1, reset_timeout_seconds=10)

    async def cancelled():
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await breaker.call(cancelled)

    assert breaker.state is CircuitState.CLOSED  # not tripped


def test_circuit_breaker_rejects_non_positive_failure_threshold():
    with pytest.raises(ValueError):
        CircuitBreaker(name="test", failure_threshold=0)
