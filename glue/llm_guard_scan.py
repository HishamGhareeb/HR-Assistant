"""Output safety net: scan Claude's response for leaked PII/sensitive data
before it's sent to the user. This is a last line of defense, not the
primary control -- OpenFGA filtering is what actually enforces access."""
from __future__ import annotations


class OutputScanner:
    def __init__(self) -> None:
        from llm_guard.output_scanners import Sensitive

        self._scanner = Sensitive(redact=False)

    def scan(self, prompt: str, output: str) -> tuple[str, bool]:
        sanitized, is_valid, _risk_score = self._scanner.scan(prompt, output)
        return sanitized, is_valid
