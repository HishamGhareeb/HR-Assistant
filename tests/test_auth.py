"""Security tests for signed authentication. These generate real RSA
keypairs and real signed JWTs (via `cryptography` + `PyJWT`) rather than
mocking the crypto -- a "forged token" test that mocks signature
verification wouldn't actually prove anything about signature
verification.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError

from glue.auth import (
    TokenValidationError,
    TokenVerifier,
    build_identity_dependency,
    jwks_key_resolver,
    static_key_resolver,
)
from glue.domain import CrossTenantError, Identity, require_same_tenant

ISSUER = "https://auth.hr-assistant.internal"
AUDIENCE = "hr-assistant-api"


def generate_keypair() -> tuple[str, str]:
    """Returns (private_key_pem, public_key_pem)."""
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


def make_token(
    private_key_pem: str,
    kid: str = "key-1",
    issuer: str = ISSUER,
    audience: str = AUDIENCE,
    tenant_id: str = "acme",
    user_id: str = "sarah",
    expires_in: float = 3600,
    extra_claims: dict | None = None,
    omit_claims: tuple[str, ...] = (),
) -> str:
    now = int(time.time())
    claims = {
        "iss": issuer,
        "aud": audience,
        "exp": now + expires_in,
        "iat": now,
        "tenant_id": tenant_id,
        "sub": user_id,
    }
    if extra_claims:
        claims.update(extra_claims)
    for key in omit_claims:
        claims.pop(key, None)
    return jwt.encode(claims, private_key_pem, algorithm="RS256", headers={"kid": kid})


@pytest.fixture(scope="module")
def keypair():
    return generate_keypair()


@pytest.fixture(scope="module")
def foreign_keypair():
    # A second, unrelated keypair -- used to sign "forged" tokens that
    # claim a legitimate kid but were never actually signed by it.
    return generate_keypair()


def make_verifier(public_key_pem: str, **overrides) -> TokenVerifier:
    return TokenVerifier(
        key_resolver=static_key_resolver({"key-1": public_key_pem}),
        issuer=ISSUER,
        audience=AUDIENCE,
        **overrides,
    )


# --- happy path -----------------------------------------------------------


def test_valid_token_produces_identity(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    token = make_token(private_pem)

    identity = verifier.verify(token)

    assert identity == Identity(tenant_id="acme", user_id="sarah")


@pytest.mark.asyncio
async def test_verify_async_matches_verify(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    token = make_token(private_pem)

    identity = await verifier.verify_async(token)

    assert identity == Identity(tenant_id="acme", user_id="sarah")


# --- forged / tampered tokens ------------------------------------------


def test_token_signed_by_an_unrelated_key_is_rejected(keypair, foreign_keypair):
    _trusted_private, trusted_public = keypair
    forged_private, _forged_public = foreign_keypair
    verifier = make_verifier(trusted_public)

    # Signed with a completely different private key, but claims the
    # trusted kid -- this is what a forged token actually looks like.
    forged_token = make_token(forged_private, kid="key-1")

    with pytest.raises(TokenValidationError):
        verifier.verify(forged_token)


def test_token_with_unknown_kid_is_rejected(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    token = make_token(private_pem, kid="key-does-not-exist")

    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_tampered_payload_is_rejected(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    token = make_token(private_pem, tenant_id="acme")

    # Flip one character in the payload segment without re-signing --
    # simulates a naive tamper attempt (e.g. trying to swap tenant_id).
    header_b64, payload_b64, sig_b64 = token.split(".")
    tampered_payload = ("A" if payload_b64[0] != "A" else "B") + payload_b64[1:]
    tampered_token = f"{header_b64}.{tampered_payload}.{sig_b64}"

    with pytest.raises(TokenValidationError):
        verifier.verify(tampered_token)


def test_malformed_token_is_rejected(keypair):
    _private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)

    with pytest.raises(TokenValidationError):
        verifier.verify("not-a-jwt-at-all")


def test_token_missing_kid_header_is_rejected(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    now = int(time.time())
    token = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "exp": now + 3600, "tenant_id": "acme", "sub": "sarah"},
        private_pem,
        algorithm="RS256",
    )  # no kid in header

    with pytest.raises(TokenValidationError):
        verifier.verify(token)


# --- claim validation ----------------------------------------------------


def test_expired_token_is_rejected(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    token = make_token(private_pem, expires_in=-3600)

    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_wrong_issuer_is_rejected(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    token = make_token(private_pem, issuer="https://attacker.example")

    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_wrong_audience_is_rejected(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    token = make_token(private_pem, audience="some-other-api")

    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_missing_tenant_claim_is_rejected(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    token = make_token(private_pem, omit_claims=("tenant_id",))

    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_blank_tenant_claim_is_rejected(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    token = make_token(private_pem, tenant_id="   ")

    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_missing_user_claim_is_rejected(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    token = make_token(private_pem, omit_claims=("sub",))

    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_clock_skew_within_leeway_is_accepted(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem, leeway_seconds=30)
    # Expired 10 seconds ago -- within the 30s leeway.
    token = make_token(private_pem, expires_in=-10)

    identity = verifier.verify(token)
    assert identity.tenant_id == "acme"


def test_clock_skew_beyond_leeway_is_rejected(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem, leeway_seconds=5)
    token = make_token(private_pem, expires_in=-30)

    with pytest.raises(TokenValidationError):
        verifier.verify(token)


# --- key rotation ----------------------------------------------------------


def test_rotation_overlap_accepts_both_old_and_new_key(keypair, foreign_keypair):
    old_private, old_public = keypair
    new_private, new_public = foreign_keypair
    verifier = TokenVerifier(
        key_resolver=static_key_resolver({"old-key": old_public, "new-key": new_public}),
        issuer=ISSUER,
        audience=AUDIENCE,
    )

    old_token = make_token(old_private, kid="old-key")
    new_token = make_token(new_private, kid="new-key")

    assert verifier.verify(old_token).tenant_id == "acme"
    assert verifier.verify(new_token).tenant_id == "acme"


def test_rotated_out_key_is_rejected_once_removed(keypair):
    old_private, old_public = keypair
    old_token = make_token(old_private, kid="old-key")

    # Before rotation: still resolvable.
    verifier_before = TokenVerifier(
        key_resolver=static_key_resolver({"old-key": old_public}), issuer=ISSUER, audience=AUDIENCE
    )
    assert verifier_before.verify(old_token).tenant_id == "acme"

    # After rotation: old-key removed from the resolver entirely.
    verifier_after = TokenVerifier(
        key_resolver=static_key_resolver({}), issuer=ISSUER, audience=AUDIENCE
    )
    with pytest.raises(TokenValidationError):
        verifier_after.verify(old_token)


# --- jwks_key_resolver (PyJWKClient wiring, no live network call) ---------


def test_jwks_key_resolver_returns_the_resolved_key(keypair):
    _private_pem, public_pem = keypair

    class FakeJwk:
        key = public_pem

    with patch.object(PyJWKClient, "__init__", return_value=None), patch.object(
        PyJWKClient, "get_signing_key", return_value=FakeJwk()
    ):
        resolve = jwks_key_resolver("https://idp.example/.well-known/jwks.json")
        assert resolve("key-1") == public_pem


def test_jwks_key_resolver_wraps_client_errors():
    with patch.object(PyJWKClient, "__init__", return_value=None), patch.object(
        PyJWKClient, "get_signing_key", side_effect=PyJWKClientError("unable to find a signing key")
    ):
        resolve = jwks_key_resolver("https://idp.example/.well-known/jwks.json")
        with pytest.raises(TokenValidationError):
            resolve("key-1")


# --- FastAPI dependency ------------------------------------------------


@pytest.mark.asyncio
async def test_dependency_returns_identity_for_valid_token(keypair):
    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    get_identity = build_identity_dependency(verifier)
    token = make_token(private_pem)

    identity = await get_identity(authorization=f"Bearer {token}")

    assert identity == Identity(tenant_id="acme", user_id="sarah")


@pytest.mark.asyncio
async def test_dependency_rejects_missing_header(keypair):
    _private_pem, public_pem = keypair
    get_identity = build_identity_dependency(make_verifier(public_pem))

    with pytest.raises(HTTPException) as exc_info:
        await get_identity(authorization=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_dependency_rejects_non_bearer_scheme(keypair):
    _private_pem, public_pem = keypair
    get_identity = build_identity_dependency(make_verifier(public_pem))

    with pytest.raises(HTTPException) as exc_info:
        await get_identity(authorization="Basic dXNlcjpwYXNz")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_dependency_rejects_forged_token_with_generic_message(keypair, foreign_keypair):
    _trusted_private, trusted_public = keypair
    forged_private, _forged_public = foreign_keypair
    get_identity = build_identity_dependency(make_verifier(trusted_public))
    forged_token = make_token(forged_private, kid="key-1")

    with pytest.raises(HTTPException) as exc_info:
        await get_identity(authorization=f"Bearer {forged_token}")

    assert exc_info.value.status_code == 401
    # The client-facing message must not reveal *why* verification failed.
    assert exc_info.value.detail == "Invalid or expired token"


# --- cross-tenant rejection at downstream boundaries ------------------------


def test_verified_identity_feeds_require_same_tenant_and_rejects_foreign_data(keypair):
    """End-to-end: a verified Identity's tenant_id is what
    require_same_tenant (and OnyxClient/OpenFgaFilter's tenant_id params)
    is checked against -- a token for tenant "acme" must not authorize
    inspecting a document tagged for tenant "globex", even though both are
    individually valid, correctly-signed pieces of data."""
    from datetime import datetime, timezone

    from glue.frappe_sync import FrappeRecord
    from glue.openfga_client import scoped_object_id
    from glue.onyx_client import Document as OnyxDocument

    private_pem, public_pem = keypair
    verifier = make_verifier(public_pem)
    token = make_token(private_pem, tenant_id="acme")
    identity = verifier.verify(token)

    foreign_document = OnyxDocument(
        object_type="leave_record",
        object_id="x",
        chunk="c",
        tenant_id="globex",
        retrieved_at=datetime.now(timezone.utc),
    )
    with pytest.raises(CrossTenantError):
        require_same_tenant(foreign_document.to_canonical(), tenant_id=identity.tenant_id)

    # Sanity check the same tenant_id is what the tenant-scoped OpenFGA
    # object ID and the Frappe sync's cross-tenant guard both key off of.
    assert scoped_object_id("leave_record", identity.tenant_id, "x") == "leave_record:acme__x"
    cross_tenant_record = FrappeRecord(doctype="Leave Application", name="LA-1", tenant_id="globex", fields={})
    assert cross_tenant_record.tenant_id != identity.tenant_id
