import json
import threading

import pytest

from glue.claude_client import AssistantResponse, Suggestion
from glue.onyx_client import Document
from glue.pipeline import BLOCKED_RESPONSE, NO_INFO_RESPONSE, Pipeline


class FakeOnyx:
    def __init__(self, candidates):
        self._candidates = candidates

    async def search(self, question):
        return self._candidates


class FakeOpenFga:
    def __init__(self, authorized_ids):
        self._authorized_ids = authorized_ids

    async def filter_authorized(self, user_id, documents):
        return [d for d in documents if d.object_id in self._authorized_ids]


class FakeClaude:
    def __init__(self, response):
        self._response = response

    def answer(self, question, context_chunks):
        return self._response


class FakeGuard:
    def __init__(self, is_valid):
        self._is_valid = is_valid
        self.scanned_output = None
        self.thread_id = None

    def scan(self, prompt, output):
        self.scanned_output = output
        self.thread_id = threading.get_ident()
        return output, self._is_valid


class FakeSpan:
    def __init__(self):
        self.generations = []

    def span(self, **kwargs):
        return self

    def generation(self, **kwargs):
        self.generations.append(kwargs)
        return self


class FakeTracer:
    def __init__(self):
        self.trace = FakeSpan()

    def trace_request(self):
        return self.trace


def make_pipeline(authorized_ids, claude_response=None, guard_valid=True, guard=None, tracer=None):
    docs = [Document("leave_record", "sarah_leave", "chunk-a"), Document("leave_record", "david_leave", "chunk-b")]
    return Pipeline(
        onyx=FakeOnyx(docs),
        openfga=FakeOpenFga(authorized_ids),
        claude=FakeClaude(claude_response or AssistantResponse(answer="ok", suggestions=[])),
        guard=guard or FakeGuard(guard_valid),
        tracer=tracer or FakeTracer(),
    )


@pytest.mark.asyncio
async def test_no_authorized_documents_returns_no_info_response():
    pipeline = make_pipeline(authorized_ids=set())
    result = await pipeline.handle_question("david", "what is sarah's leave balance?")
    assert result.answer == NO_INFO_RESPONSE
    assert result.blocked is False


@pytest.mark.asyncio
async def test_authorized_documents_reach_claude():
    pipeline = make_pipeline(
        authorized_ids={"sarah_leave"},
        claude_response=AssistantResponse(answer="you have 5 days left", suggestions=[]),
    )
    result = await pipeline.handle_question("sarah", "how much leave do I have?")
    assert result.answer == "you have 5 days left"
    assert result.blocked is False


@pytest.mark.asyncio
async def test_llm_guard_block_withholds_response_without_silent_edit():
    tracer = FakeTracer()
    pipeline = make_pipeline(
        authorized_ids={"sarah_leave"},
        claude_response=AssistantResponse(answer="leaked SSN: 123-45-6789", suggestions=[]),
        guard_valid=False,
        tracer=tracer,
    )
    result = await pipeline.handle_question("sarah", "how much leave do I have?")
    assert result.answer == BLOCKED_RESPONSE
    assert result.suggestions == []
    assert result.blocked is True
    assert tracer.trace.generations == [{"name": "claude-answer", "output": {"blocked": True}}]


@pytest.mark.asyncio
async def test_llm_guard_scans_and_withholds_sensitive_suggestions():
    guard = FakeGuard(is_valid=False)
    pipeline = make_pipeline(
        authorized_ids={"sarah_leave"},
        claude_response=AssistantResponse(
            answer="I found something for HR to review.",
            suggestions=[
                Suggestion(
                    category="Payroll",
                    reasoning="Leaked account: 123456789",
                    record_reference="salary-42",
                )
            ],
        ),
        guard=guard,
    )

    result = await pipeline.handle_question("sarah", "Any issues?")

    scanned = json.loads(guard.scanned_output)
    assert scanned["suggestions"][0]["reasoning"] == "Leaked account: 123456789"
    assert result.answer == BLOCKED_RESPONSE
    assert result.suggestions == []
    assert result.blocked is True


@pytest.mark.asyncio
async def test_pipeline_delivers_and_traces_the_scanner_sanitized_payload():
    class SanitizingGuard(FakeGuard):
        def scan(self, prompt, output):
            super().scan(prompt, output)
            return json.dumps(
                {
                    "answer": "Your leave balance is [REDACTED].",
                    "suggestions": [
                        {
                            "category": "Payroll",
                            "reasoning": "Review [REDACTED].",
                            "record_reference": "salary-42",
                        }
                    ],
                }
            ), True

    tracer = FakeTracer()
    pipeline = make_pipeline(
        authorized_ids={"sarah_leave"},
        claude_response=AssistantResponse(
            answer="Your leave balance is 123-45-6789.",
            suggestions=[Suggestion("Payroll", "Review 123456789.", "salary-42")],
        ),
        guard=SanitizingGuard(is_valid=True),
        tracer=tracer,
    )

    result = await pipeline.handle_question("employee-secret", "Question secret")

    assert result.answer == "Your leave balance is [REDACTED]."
    assert result.suggestions[0].reasoning == "Review [REDACTED]."
    assert tracer.trace.generations == [
        {
            "name": "claude-answer",
            "output": {
                "answer": "Your leave balance is [REDACTED].",
                "suggestions": [
                    {
                        "category": "Payroll",
                        "reasoning": "Review [REDACTED].",
                        "record_reference": "salary-42",
                    }
                ],
            },
        }
    ]


@pytest.mark.asyncio
async def test_llm_guard_scan_runs_off_the_event_loop_thread():
    guard = FakeGuard(is_valid=True)
    event_loop_thread = threading.get_ident()
    pipeline = make_pipeline(authorized_ids={"sarah_leave"}, guard=guard)

    await pipeline.handle_question("sarah", "My leave balance?")

    assert guard.thread_id is not None
    assert guard.thread_id != event_loop_thread
