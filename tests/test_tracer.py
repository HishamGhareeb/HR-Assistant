from unittest.mock import Mock, patch

from glue.tracer import Tracer


def test_tracer_uses_langfuse_v2_trace_api_without_identity_or_question():
    client = Mock()
    trace = Mock()
    client.trace.return_value = trace

    with patch("glue.tracer.Langfuse", return_value=client):
        tracer = Tracer("public", "secret", "https://langfuse.example")
        result = tracer.trace_request()

    assert result is trace
    client.trace.assert_called_once_with(
        name="hr-assistant-request",
    )


def test_tracer_is_noop_without_complete_langfuse_credentials():
    with patch("glue.tracer.Langfuse") as langfuse:
        trace = Tracer("", "", "https://langfuse.example").trace_request()

    langfuse.assert_not_called()
    assert trace.span(name="safe", output={"count": 1}) is trace
    assert trace.generation(name="safe", output={"blocked": False}) is trace
