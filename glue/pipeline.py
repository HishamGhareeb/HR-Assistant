"""End-to-end request pipeline: Onyx retrieval -> OpenFGA filtering ->
Claude -> LLM Guard -> Langfuse trace. This is the only place these pieces
are wired together -- every delivery channel (WhatsApp, etc.) just calls
`handle_question`."""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from dataclasses import dataclass

from .claude_client import AssistantResponse, ClaudeClient, Suggestion
from .llm_guard_scan import OutputScanner
from .onyx_client import OnyxClient
from .openfga_client import OpenFgaFilter
from .tracer import Tracer

NO_INFO_RESPONSE = "I don't have information on that."
BLOCKED_RESPONSE = "That response was flagged by an automated safety check and held for review."


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
    ) -> None:
        self._onyx = onyx
        self._openfga = openfga
        self._claude = claude
        self._guard = guard
        self._tracer = tracer

    async def handle_question(self, user_id: str, question: str) -> PipelineResult:
        trace = self._tracer.trace_request()

        candidates = await self._onyx.search(question)
        trace.span(name="onyx-retrieval", output={"candidate_count": len(candidates)})

        authorized = await self._openfga.filter_authorized(user_id, candidates)
        trace.span(name="openfga-filter", output={"authorized_count": len(authorized)})

        if not authorized:
            trace.span(name="result", output={"answer": NO_INFO_RESPONSE})
            return PipelineResult(answer=NO_INFO_RESPONSE, suggestions=[], blocked=False)

        response: AssistantResponse = await asyncio.to_thread(
            self._claude.answer,
            question,
            [d.chunk for d in authorized],
        )
        # Never record raw model output before it passes the safety scan.
        # Suggestions are user-visible output too, so the complete payload is
        # scanned as one unit.
        generated_output = json.dumps(
            {
                "answer": response.answer,
                "suggestions": [asdict(suggestion) for suggestion in response.suggestions],
            },
            ensure_ascii=False,
        )
        sanitized_output, is_valid = await asyncio.to_thread(
            self._guard.scan,
            question,
            generated_output,
        )
        trace.span(name="llm-guard-scan", output={"is_valid": is_valid})

        if not is_valid:
            trace.generation(name="claude-answer", output={"blocked": True})
            trace.span(name="result", output={"answer": BLOCKED_RESPONSE, "blocked": True})
            return PipelineResult(answer=BLOCKED_RESPONSE, suggestions=[], blocked=True)

        # Use the scanner's value, never the original model object, for both
        # delivery and observability.  If a scanner returns malformed JSON,
        # fail closed instead of risking an unscanned partial response.
        try:
            safe_payload = json.loads(sanitized_output)
            safe_answer = safe_payload["answer"]
            safe_suggestions = [Suggestion(**item) for item in safe_payload["suggestions"]]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            trace.generation(name="claude-answer", output={"blocked": True})
            trace.span(name="result", output={"answer": BLOCKED_RESPONSE, "blocked": True})
            return PipelineResult(answer=BLOCKED_RESPONSE, suggestions=[], blocked=True)

        safe_response = {"answer": safe_answer, "suggestions": safe_payload["suggestions"]}
        trace.generation(name="claude-answer", output=safe_response)
        trace.span(name="result", output={"answer": safe_answer, "blocked": False})
        return PipelineResult(answer=safe_answer, suggestions=safe_suggestions, blocked=False)
