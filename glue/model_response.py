"""Validates Claude's structured JSON output against a strict schema, so a
malformed or unexpected response degrades to a safe fallback instead of a
raw parse error (or, worse, partially-parsed content) reaching a client.

Claude is instructed (see `glue/claude_client.py`'s `SYSTEM_PROMPT`) to
return exactly `{"answer": str, "suggestions": [...]}` -- but a model
response is still untrusted input as far as this codebase's own contracts
are concerned (`docs/ARCHITECTURE.md` trust boundary #4: "Model output is
untrusted until the output scanner passes it"). `validate_model_response`
is the schema half of that boundary; `glue/llm_guard_scan.py` is the
content half.
"""
from __future__ import annotations

import json

from pydantic import BaseModel, Field, ValidationError

MAX_ANSWER_LENGTH = 8_000
MAX_SUGGESTIONS = 20


class ModelResponseValidationError(Exception):
    """Claude's raw output text was not valid JSON, or didn't match the
    expected schema. Callers must treat this as a safe-fallback case (the
    pipeline's existing "no information" or "held for review" responses)
    -- never surface the raw text or this exception's message to a
    client, since the raw text may echo back retrieved (and therefore
    untrusted) document content."""


class SuggestionPayload(BaseModel):
    model_config = {"frozen": True}

    category: str = Field(min_length=1, max_length=200)
    reasoning: str = Field(min_length=1, max_length=2_000)
    record_reference: str | None = Field(default=None, max_length=200)


class ModelResponsePayload(BaseModel):
    model_config = {"frozen": True}

    answer: str = Field(min_length=1, max_length=MAX_ANSWER_LENGTH)
    suggestions: list[SuggestionPayload] = Field(default_factory=list, max_length=MAX_SUGGESTIONS)


def validate_model_response(raw_text: str) -> ModelResponsePayload:
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ModelResponseValidationError(f"model output was not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ModelResponseValidationError(f"model output was valid JSON but not an object: {type(parsed).__name__}")

    try:
        return ModelResponsePayload.model_validate(parsed)
    except ValidationError as exc:
        raise ModelResponseValidationError(f"model output did not match the expected schema: {exc}") from exc
