"""Langfuse tracing: every retrieval, permission check, Claude call, and
LLM Guard scan gets logged here so a request is fully auditable end to end."""
from __future__ import annotations

from langfuse import Langfuse


class Tracer:
    def __init__(self, public_key: str, secret_key: str, host: str) -> None:
        self._client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

    def trace_request(self, user_id: str, question: str):
        return self._client.trace(
            name="hr-assistant-request",
            user_id=user_id,
            input={"question": question},
        )
