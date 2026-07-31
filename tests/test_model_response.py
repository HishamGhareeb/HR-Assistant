from __future__ import annotations

import json

import pytest

from glue.model_response import ModelResponseValidationError, validate_model_response


def test_valid_response_parses():
    raw = json.dumps({"answer": "You have 5 days of leave.", "suggestions": []})
    result = validate_model_response(raw)
    assert result.answer == "You have 5 days of leave."
    assert result.suggestions == []


def test_valid_response_with_suggestions_parses():
    raw = json.dumps(
        {
            "answer": "Approved.",
            "suggestions": [
                {"category": "leave_expiring", "reasoning": "Expires in 7 days.", "record_reference": "sarah_leave"}
            ],
        }
    )
    result = validate_model_response(raw)
    assert len(result.suggestions) == 1
    assert result.suggestions[0].category == "leave_expiring"


def test_suggestion_record_reference_may_be_null():
    raw = json.dumps(
        {"answer": "ok", "suggestions": [{"category": "x", "reasoning": "y", "record_reference": None}]}
    )
    result = validate_model_response(raw)
    assert result.suggestions[0].record_reference is None


def test_malformed_json_raises_validation_error():
    with pytest.raises(ModelResponseValidationError):
        validate_model_response("{not valid json")


def test_non_object_json_raises_validation_error():
    with pytest.raises(ModelResponseValidationError):
        validate_model_response(json.dumps(["answer", "suggestions"]))


def test_missing_answer_field_raises_validation_error():
    with pytest.raises(ModelResponseValidationError):
        validate_model_response(json.dumps({"suggestions": []}))


def test_blank_answer_raises_validation_error():
    with pytest.raises(ModelResponseValidationError):
        validate_model_response(json.dumps({"answer": "", "suggestions": []}))


def test_suggestion_missing_required_field_raises_validation_error():
    raw = json.dumps({"answer": "ok", "suggestions": [{"category": "x"}]})  # missing reasoning
    with pytest.raises(ModelResponseValidationError):
        validate_model_response(raw)


def test_answer_exceeding_max_length_raises_validation_error():
    raw = json.dumps({"answer": "x" * 8_001, "suggestions": []})
    with pytest.raises(ModelResponseValidationError):
        validate_model_response(raw)


def test_too_many_suggestions_raises_validation_error():
    raw = json.dumps(
        {"answer": "ok", "suggestions": [{"category": "x", "reasoning": "y"} for _ in range(21)]}
    )
    with pytest.raises(ModelResponseValidationError):
        validate_model_response(raw)


def test_wrong_type_for_suggestions_raises_validation_error():
    raw = json.dumps({"answer": "ok", "suggestions": "not-a-list"})
    with pytest.raises(ModelResponseValidationError):
        validate_model_response(raw)


def test_error_message_does_not_include_raw_model_text_verbatim_as_only_content():
    # A ModelResponseValidationError's message is for logs, not clients --
    # but even so it should describe the failure, not silently swallow it.
    try:
        validate_model_response("not json at all")
    except ModelResponseValidationError as exc:
        assert "not valid JSON" in str(exc)
    else:
        pytest.fail("expected ModelResponseValidationError")
