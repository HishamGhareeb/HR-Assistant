"""Unit tests for dev-only token minting (HIS-72): disabled by default,
misconfigured raises rather than silently minting, and a minted token
actually round-trips through the real glue.auth.TokenVerifier -- it is
not a parallel, weaker verification path.
"""
from __future__ import annotations

import pytest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from glue.auth import TokenVerifier, static_key_resolver
from glue.dev_auth import (
    DevAuthMisconfiguredError,
    DevAuthNotEnabledError,
    DevAuthSettings,
    load_dev_auth_settings,
    mint_dev_token,
)

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


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("DEV_AUTH_ENABLED", raising=False)

    settings = load_dev_auth_settings()

    assert settings.enabled is False


@pytest.mark.parametrize("value", ["1", "true", "True", "yes"])
def test_enabled_recognizes_truthy_values(monkeypatch, value):
    monkeypatch.setenv("DEV_AUTH_ENABLED", value)
    monkeypatch.setenv("DEV_AUTH_PRIVATE_KEY_PEM", PRIVATE_KEY)
    monkeypatch.setenv("AUTH_ISSUER", ISSUER)
    monkeypatch.setenv("AUTH_AUDIENCE", AUDIENCE)

    settings = load_dev_auth_settings()

    assert settings.enabled is True


def test_enabled_without_private_key_is_misconfigured(monkeypatch):
    monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
    monkeypatch.delenv("DEV_AUTH_PRIVATE_KEY_PEM", raising=False)
    monkeypatch.setenv("AUTH_ISSUER", ISSUER)
    monkeypatch.setenv("AUTH_AUDIENCE", AUDIENCE)

    with pytest.raises(DevAuthMisconfiguredError):
        load_dev_auth_settings()


def test_enabled_without_issuer_or_audience_is_misconfigured(monkeypatch):
    monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
    monkeypatch.setenv("DEV_AUTH_PRIVATE_KEY_PEM", PRIVATE_KEY)
    monkeypatch.delenv("AUTH_ISSUER", raising=False)
    monkeypatch.delenv("AUTH_AUDIENCE", raising=False)

    with pytest.raises(DevAuthMisconfiguredError):
        load_dev_auth_settings()


def test_mint_dev_token_rejects_disabled_settings():
    with pytest.raises(DevAuthNotEnabledError):
        mint_dev_token(DevAuthSettings(enabled=False), tenant_id="acme", user_id="sarah")


def test_mint_dev_token_rejects_blank_tenant_or_user():
    settings = DevAuthSettings(
        enabled=True, private_key_pem=PRIVATE_KEY, kid="dev-key-1",
        issuer=ISSUER, audience=AUDIENCE, token_ttl_seconds=3600,
    )
    with pytest.raises(ValueError, match="tenant_id"):
        mint_dev_token(settings, tenant_id="  ", user_id="sarah")
    with pytest.raises(ValueError, match="user_id"):
        mint_dev_token(settings, tenant_id="acme", user_id="  ")


def test_minted_token_verifies_through_the_real_token_verifier():
    settings = DevAuthSettings(
        enabled=True, private_key_pem=PRIVATE_KEY, kid="dev-key-1",
        issuer=ISSUER, audience=AUDIENCE, token_ttl_seconds=3600,
    )
    token, expires_in = mint_dev_token(settings, tenant_id="acme", user_id="priya")

    verifier = TokenVerifier(
        key_resolver=static_key_resolver({"dev-key-1": PUBLIC_KEY}), issuer=ISSUER, audience=AUDIENCE
    )
    identity = verifier.verify(token)

    assert identity.tenant_id == "acme"
    assert identity.user_id == "priya"
    assert expires_in == 3600


def test_minted_token_uses_the_configured_ttl_default_when_unset(monkeypatch):
    monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
    monkeypatch.setenv("DEV_AUTH_PRIVATE_KEY_PEM", PRIVATE_KEY)
    monkeypatch.setenv("AUTH_ISSUER", ISSUER)
    monkeypatch.setenv("AUTH_AUDIENCE", AUDIENCE)
    monkeypatch.delenv("DEV_AUTH_TOKEN_TTL_SECONDS", raising=False)

    settings = load_dev_auth_settings()

    assert settings.token_ttl_seconds == 28_800
