"""API-level tests for the Bahrain payroll rule-pack endpoints (HIS-59).

Covers: HR-admin authorization gating, valid and rule-violating payloads for
WPS/SIO-wage-update/EOSB, citation/explanation metadata on every response,
and the "supported: false" fail-closed shape for statutory rates that are
not yet source-backed (rather than a bare 4xx/5xx).
"""
from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from glue.admin_controls import StaticHrAdminAuthorizer
from glue.app import create_app
from glue.auth import TokenVerifier, static_key_resolver
from glue.observability import Metrics
from glue.pipeline import PipelineResult
from prometheus_client import CollectorRegistry

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


def make_token(tenant_id="acme", user_id="hr-1", expires_in=3600):
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
        return PipelineResult(answer="", suggestions=[], blocked=False)


def build_client(admins=None) -> TestClient:
    return TestClient(
        create_app(
            FakePipeline(),
            make_verifier(),
            admin_authorizer=StaticHrAdminAuthorizer(admins or {"acme": ["hr-1"]}),
        )
    )


def auth_headers(user_id="hr-1") -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user_id=user_id)}"}


# --- authorization gating ----------------------------------------------------


def test_wps_validate_requires_hr_admin_authorization():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/wps/validate",
            headers=auth_headers(user_id="not-hr"),
            json=VALID_WPS_PAYLOAD,
        )
    assert response.status_code == 403


def test_wps_validate_without_authorization_header_is_rejected():
    with build_client() as client:
        response = client.post("/v1/hr/payroll/bahrain/wps/validate", json=VALID_WPS_PAYLOAD)
    assert response.status_code == 401


# --- WPS compliance validation -----------------------------------------------

VALID_WPS_PAYLOAD = {
    "payroll_month": "2026-08",
    "scheduled_transfer_date": "2026-08-20",
    "actual_transfer_date": "2026-08-25",
    "worker_payments": [
        {
            "employee_full_name": "Fatima Al Khalifa",
            "employee_id_number": "820100123",
            "wage_amount": "500.000",
            "payment_date": "2026-08-25",
            "employee_account_identifier": "BH00ACME0000000001",
            "employer_account_number": "BH00ACME0000000099",
            "employer_id_cr_number": "12345-1",
            "fixed_salary": "400.000",
            "social_allowance": "50.000",
            "variable_salary": "50.000",
            "payment_status": "paid",
        }
    ],
    "approvals": [
        {"actor_user_id": "maker-1", "role": "maker", "action": "prepare", "acted_at": "2026-08-19"},
        {"actor_user_id": "checker-1", "role": "checker", "action": "approve", "acted_at": "2026-08-20"},
    ],
}


def test_wps_validate_valid_payload_returns_valid_true_with_citations():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/wps/validate",
            headers=auth_headers(),
            json=VALID_WPS_PAYLOAD,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True
    assert body["errors"] == []
    assert len(body["citations"]) == 3
    assert all(c["instrument"] for c in body["citations"])


def test_wps_validate_record_cap_violation_returns_error():
    payload = dict(VALID_WPS_PAYLOAD)
    payload["worker_payments"] = VALID_WPS_PAYLOAD["worker_payments"] * 1001
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/wps/validate",
            headers=auth_headers(),
            json=payload,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert any(e["code"] == "wps_file_record_cap_exceeded" for e in body["errors"])


# --- SIO wage-update validation ----------------------------------------------

VALID_SIO_WAGE_UPDATE_PAYLOAD = {
    "update_type": "annual",
    "previous_cpr_number": "820100123",
    "submitted_cpr_number": "820100123",
    "previous_employee_name": "Fatima Al Khalifa",
    "submitted_employee_name": "Fatima Al Khalifa",
    "previous_total_earnings": "500.000",
    "submitted_total_previous_earnings": "500.000",
    "previous_components": {"basic_salary": "400.000", "social_allowance": "50.000"},
    "new_components": {"basic_salary": "440.000", "social_allowance": "55.000"},
}


def test_sio_wage_update_valid_payload_returns_valid_true_with_citations():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/sio-wage-update/validate",
            headers=auth_headers(),
            json=VALID_SIO_WAGE_UPDATE_PAYLOAD,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True
    assert body["errors"] == []
    assert len(body["citations"]) == 5
    assert body["contribution_scope_components"]["basic_salary"] == "440.000"


def test_sio_wage_update_salary_decrease_is_rejected():
    payload = dict(VALID_SIO_WAGE_UPDATE_PAYLOAD)
    payload["new_components"] = {"basic_salary": "300.000", "social_allowance": "50.000"}
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/sio-wage-update/validate",
            headers=auth_headers(),
            json=payload,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert any(e["code"] == "sio_salary_decrease_not_permitted" for e in body["errors"])


def test_sio_wage_update_increase_cap_exceeded_is_rejected():
    payload = dict(VALID_SIO_WAGE_UPDATE_PAYLOAD)
    payload["new_components"] = {"basic_salary": "900.000", "social_allowance": "50.000"}
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/sio-wage-update/validate",
            headers=auth_headers(),
            json=payload,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert any(e["code"] == "sio_salary_increase_cap_exceeded" for e in body["errors"])


# --- EOSB eligibility ---------------------------------------------------------


def test_eosb_eligibility_eligible_case():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/eosb/eligibility",
            headers=auth_headers(),
            json={
                "sector": "private",
                "nationality_category": "non_bahraini",
                "employment_injuries_branch_covered": True,
                "social_insurance_law_article_3_excluded": False,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["reasons"] == []
    assert len(body["citations"]) == 2


def test_eosb_eligibility_ineligible_bahraini_case():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/eosb/eligibility",
            headers=auth_headers(),
            json={
                "sector": "private",
                "nationality_category": "bahraini",
                "employment_injuries_branch_covered": True,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert len(body["reasons"]) == 1


# --- EOSB gratuity, pre/post-1-March-2024 split -------------------------------


def test_eosb_gratuity_spanning_boundary_reports_both_portions():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/eosb/gratuity",
            headers=auth_headers(),
            json={
                "monthly_basic_salary": "900",
                "monthly_social_allowance": "100",
                "hire_date": "2020-03-01",
                "termination_date": "2026-03-01",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["pre_march_2024_employer_direct_liability"] == "2502.740"
    assert body["post_march_2024_sio_funded_amount"] == "1000.000"
    assert body["total_amount"] == "3502.740"
    assert len(body["figures"]) == 7


def test_eosb_gratuity_negative_wage_base_returns_422():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/eosb/gratuity",
            headers=auth_headers(),
            json={
                "monthly_basic_salary": "-1",
                "monthly_social_allowance": "0",
                "hire_date": "2024-03-01",
                "termination_date": "2025-03-01",
            },
        )
    assert response.status_code == 422


# --- EOSB monthly contribution, Article 13 transition-aware -------------------


def test_eosb_monthly_contribution_supported_flat_rate_for_long_pre_2024_tenure():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/eosb/monthly-contribution",
            headers=auth_headers(),
            json={"hire_date": "2018-01-01", "monthly_wage": "1000", "as_of": "2024-03-01"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["result"]["contribution_rate_percent"] == "8.4"
    assert body["result"]["employer_monthly_contribution_amount"] == "84.000"


def test_eosb_monthly_contribution_unsupported_before_scheme_start():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/eosb/monthly-contribution",
            headers=auth_headers(),
            json={"hire_date": "2023-01-01", "monthly_wage": "1000", "as_of": "2024-02-29"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is False
    assert body["result"] is None
    assert body["unsupported"]["requires_hr_review"] is True


# --- EOSB employer non-payment penalty ----------------------------------------


def test_eosb_employer_penalty_range():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/eosb/employer-penalty",
            headers=auth_headers(),
            json={"unpaid_contribution_amount": "100"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["minimum"] == "100.000"
    assert body["maximum"] == "300.000"


# --- SIO contributions ---------------------------------------------------------


def test_sio_contribution_bahraini_pension_employee_is_supported():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/sio-contributions/calculate",
            headers=auth_headers(),
            json={
                "worker_category": "bahraini_private",
                "branch": "old_age_disability_death",
                "payer": "employee",
                "monthly_wage": "1000",
                "as_of": "2026-01-01",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["result"]["rate_percent"] == "7"
    assert body["result"]["amount"] == "70.000"
    assert body["result"]["figure"]["citation"]["instrument"]


def test_sio_contribution_bahraini_pension_employer_share_is_unsupported():
    """Deliberately not registered -- see docs/BAHRAIN_RATE_VERSIONING.md."""
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/sio-contributions/calculate",
            headers=auth_headers(),
            json={
                "worker_category": "bahraini_private",
                "branch": "old_age_disability_death",
                "payer": "employer",
                "monthly_wage": "1000",
                "as_of": "2026-01-01",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is False
    assert body["unsupported"]["requires_hr_review"] is True


def test_sio_contribution_unemployment_labour_fund_share_is_supported():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/sio-contributions/calculate",
            headers=auth_headers(),
            json={
                "worker_category": "non_bahraini_private",
                "branch": "unemployment",
                "payer": "labour_fund",
                "monthly_wage": "1000",
                "as_of": "2026-01-01",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["result"]["amount"] == "10.000"


def test_sio_contribution_negative_wage_returns_422():
    with build_client() as client:
        response = client.post(
            "/v1/hr/payroll/bahrain/sio-contributions/calculate",
            headers=auth_headers(),
            json={
                "worker_category": "bahraini_private",
                "branch": "old_age_disability_death",
                "payer": "employee",
                "monthly_wage": "-1",
                "as_of": "2026-01-01",
            },
        )
    assert response.status_code == 422
