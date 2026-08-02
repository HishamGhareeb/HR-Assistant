"""API-level tests for answer feedback, unanswered-question tracking, HR
escalation resolution, and the quality-analytics dashboard (HIS-23).
"""
from __future__ import annotations

import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from glue.app import create_app
from glue.auth import TokenVerifier, static_key_resolver
from glue.feedback import InMemoryFeedbackStore, StaticHrFeedbackAuthorizer
from glue.observability import Metrics
from glue.pipeline import PipelineResult

ISSUER = "https://auth.hr-assistant.internal"
AUDIENCE = "hr-assistant-api"


def generate_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


PRIVATE_KEY, PUBLIC_KEY = generate_keypair()


def make_token(tenant_id="acme", user_id="sarah", expires_in=3600):
    now = int(time.time())
    claims = {
        "iss": ISSUER, "aud": AUDIENCE, "exp": now + expires_in, "iat": now,
        "tenant_id": tenant_id, "sub": user_id,
    }
    return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256", headers={"kid": "key-1"})


def make_verifier() -> TokenVerifier:
    return TokenVerifier(
        key_resolver=static_key_resolver({"key-1": PUBLIC_KEY}), issuer=ISSUER, audience=AUDIENCE
    )


class FakePipeline:
    def __init__(self):
        self.metrics = Metrics(CollectorRegistry())

    async def handle_question(self, identity, question) -> PipelineResult:
        return PipelineResult(
            answer="", suggestions=[], blocked=False, request_id="test-request-id", model_outcome="answered"
        )


def build_client(store=None, reviewers=None) -> TestClient:
    return TestClient(
        create_app(
            FakePipeline(),
            make_verifier(),
            feedback_store=store or InMemoryFeedbackStore(),
            feedback_authorizer=StaticHrFeedbackAuthorizer(reviewers or {"acme": ["hr-1"]}),
        )
    )


def auth_headers(user_id="sarah") -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user_id=user_id)}"}


# --- submitting feedback (self-service, no HR authorization needed) ---------


def test_submit_helpful_feedback():
    with build_client() as client:
        response = client.post(
            "/v1/questions/req-1/feedback",
            headers=auth_headers(),
            json={"question": "My leave balance?", "answer": "You have 5 days left.", "helpful": True},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["helpful"] is True
    assert body["escalated"] is False
    assert body["request_id"] == "req-1"
    assert body["user_id"] == "sarah"


def test_submit_not_helpful_feedback_requires_reason_code():
    with build_client() as client:
        response = client.post(
            "/v1/questions/req-1/feedback",
            headers=auth_headers(),
            json={"question": "q", "answer": "a", "helpful": False},
        )
    assert response.status_code == 422


def test_submit_not_helpful_feedback_is_automatically_escalated():
    with build_client() as client:
        response = client.post(
            "/v1/questions/req-1/feedback",
            headers=auth_headers(),
            json={
                "question": "What's the maternity leave policy?",
                "answer": "I don't have information on that.",
                "helpful": False,
                "reason_code": "incomplete",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is True
    assert body["resolved"] is False


def test_submit_feedback_without_authorization_header_is_rejected():
    with build_client() as client:
        response = client.post(
            "/v1/questions/req-1/feedback",
            json={"question": "q", "answer": "a", "helpful": True},
        )
    assert response.status_code == 401


# --- HR feedback list/unanswered/quality-summary/resolve --------------------


def test_hr_feedback_list_requires_authorization():
    with build_client() as client:
        response = client.get("/v1/hr/feedback", headers=auth_headers(user_id="not-hr"))
    assert response.status_code == 403


def test_hr_feedback_list_is_tenant_scoped():
    store = InMemoryFeedbackStore()
    with build_client(store=store) as client:
        client.post(
            "/v1/questions/req-1/feedback",
            headers=auth_headers(user_id="sarah"),
            json={"question": "q", "answer": "a", "helpful": True},
        )
        client.post(
            "/v1/questions/req-2/feedback",
            headers={"Authorization": f"Bearer {make_token(tenant_id='globex', user_id='alex')}"},
            json={"question": "q", "answer": "a", "helpful": True},
        )
        response = client.get("/v1/hr/feedback", headers=auth_headers(user_id="hr-1"))

    assert response.status_code == 200
    assert [item["request_id"] for item in response.json()] == ["req-1"]


def test_hr_feedback_list_filters_by_helpful_and_escalated():
    store = InMemoryFeedbackStore()
    with build_client(store=store) as client:
        client.post(
            "/v1/questions/req-helpful/feedback",
            headers=auth_headers(),
            json={"question": "q", "answer": "a", "helpful": True},
        )
        client.post(
            "/v1/questions/req-not-helpful/feedback",
            headers=auth_headers(),
            json={"question": "q", "answer": "a", "helpful": False, "reason_code": "incorrect"},
        )

        only_escalated = client.get(
            "/v1/hr/feedback", headers=auth_headers(user_id="hr-1"), params={"escalated_only": True}
        )

    assert only_escalated.status_code == 200
    assert [item["request_id"] for item in only_escalated.json()] == ["req-not-helpful"]


def test_hr_can_resolve_escalated_feedback():
    store = InMemoryFeedbackStore()
    with build_client(store=store) as client:
        submitted = client.post(
            "/v1/questions/req-1/feedback",
            headers=auth_headers(),
            json={
                "question": "q", "answer": "a", "helpful": False, "reason_code": "outdated",
            },
        )
        feedback_id = submitted.json()["feedback_id"]

        response = client.post(
            f"/v1/hr/feedback/{feedback_id}/resolve",
            headers=auth_headers(user_id="hr-1"),
            json={"note": "Updated the source document."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["resolved"] is True
    assert body["resolution"]["resolved_by"] == "hr-1"
    assert body["resolution"]["note"] == "Updated the source document."


def test_resolving_helpful_feedback_is_rejected():
    store = InMemoryFeedbackStore()
    with build_client(store=store) as client:
        submitted = client.post(
            "/v1/questions/req-1/feedback",
            headers=auth_headers(),
            json={"question": "q", "answer": "a", "helpful": True},
        )
        feedback_id = submitted.json()["feedback_id"]

        response = client.post(
            f"/v1/hr/feedback/{feedback_id}/resolve", headers=auth_headers(user_id="hr-1"), json={}
        )

    assert response.status_code == 409


def test_resolving_unknown_feedback_returns_404():
    with build_client() as client:
        response = client.post(
            "/v1/hr/feedback/does-not-exist/resolve", headers=auth_headers(user_id="hr-1"), json={}
        )
    assert response.status_code == 404


def test_unanswered_questions_are_listed_for_hr():
    from glue.feedback import UnansweredQuestion
    from datetime import datetime, timezone

    store = InMemoryFeedbackStore()
    store.record_unanswered(
        UnansweredQuestion(
            tenant_id="acme", user_id="sarah", request_id="req-3",
            question="Do we offer sabbaticals?", model_outcome="no_info",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )

    with build_client(store=store) as client:
        response = client.get("/v1/hr/feedback/unanswered", headers=auth_headers(user_id="hr-1"))

    assert response.status_code == 200
    assert [item["question"] for item in response.json()] == ["Do we offer sabbaticals?"]


def test_quality_summary_requires_authorization_and_is_aggregate_only():
    store = InMemoryFeedbackStore()
    with build_client(store=store) as client:
        denied = client.get("/v1/hr/feedback/quality-summary", headers=auth_headers(user_id="sarah"))
        assert denied.status_code == 403

        client.post(
            "/v1/questions/req-1/feedback",
            headers=auth_headers(),
            json={"question": "q", "answer": "a", "helpful": True},
        )
        client.post(
            "/v1/questions/req-2/feedback",
            headers=auth_headers(),
            json={"question": "q2", "answer": "a2", "helpful": False, "reason_code": "irrelevant"},
        )

        response = client.get("/v1/hr/feedback/quality-summary", headers=auth_headers(user_id="hr-1"))

    assert response.status_code == 200
    body = response.json()
    assert body["total_feedback"] == 2
    assert body["helpful_count"] == 1
    assert body["not_helpful_count"] == 1
    assert body["helpful_rate"] == 0.5
    assert body["reason_code_counts"] == {"irrelevant": 1}
    assert body["unresolved_escalation_count"] == 1
    assert "question" not in body
    assert "answer" not in body
