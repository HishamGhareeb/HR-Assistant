"""Privacy-minimising observability for request lifecycle metadata.

Langfuse is optional.  Traces deliberately contain no user identifier and no
raw question.  The pipeline only adds scanner-approved response content.
"""
from __future__ import annotations

from langfuse import Langfuse


class _NoopTrace:
    """Drop-in trace object used when observability is not configured."""

    def span(self, **_kwargs):
        return self

    def generation(self, **_kwargs):
        return self


class Tracer:
    def __init__(self, public_key: str, secret_key: str, host: str) -> None:
        self._client = (
            Langfuse(public_key=public_key, secret_key=secret_key, host=host)
            if public_key and secret_key
            else None
        )

    def trace_request(self):
        """Start a trace without attaching identity or request content."""
        if self._client is None:
            return _NoopTrace()
        return self._client.trace(name="hr-assistant-request")
