import pytest

from glue.claude_client import AssistantResponse
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

    def scan(self, prompt, output):
        return output, self._is_valid


class FakeSpan:
    def span(self, **kwargs):
        return self

    def generation(self, **kwargs):
        return self


class FakeTracer:
    def trace_request(self, user_id, question):
        return FakeSpan()


def make_pipeline(authorized_ids, claude_response=None, guard_valid=True):
    docs = [Document("leave_record", "sarah_leave", "chunk-a"), Document("leave_record", "david_leave", "chunk-b")]
    return Pipeline(
        onyx=FakeOnyx(docs),
        openfga=FakeOpenFga(authorized_ids),
        claude=FakeClaude(claude_response or AssistantResponse(answer="ok", suggestions=[])),
        guard=FakeGuard(guard_valid),
        tracer=FakeTracer(),
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
    pipeline = make_pipeline(
        authorized_ids={"sarah_leave"},
        claude_response=AssistantResponse(answer="leaked SSN: 123-45-6789", suggestions=[]),
        guard_valid=False,
    )
    result = await pipeline.handle_question("sarah", "how much leave do I have?")
    assert result.answer == BLOCKED_RESPONSE
    assert result.blocked is True
