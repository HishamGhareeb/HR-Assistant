from __future__ import annotations

import pytest

from glue.context_budget import fit_to_budget


def test_all_chunks_kept_when_well_under_budget():
    chunks = ["short chunk one", "short chunk two"]
    result = fit_to_budget(chunks, max_tokens=1000)
    assert result.kept == chunks
    assert result.dropped_count == 0


def test_chunks_dropped_once_budget_exceeded():
    # chars_per_token=4, max_tokens=10 -> 40 char budget: "a"*20 + "b"*20
    # fits exactly (40 <= 40); "c"*20 would push it to 60 and is dropped.
    chunks = ["a" * 20, "b" * 20, "c" * 20]
    result = fit_to_budget(chunks, max_tokens=10, chars_per_token=4)
    assert result.kept == ["a" * 20, "b" * 20]
    assert result.dropped_count == 1


def test_stops_at_first_overflow_rather_than_skipping_to_a_smaller_later_chunk():
    chunks = ["a" * 30, "b" * 5, "c" * 5]  # budget only fits the first
    result = fit_to_budget(chunks, max_tokens=5, chars_per_token=4)  # 20 char budget
    assert result.kept == ["a" * 30]  # first chunk kept even though it alone overflows
    assert result.dropped_count == 2


def test_always_keeps_at_least_one_chunk_even_if_it_alone_exceeds_budget():
    chunks = ["x" * 1000]
    result = fit_to_budget(chunks, max_tokens=1, chars_per_token=4)
    assert result.kept == chunks
    assert result.dropped_count == 0


def test_empty_input_returns_empty_result():
    result = fit_to_budget([], max_tokens=1000)
    assert result.kept == []
    assert result.dropped_count == 0
    assert result.estimated_tokens == 0


def test_estimated_tokens_reflects_kept_chunks_only():
    chunks = ["a" * 20, "b" * 20, "c" * 20]
    result = fit_to_budget(chunks, max_tokens=10, chars_per_token=4)
    assert result.estimated_tokens == (len("a" * 20) + len("b" * 20)) // 4


def test_rejects_non_positive_max_tokens():
    with pytest.raises(ValueError):
        fit_to_budget(["chunk"], max_tokens=0)
