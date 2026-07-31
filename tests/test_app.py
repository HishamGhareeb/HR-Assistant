from fastapi.testclient import TestClient

from glue.app import create_app
from glue.pipeline import PipelineResult


class FakePipeline:
    async def handle_question(self, user_id, question):
        return PipelineResult(answer=f"{user_id}: {question}", suggestions=[], blocked=False)


def test_health_endpoint():
    with TestClient(create_app(FakePipeline())) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_question_requires_authenticated_identity():
    with TestClient(create_app(FakePipeline())) as client:
        response = client.post("/v1/questions", json={"question": "My leave balance?"})
    assert response.status_code == 401


def test_question_reaches_pipeline_with_trusted_identity():
    with TestClient(create_app(FakePipeline())) as client:
        response = client.post(
            "/v1/questions",
            headers={"X-User-ID": "sarah"},
            json={"question": "My leave balance?"},
        )
    assert response.status_code == 200
    assert response.json() == {
        "answer": "sarah: My leave balance?",
        "suggestions": [],
        "blocked": False,
    }


def test_health_starts_without_service_configuration(monkeypatch):
    for name in (
        "ANTHROPIC_API_KEY",
        "ONYX_API_URL",
        "OPENFGA_API_URL",
        "OPENFGA_STORE_ID",
    ):
        monkeypatch.delenv(name, raising=False)

    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_question_returns_service_unavailable_when_not_configured(monkeypatch):
    for name in (
        "ANTHROPIC_API_KEY",
        "ONYX_API_URL",
        "OPENFGA_API_URL",
        "OPENFGA_STORE_ID",
    ):
        monkeypatch.delenv(name, raising=False)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/questions",
            headers={"X-User-ID": "sarah"},
            json={"question": "My leave balance?"},
        )

    assert response.status_code == 503
    assert response.json()["detail"].startswith("HR Assistant is not configured:")
