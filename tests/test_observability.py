from __future__ import annotations

import asyncio
import logging

import pytest
from prometheus_client import CollectorRegistry

from glue.observability import Metrics, safe_call, safe_call_async
from glue.resilience import bind_request_id


def test_optional_sync_tracing_failure_is_noop(caplog) -> None:
    bind_request_id("request-observe")
    with caplog.at_level(logging.ERROR):
        assert safe_call(lambda: (_ for _ in ()).throw(RuntimeError("do not expose me")), component="langfuse") is None
    assert "optional_component_failed" in caplog.text
    assert "request-observe" in caplog.text
    assert "do not expose me" not in caplog.text


@pytest.mark.asyncio
async def test_optional_async_tracing_failure_is_noop() -> None:
    async def fail():
        raise RuntimeError("unavailable")
    assert await safe_call_async(fail, component="langfuse") is None


@pytest.mark.asyncio
async def test_cancellation_is_not_swallowed() -> None:
    async def cancelled():
        raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await safe_call_async(cancelled, component="langfuse")


def test_metrics_are_aggregate_only_and_renderable() -> None:
    metrics = Metrics(CollectorRegistry())
    metrics.record_request(
        retrieval_count=5, authorized_count=3, model_outcome="answered",
        suggestion_count=2, scanner_blocked=False,
    )
    body, content_type = metrics.render()
    rendered = body.decode()
    assert "hr_assistant_requests_total" in rendered
    assert "hr_assistant_retrieval_candidates" in rendered
    assert "request_id" not in rendered
    assert "text/plain" in content_type
