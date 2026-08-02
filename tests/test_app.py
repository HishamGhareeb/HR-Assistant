"""API-level tests: signed bearer auth replaces X-User-ID, identity reaches
the pipeline, request IDs are bound/echoed, and the service degrades to
503 (not a crash) when unconfigured -- for both the pipeline and the new
auth verifier.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from prometheus_client import CollectorRegistry

from glue.admin_controls import InMemoryAdminControlStore, StaticHrAdminAuthorizer
from glue.app import create_app
from glue.auth import TokenVerifier, static_key_resolver
from glue.domain import Identity, Suggestion, SuggestionStatus
from glue.frappe_sync import SyncConfig, SyncEngine
from glue.observability import Metrics
from glue.pipeline import PipelineResult
from glue.suggestions import InMemorySuggestionStore, StaticHrReviewAuthorizer

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


def make_token(tenant_id="acme", user_id="sarah", issuer=ISSUER, audience=AUDIENCE, expires_in=3600):
    now = int(time.time())
    claims = {
        "iss": issuer, "aud": audience, "exp": now + expires_in, "iat": now,
        "tenant_id": tenant_id, "sub": user_id,
    }
    return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256", headers={"kid": "key-1"})


def make_verifier() -> TokenVerifier:
    return TokenVerifier(
        key_resolver=static_key_resolver({"key-1": PUBLIC_KEY}), issuer=ISSUER, audience=AUDIENCE
    )


class FakePipeline:
    def __init__(self):
        self.calls: list[tuple[Identity, str]] = []
        self.metrics = Metrics(CollectorRegistry())

    async def handle_question(self, identity: Identity, question: str) -> PipelineResult:
        self.calls.append((identity, question))
        return PipelineResult(answer=f"{identity.tenant_id}/{identity.user_id}: {question}", suggestions=[], blocked=False)


def build_client(pipeline=None, verifier=None) -> TestClient:
    return TestClient(create_app(pipeline or FakePipeline(), verifier or make_verifier()))


def build_review_client(store, reviewers=None, pipeline=None) -> TestClient:
    return TestClient(
        create_app(
            pipeline or FakePipeline(),
            make_verifier(),
            suggestion_store=store,
            review_authorizer=StaticHrReviewAuthorizer(reviewers or {"acme": ["hr-1"]}),
        )
    )


class FakeDocumentIndex:
    def __init__(self, fail_next: bool = False) -> None:
        self.documents: dict[str, dict] = {}
        self.fail_next = fail_next

    async def upsert(self, *, document_id, semantic_identifier, text, metadata):
        if self.fail_next:
            self.fail_next = False
            raise ConnectionError("onyx unavailable")
        already_existed = document_id in self.documents
        self.documents[document_id] = {
            "semantic_identifier": semantic_identifier,
            "text": text,
            "metadata": metadata,
        }
        return already_existed

    async def delete(self, document_id):
        self.documents.pop(document_id, None)


class FakeTupleWriter:
    def __init__(self) -> None:
        self.tuples: set[tuple[str, str, str]] = set()

    async def write_tuples(self, tuples):
        self.tuples.update(tuples)

    async def delete_tuples(self, tuples):
        for tuple_ in tuples:
            self.tuples.discard(tuple_)


class FakeTenantRoleSyncer:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, object]] = []

    async def sync_tenant_roles(self, *, tenant_id: str, store):
        self.calls.append((tenant_id, store))
        if self.fail:
            raise ConnectionError("openfga unavailable")
        return {"tenant_id": tenant_id, "written": 1, "deleted": 0}


def build_admin_client(
    store=None,
    admins=None,
    sync_engine=None,
    tenant_role_syncer=None,
) -> tuple[TestClient, InMemoryAdminControlStore, FakeDocumentIndex]:
    admin_store = store or InMemoryAdminControlStore()
    index = FakeDocumentIndex()
    engine = sync_engine or SyncEngine(index, FakeTupleWriter(), config=SyncConfig(hr_admin_user_ids=("hr-1",)))
    return (
        TestClient(
            create_app(
                FakePipeline(),
                make_verifier(),
                admin_store=admin_store,
                admin_authorizer=StaticHrAdminAuthorizer(admins or {"acme": ["hr-1"]}),
                sync_engine=engine,
                tenant_role_syncer=tenant_role_syncer,
            )
        ),
        admin_store,
        index,
    )


def make_suggestion(tenant_id="acme", suggestion_id="sug-1") -> Suggestion:
    return Suggestion(
        suggestion_id=suggestion_id,
        tenant_id=tenant_id,
        category="leave_expiring",
        reasoning="Carried-over leave expires soon.",
        record_reference="LEAVE-1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


# --- health / unauthenticated basics --------------------------------------


def test_health_endpoint():
    with build_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_question_without_authorization_header_is_rejected():
    with build_client() as client:
        response = client.post("/v1/questions", json={"question": "My leave balance?"})
    assert response.status_code == 401


def test_question_with_stale_x_user_id_header_alone_is_rejected():
    # The old internal handoff header must no longer be a valid substitute
    # for a signed token.
    with build_client() as client:
        response = client.post(
            "/v1/questions", headers={"X-User-ID": "sarah"}, json={"question": "My leave balance?"}
        )
    assert response.status_code == 401


def test_question_with_forged_token_is_rejected():
    other_private, _other_public = generate_keypair()
    forged = jwt.encode(
        {
            "iss": ISSUER, "aud": AUDIENCE, "exp": int(time.time()) + 3600,
            "tenant_id": "acme", "sub": "sarah",
        },
        other_private,
        algorithm="RS256",
        headers={"kid": "key-1"},  # claims the trusted kid, signed by the wrong key
    )
    with build_client() as client:
        response = client.post(
            "/v1/questions", headers={"Authorization": f"Bearer {forged}"}, json={"question": "q"}
        )
    assert response.status_code == 401


# --- happy path: identity reaches the pipeline -----------------------------


def test_valid_token_reaches_pipeline_with_verified_identity():
    pipeline = FakePipeline()
    token = make_token(tenant_id="acme", user_id="sarah")

    with build_client(pipeline=pipeline) as client:
        response = client.post(
            "/v1/questions", headers={"Authorization": f"Bearer {token}"}, json={"question": "My leave balance?"}
        )

    assert response.status_code == 200
    assert response.json() == {"answer": "acme/sarah: My leave balance?", "suggestions": [], "blocked": False}
    assert len(pipeline.calls) == 1
    identity, question = pipeline.calls[0]
    assert identity == Identity(tenant_id="acme", user_id="sarah")
    assert question == "My leave balance?"


def test_different_tenant_token_produces_different_identity():
    pipeline = FakePipeline()
    token = make_token(tenant_id="globex", user_id="david")

    with build_client(pipeline=pipeline) as client:
        client.post("/v1/questions", headers={"Authorization": f"Bearer {token}"}, json={"question": "q"})

    identity, _question = pipeline.calls[0]
    assert identity.tenant_id == "globex"
    assert identity.user_id == "david"


# --- HR suggestion review inbox ------------------------------------------


def test_review_inbox_requires_authorized_hr_reviewer_before_listing():
    store = InMemorySuggestionStore()
    store.create(make_suggestion())

    with build_review_client(store) as client:
        response = client.get("/v1/hr/suggestions", headers={"Authorization": f"Bearer {make_token(user_id='sarah')}"})

    assert response.status_code == 403


def test_review_inbox_lists_only_callers_tenant():
    store = InMemorySuggestionStore()
    store.create(make_suggestion("acme", "acme-sug"))
    store.create(make_suggestion("globex", "globex-sug"))

    with build_review_client(store) as client:
        response = client.get("/v1/hr/suggestions", headers={"Authorization": f"Bearer {make_token(user_id='hr-1')}"})

    assert response.status_code == 200
    assert [item["suggestion_id"] for item in response.json()] == ["acme-sug"]


def test_review_decision_approves_without_mutating_pipeline_or_frappe():
    store = InMemorySuggestionStore()
    store.create(make_suggestion())
    pipeline = FakePipeline()

    with build_review_client(store, pipeline=pipeline) as client:
        response = client.post(
            "/v1/hr/suggestions/sug-1/decision",
            headers={"Authorization": f"Bearer {make_token(user_id='hr-1')}"},
            json={"action": "approved", "note": "Verified by HR."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["decided_by"] == "hr-1"
    assert body["decision_history"][0]["note"] == "Verified by HR."
    assert pipeline.calls == []  # approval is a review record only; it does not call downstream mutation paths


def test_review_rejects_invalid_second_transition():
    store = InMemorySuggestionStore()
    store.create(make_suggestion())

    with build_review_client(store) as client:
        headers = {"Authorization": f"Bearer {make_token(user_id='hr-1')}"}
        first = client.post("/v1/hr/suggestions/sug-1/decision", headers=headers, json={"action": "rejected"})
        second = client.post("/v1/hr/suggestions/sug-1/decision", headers=headers, json={"action": "approved"})

    assert first.status_code == 200
    assert second.status_code == 409


# --- HR admin ingestion and access controls -------------------------------


def test_admin_controls_require_tenant_scoped_admin_authorization():
    client, _store, _index = build_admin_client()
    with client:
        response = client.get(
            "/v1/hr/admin/sources",
            headers={"Authorization": f"Bearer {make_token(user_id='sarah')}"},
        )

    assert response.status_code == 403


def test_admin_role_assignments_are_tenant_scoped_without_global_bypass():
    client, _store, _index = build_admin_client()
    with client:
        acme_headers = {"Authorization": f"Bearer {make_token(tenant_id='acme', user_id='hr-1')}"}
        globex_headers = {"Authorization": f"Bearer {make_token(tenant_id='globex', user_id='hr-1')}"}
        created = client.put(
            "/v1/hr/admin/access/roles/sarah",
            headers=acme_headers,
            json={"roles": ["employee", "manager"]},
        )
        acme_list = client.get("/v1/hr/admin/access/roles", headers=acme_headers)
        globex_list = client.get("/v1/hr/admin/access/roles", headers=globex_headers)

    assert created.status_code == 200
    assert created.json()["tenant_id"] == "acme"
    assert created.json()["roles"] == ["employee", "manager"]
    assert [assignment["user_id"] for assignment in acme_list.json()] == ["sarah"]
    assert globex_list.status_code == 403


def test_admin_role_assignment_triggers_optional_tenant_role_sync():
    syncer = FakeTenantRoleSyncer()
    client, store, _index = build_admin_client(tenant_role_syncer=syncer)

    with client:
        response = client.put(
            "/v1/hr/admin/access/roles/sarah",
            headers={"Authorization": f"Bearer {make_token(tenant_id='acme', user_id='hr-1')}"},
            json={"roles": ["employee", "manager"]},
        )

    assert response.status_code == 200
    assert syncer.calls == [("acme", store)]


def test_admin_role_assignment_surfaces_retryable_sync_failure():
    syncer = FakeTenantRoleSyncer(fail=True)
    client, _store, _index = build_admin_client(tenant_role_syncer=syncer)

    with client:
        response = client.put(
            "/v1/hr/admin/access/roles/sarah",
            headers={"Authorization": f"Bearer {make_token(tenant_id='acme', user_id='hr-1')}"},
            json={"roles": ["employee"]},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "role assignment saved but authorization sync failed; retry required"


def test_admin_synthetic_resync_records_status_and_index_metadata_without_frappe_mutation():
    client, store, index = build_admin_client()
    with client:
        response = client.post(
            "/v1/hr/admin/sync/resync",
            headers={"Authorization": f"Bearer {make_token(user_id='hr-1')}"},
            json={
                "source_id": "synthetic-fixture",
                "records": [
                    {
                        "doctype": "HR Policy",
                        "name": "POL-1",
                        "fields": {"title": "Leave", "body": "Employees get 21 days."},
                    }
                ],
            },
        )
        sources = client.get(
            "/v1/hr/admin/sources",
            headers={"Authorization": f"Bearer {make_token(user_id='hr-1')}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["created"] == 1
    assert body["failed"] == []
    assert sources.json()[0]["source_id"] == "synthetic-fixture"
    [indexed] = index.documents.values()
    assert indexed["metadata"] == {
        "tenant_id": "acme",
        "record_type": "policy_document",
        "classification": "public",
    }
    assert store.frappe_mutation_attempts == 0


def test_admin_resync_failure_is_visible_and_retryable():
    store = InMemoryAdminControlStore()
    index = FakeDocumentIndex(fail_next=True)
    engine = SyncEngine(index, FakeTupleWriter())
    client, _store, _unused_index = build_admin_client(store=store, sync_engine=engine)
    headers = {"Authorization": f"Bearer {make_token(user_id='hr-1')}"}
    payload = {
        "source_id": "synthetic-fixture",
        "records": [
            {
                "doctype": "HR Policy",
                "name": "POL-1",
                "fields": {"title": "Leave", "body": "Employees get 21 days."},
            }
        ],
    }

    with client:
        failed = client.post("/v1/hr/admin/sync/resync", headers=headers, json=payload)
        retried = client.post("/v1/hr/admin/sync/resync", headers=headers, json=payload)
        runs = client.get("/v1/hr/admin/sync/runs", headers=headers)

    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["failed"][0]["name"] == "POL-1"
    assert retried.json()["status"] == "completed"
    assert [run["status"] for run in runs.json()] == ["completed", "failed"]


def test_admin_synthetic_revoke_removes_indexed_data_safely():
    client, store, index = build_admin_client()
    headers = {"Authorization": f"Bearer {make_token(user_id='hr-1')}"}
    with client:
        client.post(
            "/v1/hr/admin/sync/resync",
            headers=headers,
            json={
                "source_id": "synthetic-fixture",
                "records": [
                    {
                        "doctype": "HR Policy",
                        "name": "POL-1",
                        "fields": {"title": "Leave", "body": "Employees get 21 days."},
                    }
                ],
            },
        )
        response = client.post(
            "/v1/hr/admin/sync/revoke",
            headers=headers,
            json={"source_id": "synthetic-fixture", "doctype": "HR Policy", "name": "POL-1"},
        )

    assert response.status_code == 200
    assert response.json()["deleted"] == 1
    assert index.documents == {}
    assert store.frappe_mutation_attempts == 0


# --- request ID propagation -------------------------------------------


def test_response_echoes_a_generated_request_id():
    with build_client() as client:
        response = client.get("/health")
    assert response.headers.get("X-Request-ID")


def test_response_echoes_a_caller_supplied_request_id():
    with build_client() as client:
        response = client.get("/health", headers={"X-Request-ID": "caller-req-123"})
    assert response.headers["X-Request-ID"] == "caller-req-123"


# --- metrics -------------------------------------------------------------


def test_metrics_endpoint_returns_prometheus_exposition_format():
    with build_client() as client:
        # Generate at least one request so there's something to render.
        token = make_token()
        client.post("/v1/questions", headers={"Authorization": f"Bearer {token}"}, json={"question": "q"})
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "hr_assistant_requests_total" in response.text


# --- unconfigured service degrades to 503, not a crash --------------------


REQUIRED_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "ONYX_API_URL",
    "ONYX_API_KEY",
    "OPENFGA_API_URL",
    "OPENFGA_STORE_ID",
    "AUTH_ISSUER",
    "AUTH_AUDIENCE",
    "AUTH_JWKS_URL",
    "AUTH_STATIC_KEYS_JSON",
    "AUDIT_PRIVACY_KEY",
)


def test_health_starts_without_any_service_configuration(monkeypatch):
    for name in REQUIRED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_question_returns_service_unavailable_when_pipeline_not_configured(monkeypatch):
    for name in REQUIRED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AUTH_ISSUER", ISSUER)
    monkeypatch.setenv("AUTH_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("AUTH_STATIC_KEYS_JSON", json.dumps({"key-1": PUBLIC_KEY}))

    token = make_token()
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/questions", headers={"Authorization": f"Bearer {token}"}, json={"question": "q"}
        )

    assert response.status_code == 503
    assert response.json()["detail"].startswith("HR Assistant is not configured:")


def test_question_returns_service_unavailable_when_auth_not_configured(monkeypatch):
    for name in REQUIRED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/questions", headers={"Authorization": "Bearer whatever"}, json={"question": "q"}
        )

    assert response.status_code == 503
    assert response.json()["detail"].startswith("HR Assistant is not configured:")
