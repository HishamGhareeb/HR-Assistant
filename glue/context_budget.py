"""Keeps the context assembled from authorized document chunks within a
token budget before it's sent to Claude.

There's no offline tokenizer for Claude's models available locally, and
counting via the Anthropic API (`client.messages.count_tokens`) would mean
a network round trip just to decide how much context to send -- so token
counts here are a deliberately conservative **character-based
approximation** (`chars_per_token`, default 4), not an exact count. Treat
`max_tokens` as a budget to stay comfortably under, not a hard guarantee
of the real token count Claude's tokenizer would produce.
"""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class BudgetResult:
    kept: list[str]
    dropped_count: int
    estimated_tokens: int


def fit_to_budget(
    chunks: list[str],
    *,
    max_tokens: int,
    chars_per_token: int = DEFAULT_CHARS_PER_TOKEN,
) -> BudgetResult:
    """Keep chunks in their given order (assumed most-relevant-first, per
    retrieval ranking) up to `max_tokens`, then stop -- rather than
    skipping an over-budget chunk to see if a smaller, less relevant one
    later still fits. Always keeps at least the first chunk even if it
    alone exceeds the budget: sending one oversized but most-relevant
    chunk is preferable to sending no context at all.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")

    max_chars = max_tokens * chars_per_token
    kept: list[str] = []
    used_chars = 0

    for chunk in chunks:
        chunk_len = len(chunk)
        if kept and used_chars + chunk_len > max_chars:
            break
        kept.append(chunk)
        used_chars += chunk_len

    return BudgetResult(
        kept=kept,
        dropped_count=len(chunks) - len(kept),
        estimated_tokens=used_chars // chars_per_token,
    )
