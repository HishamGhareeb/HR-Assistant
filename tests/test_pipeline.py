"""Pipeline integration tests: identity threading, retrieval -> authorization
-> context budget -> Claude -> scanner -> schema validation, resilience
wrapping around each external call, and exactly-once audit/metrics
emission -- including on cross-tenant, dependency-failure, malformed-
output, and scanner-blocked paths.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

import pytest
from prometheus_client import CollectorRegistry

from glue.audit import AuditLogger, InMemoryAuditSink
from glue.domain import Identity
from glue.observability import Metrics
from glue.onyx_client import Document
from glue.openfga_client import OpenFgaFilter
from glue.pipeline import BLOCKED_RESPONSE, NO_INFO_RESPONSE, Pipeline
from glue.resilience import RetryPolicy, bind_request_id

PRIVACY_KEY = b"test-privacy-key"
FAST_RETRY_POLICY = RetryPolicy(max_attempts=3, base_delay_seconds=0, max_delay_seconds=0, jitter=False)


@pytest.fixture(autouse=True)
def _fresh_request_id():
    # asyncio Tasks copy the context that was current at task-creation
    # time, so a contextvar set by an unrelated test elsewhere in the
    # suite (e.g. test_observability.py binding a non-UUID request ID)
    # can otherwise leak in here -- audit.py validates the request_id
    # format strictly, so this needs to be a real one per test.
    bind_request_id()


def make_document(object_id: str, tenant_id: str = "acme", chunk: str = "chunk") -> Document:
    return Document(
        object_type="leave_record",
        object_id=object_id,
        chunk=chunk,
        tenant_id=tenant_id,
        source="onyx",
        retrieved_at=datetime.now(timezone.utc),
    )


class FakeOnyx:
    def __init__(self, candidates, error=None):
        self._candidates = candidates
        self._error = error
        self.calls: list[tuple[str, str | None]] = []

    async def search(self, question, *, tenant_id=None):
        self.calls.append((question, tenant_id))
        if self._error is not None:
            raise self._error
        return self._candidates


class FakeOpenFga:
    def __init__(self, authorized_ids, error=None):
        self._authorized_ids = authorized_ids
        self._error = error
        self.calls: list[tuple[str, str | None]] = []

    async def filter_authorized(self, user_id, documents, *, tenant_id=None):
        self.calls.append((user_id, tenant_id))
        if self._error is not None:
            raise self._error
        return [d for d in documents if d.object_id in self._authorized_ids]


class FakeClaude:
    def __init__(self, raw_response: str):
        self._raw_response = raw_response
        self.received_context_chunks: list[str] | None = None
        self.thread_id: int | None = None

    def complete(self, question, context_chunks):
        self.received_context_chunks = list(context_chunks)
        self.thread_id = threading.get_ident()
        return self._raw_response


class FakeGuard:
    def __init__(self, is_valid: bool, sanitized: str | None = None):
        self._is_valid = is_valid
        self._sanitized = sanitized
        self.scanned_output: str | None = None
        self.thread_id: int | None = None

    def scan(self, prompt, output):
        self.scanned_output = output
        self.thread_id = threading.get_ident()
        return (self._sanitized if self._sanitized is not None else output), self._is_valid


class FakeTrace:
    def __init__(self):
        self.spans: list[dict] = []
        self.generations: list[dict] = []

    def span(self, **kwargs):
        self.spans.append(kwargs)
        return self

    def generation(self, **kwargs):
        self.generations.append(kwargs)
        return self


class FakeTracer:
    def __init__(self):
        self.trace = FakeTrace()

    def trace_request(self):
        return self.trace


def build_pipeline(
    *,
    authorized_ids=frozenset(),
    onyx_docs=None,
    onyx_error=None,
    openfga=None,
    openfga_error=None,
    raw_claude_response=None,
    guard_valid=True,
    guard_sanitized=None,
):
    docs = onyx_docs if onyx_docs is not None else [make_document("sarah_leave"), make_document("david_leave")]
    audit_sink = InMemoryAuditSink()
    onyx = FakeOnyx(docs, error=onyx_error)
    fga = openfga if openfga is not None else FakeOpenFga(authorized_ids, error=openfga_error)
    claude = FakeClaude(raw_claude_response or json.dumps({"answer": "ok", "suggestions": []}))
    guard = FakeGuard(guard_valid, guard_sanitized)
    tracer = FakeTracer()
    pipeline = Pipeline(
        onyx=onyx,
        openfga=fga,
        claude=claude,
        guard=guard,
        tracer=tracer,
        audit_logger=AuditLogger(audit_sink, privacy_key=PRIVACY_KEY),
        metrics=Metrics(CollectorRegistry()),
        retry_policy=FAST_RETRY_POLICY,
    )
    return pipeline, {"onyx": onyx, "openfga": fga, "claude": claude, "guard": guard, "tracer": tracer, "audit": audit_sink}


IDENTITY = Identity(tenant_id="acme", user_id="sarah")


# --- identity threading ---------------------------------------------------


@pytest.mark.asyncio
async def test_identity_tenant_and_user_are_passed_to_onyx_and_openfga():
    pipeline, fakes = build_pipeline(authorized_ids={"sarah_leave"})

    await pipeline.handle_question(IDENTITY, "How much leave do I have?")

    assert fakes["onyx"].calls == [("How much leave do I have?", "acme")]
    assert fakes["openfga"].calls == [("sarah", "acme")]


# --- happy path -------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_returns_answer_and_suggestions():
    raw = json.dumps(
        {
            "answer": "You have 5 days left.",
            "suggestions": [{"category": "leave_expiring", "reasoning": "Expires soon.", "record_reference": "sarah_leave"}],
        }
    )
    pipeline, fakes = build_pipeline(authorized_ids={"sarah_leave"}, raw_claude_response=raw)

    result = await pipeline.handle_question(IDENTITY, "How much leave do I have?")

    assert result.answer == "You have 5 days left."
    assert result.blocked is False
    assert len(result.suggestions) == 1
    assert result.suggestions[0].category == "leave_expiring"

    event = fakes["audit"].events[0]
    assert event.model_outcome == "answered"
    assert event.scanner_outcome == "passed"
    assert event.retrieval_count == 2
    assert event.authorized_count == 1
    assert event.suggestion_count == 1


@pytest.mark.asyncio
async def test_trace_outputs_do_not_include_raw_answer_or_suggestion_reasoning():
    raw = json.dumps(
        {
            "answer": "Sarah's SSN is 123-45-6789.",
            "suggestions": [
                {
                    "category": "leave_expiring",
                    "reasoning": "Sarah's sensitive leave details.",
                    "record_reference": "salary-slip-123",
                }
            ],
        }
    )
    pipeline, fakes = build_pipeline(authorized_ids={"sarah_leave"}, raw_claude_response=raw)

    await pipeline.handle_question(IDENTITY, "What is Sarah's SSN?")

    trace = fakes["tracer"].trace
    serialized_trace = json.dumps(trace.generations) + json.dumps(trace.spans)
    assert "123-45-6789" not in serialized_trace
    assert "Sarah's sensitive leave details" not in serialized_trace
    assert "salary-slip-123" not in serialized_trace
    assert "leave_expiring" in serialized_trace
    assert "suggestion_count" in serialized_trace


@pytest.mark.asyncio
async def test_no_authorized_documents_returns_no_info_response():
    pipeline, fakes = build_pipeline(authorized_ids=set())

    result = await pipeline.handle_question(IDENTITY, "what is sarah's leave balance?")

    assert result.answer == NO_INFO_RESPONSE
    assert result.blocked is False
    event = fakes["audit"].events[0]
    assert event.model_outcome == "no_info"
    assert event.authorized_count == 0


# --- cross-tenant document rejection -------------------------------------


@pytest.mark.asyncio
async def test_cross_tenant_documents_never_reach_claude():
    # Real OpenFgaFilter (not a fake): every candidate is tagged for a
    # different tenant than the caller's identity, so filter_authorized's
    # own tenant check drops all of them before it would ever call
    # OpenFGA -- proving the rejection happens at that boundary, not just
    # because a fake said so.
    real_openfga = OpenFgaFilter(api_url="https://fga.invalid", store_id="unused")
    foreign_docs = [make_document("sarah_leave", tenant_id="globex")]
    pipeline, fakes = build_pipeline(onyx_docs=foreign_docs, openfga=real_openfga)

    result = await pipeline.handle_question(IDENTITY, "How much leave do I have?")

    assert result.answer == NO_INFO_RESPONSE
    assert fakes["claude"].received_context_chunks is None  # Claude never called
    event = fakes["audit"].events[0]
    assert event.authorized_count == 0


# --- OpenFGA failure denies all -------------------------------------------


@pytest.mark.asyncio
async def test_openfga_failure_denies_all_and_fails_closed():
    pipeline, fakes = build_pipeline(openfga_error=ConnectionError("openfga unreachable"))

    result = await pipeline.handle_question(IDENTITY, "How much leave do I have?")

    assert result.blocked is False
    assert result.suggestions == []
    assert fakes["claude"].received_context_chunks is None  # never reached Claude
    event = fakes["audit"].events[0]
    assert event.model_outcome == "error"
    assert event.error_class is not None
    assert event.authorized_count == 0


# --- malformed Claude JSON fails closed ------------------------------------


@pytest.mark.asyncio
async def test_malformed_claude_json_fails_closed():
    pipeline, fakes = build_pipeline(authorized_ids={"sarah_leave"}, raw_claude_response="not valid json at all")

    result = await pipeline.handle_question(IDENTITY, "How much leave do I have?")

    assert result.answer == BLOCKED_RESPONSE
    assert result.suggestions == []
    assert result.blocked is True
    event = fakes["audit"].events[0]
    assert event.model_outcome == "blocked"


@pytest.mark.asyncio
async def test_claude_json_missing_required_field_fails_closed():
    raw = json.dumps({"suggestions": []})  # missing "answer"
    pipeline, fakes = build_pipeline(authorized_ids={"sarah_leave"}, raw_claude_response=raw)

    result = await pipeline.handle_question(IDENTITY, "How much leave do I have?")

    assert result.answer == BLOCKED_RESPONSE
    assert result.blocked is True


# --- scanner block fails closed ------------------------------------------


@pytest.mark.asyncio
async def test_scanner_block_withholds_response():
    pipeline, fakes = build_pipeline(
        authorized_ids={"sarah_leave"},
        raw_claude_response=json.dumps({"answer": "leaked SSN: 123-45-6789", "suggestions": []}),
        guard_valid=False,
    )

    result = await pipeline.handle_question(IDENTITY, "How much leave do I have?")

    assert result.answer == BLOCKED_RESPONSE
    assert result.suggestions == []
    assert result.blocked is True
    event = fakes["audit"].events[0]
    assert event.scanner_outcome == "blocked"
    assert event.model_outcome == "blocked"


@pytest.mark.asyncio
async def test_scanner_receives_raw_text_before_any_json_parsing():
    pipeline, fakes = build_pipeline(
        authorized_ids={"sarah_leave"}, raw_claude_response=json.dumps({"answer": "hi", "suggestions": []})
    )

    await pipeline.handle_question(IDENTITY, "q")

    assert fakes["guard"].scanned_output == json.dumps({"answer": "hi", "suggestions": []})


@pytest.mark.asyncio
async def test_pipeline_delivers_the_scanners_sanitized_payload():
    sanitized = json.dumps({"answer": "Your leave balance is [REDACTED].", "suggestions": []})
    pipeline, fakes = build_pipeline(
        authorized_ids={"sarah_leave"},
        raw_claude_response=json.dumps({"answer": "Your leave balance is 123-45-6789.", "suggestions": []}),
        guard_valid=True,
        guard_sanitized=sanitized,
    )

    result = await pipeline.handle_question(IDENTITY, "q")

    assert result.answer == "Your leave balance is [REDACTED]."


# --- audit privacy -----------------------------------------------------


@pytest.mark.asyncio
async def test_audit_event_never_carries_question_answer_or_user_id():
    pipeline, fakes = build_pipeline(
        authorized_ids={"sarah_leave"},
        raw_claude_response=json.dumps({"answer": "Sarah's SSN is 123-45-6789.", "suggestions": []}),
    )

    result = await pipeline.handle_question(IDENTITY, "What is sarah's SSN?")
    assert result.answer == "Sarah's SSN is 123-45-6789."  # sanity: the answer really is in the response

    event = fakes["audit"].events[0]
    serialized = event.canonical_json()
    assert "SSN" not in serialized
    assert "123-45-6789" not in serialized
    assert "sarah" not in serialized.lower() or "actor_ref" in serialized  # only via the HMAC pseudonym field name
    assert IDENTITY.user_id not in serialized
    assert "What is sarah's SSN" not in serialized


@pytest.mark.asyncio
async def test_audit_event_is_emitted_exactly_once_per_call():
    pipeline, fakes = build_pipeline(authorized_ids={"sarah_leave"})
    await pipeline.handle_question(IDENTITY, "q")
    assert len(fakes["audit"].events) == 1


@pytest.mark.asyncio
async def test_audit_event_emitted_even_on_unexpected_error():
    class ExplodingOnyx(FakeOnyx):
        async def search(self, question, *, tenant_id=None):
            raise RuntimeError("boom -- not a PipelineError")

    pipeline, fakes = build_pipeline()
    fakes["onyx"] = ExplodingOnyx([])
    pipeline._onyx = fakes["onyx"]

    result = await pipeline.handle_question(IDENTITY, "q")

    assert result.blocked is False
    assert len(fakes["audit"].events) == 1
    assert fakes["audit"].events[0].model_outcome == "error"


# --- resilience wrapping (timeout/retry/circuit) around external calls -----


@pytest.mark.asyncio
async def test_onyx_dependency_failure_is_retried_then_fails_closed():
    calls = 0

    class FlakyOnyx(FakeOnyx):
        async def search(self, question, *, tenant_id=None):
            nonlocal calls
            calls += 1
            raise ConnectionError("onyx down")

    pipeline, fakes = build_pipeline()
    pipeline._onyx = FlakyOnyx([])

    result = await pipeline.handle_question(IDENTITY, "q")

    assert calls > 1  # retried at least once before giving up
    assert result.blocked is False
    assert result.answer  # a safe, non-empty fallback message
    event = fakes["audit"].events[0]
    assert event.model_outcome == "error"


# --- context budget applied before Claude ----------------------------------


@pytest.mark.asyncio
async def test_context_budget_bounds_what_claude_receives():
    huge_docs = [make_document(f"doc-{i}", chunk="x" * 10_000) for i in range(5)]
    pipeline, fakes = build_pipeline(authorized_ids={f"doc-{i}" for i in range(5)}, onyx_docs=huge_docs)

    await pipeline.handle_question(IDENTITY, "q")

    assert fakes["claude"].received_context_chunks is not None
    assert len(fakes["claude"].received_context_chunks) < 5  # budget dropped some


# --- scanner/Claude run off the event loop thread ---------------------


@pytest.mark.asyncio
async def test_claude_and_guard_run_off_the_event_loop_thread():
    event_loop_thread = threading.get_ident()
    pipeline, fakes = build_pipeline(authorized_ids={"sarah_leave"})

    await pipeline.handle_question(IDENTITY, "q")

    assert fakes["claude"].thread_id is not None
    assert fakes["claude"].thread_id != event_loop_thread
    assert fakes["guard"].thread_id is not None
    assert fakes["guard"].thread_id != event_loop_thread
