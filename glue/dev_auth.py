"""Dev-only JWT minting so `web/` can authenticate locally without a real
identity provider (HIS-72).

Reads its own small slate of `DEV_AUTH_*` (+ existing `AUTH_ISSUER`/
`AUTH_AUDIENCE`) environment variables directly, not the full
`glue.config.Config` -- so this works even when unrelated production
config (Anthropic/Onyx/OpenFGA keys) isn't set, and so a real deployment
that never sets `DEV_AUTH_*` has this capability structurally absent, not
merely unauthorized. `glue.app`'s `/v1/dev/token` endpoint returns a plain
404 (looks like it doesn't exist) rather than 403 (looks like a guarded
feature) when disabled, for the same reason.

**Never enable this in a production deployment.** It exists purely so the
frontend has something legitimate to send to `Authorization: Bearer` --
minted tokens go through the exact same `glue.auth.TokenVerifier` +
`static_key_resolver` verification path already used in tests and in
production. This module does not bypass verification; it only gives local
development something real to verify.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

import jwt

DEFAULT_DEV_AUTH_KID = "dev-key-1"
DEFAULT_DEV_AUTH_TOKEN_TTL_SECONDS = 28_800  # 8 hours: a working day of demo/dev use.


class DevAuthNotEnabledError(RuntimeError):
    """Dev token minting was requested but DEV_AUTH_ENABLED is not set."""


class DevAuthMisconfiguredError(RuntimeError):
    """DEV_AUTH_ENABLED is set but a required DEV_AUTH_*/AUTH_* value is missing."""


@dataclass(frozen=True)
class DevAuthSettings:
    enabled: bool
    private_key_pem: str = ""
    kid: str = ""
    issuer: str = ""
    audience: str = ""
    token_ttl_seconds: int = 0


def load_dev_auth_settings() -> DevAuthSettings:
    enabled = os.environ.get("DEV_AUTH_ENABLED", "false").strip().lower() in ("1", "true", "yes")
    if not enabled:
        return DevAuthSettings(enabled=False)

    private_key_pem = os.environ.get("DEV_AUTH_PRIVATE_KEY_PEM", "")
    issuer = os.environ.get("AUTH_ISSUER", "")
    audience = os.environ.get("AUTH_AUDIENCE", "")
    if not private_key_pem.strip() or not issuer.strip() or not audience.strip():
        raise DevAuthMisconfiguredError(
            "DEV_AUTH_ENABLED is set but DEV_AUTH_PRIVATE_KEY_PEM / AUTH_ISSUER / "
            "AUTH_AUDIENCE are not all configured"
        )

    kid = os.environ.get("DEV_AUTH_KID", DEFAULT_DEV_AUTH_KID)
    ttl_raw = os.environ.get("DEV_AUTH_TOKEN_TTL_SECONDS", "")
    token_ttl_seconds = int(ttl_raw) if ttl_raw.strip() else DEFAULT_DEV_AUTH_TOKEN_TTL_SECONDS

    return DevAuthSettings(
        enabled=True,
        private_key_pem=private_key_pem,
        kid=kid,
        issuer=issuer,
        audience=audience,
        token_ttl_seconds=token_ttl_seconds,
    )


def mint_dev_token(settings: DevAuthSettings, *, tenant_id: str, user_id: str) -> tuple[str, int]:
    """Returns ``(token, expires_in_seconds)``. Raises
    ``DevAuthNotEnabledError`` if ``settings.enabled`` is False -- a
    defense-in-depth check callers must not skip even though
    ``load_dev_auth_settings`` already encodes the same decision."""
    if not settings.enabled:
        raise DevAuthNotEnabledError("dev token minting is not enabled")
    if not tenant_id.strip():
        raise ValueError("tenant_id must not be blank")
    if not user_id.strip():
        raise ValueError("user_id must not be blank")

    now = int(time.time())
    claims = {
        "iss": settings.issuer,
        "aud": settings.audience,
        "iat": now,
        "exp": now + settings.token_ttl_seconds,
        "tenant_id": tenant_id.strip(),
        "sub": user_id.strip(),
    }
    token = jwt.encode(claims, settings.private_key_pem, algorithm="RS256", headers={"kid": settings.kid})
    return token, settings.token_ttl_seconds
