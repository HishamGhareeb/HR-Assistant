"""Signed authentication: replaces the `X-User-ID` internal handoff
(`docs/ARCHITECTURE.md` trust boundary #1 -- "must not be trusted from the
public internet") with a verified JWT carrying tenant and user claims.

## What gets checked

`TokenVerifier.verify` rejects a token unless **all** of these hold:

- the signature verifies against a known signing key (resolved by the
  token's `kid` header -- see "Key rotation" below)
- `exp` (expiry), `iss` (issuer), and `aud` (audience) are present and
  match the configured issuer/audience, within `leeway_seconds` of clock
  skew
- the configured tenant claim (default `tenant_id`) and user claim
  (default `sub`) are present and non-blank

A verified token produces a `glue.domain.Identity` -- the same contract
`require_same_tenant` and the tenant-scoped `OnyxClient`/`OpenFgaFilter`
already consume (HIS-12/13/14), so "trusted tenant/user context
constructed server-side" is one object that flows unchanged through every
downstream boundary rather than being re-derived at each one.

## Key rotation

Signing keys are resolved by `kid` (key ID) through a `KeyResolver`
callable, not hardcoded to one key, so rotation is: publish the new key
alongside the old one (both resolvable) for an overlap window covering the
longest-lived outstanding token, then remove the old key. Two resolvers
are provided:

- `static_key_resolver(keys)` -- a fixed `{kid: PEM public key}` dict.
  Simplest option if keys are distributed out-of-band (e.g. via secrets
  manager + deploy) rather than served from a JWKS endpoint.
- `jwks_key_resolver(jwks_url)` -- fetches and caches a JWKS document
  (the standard multi-key-with-`kid` format most IdPs expose), refreshing
  on a TTL so a newly rotated-in key is picked up without a restart. This
  performs a **blocking** HTTP call (`PyJWKClient` uses `urllib`, not
  async) -- never call a JWKS-backed resolver directly from an event
  loop; `TokenVerifier.verify_async` wraps it in `asyncio.to_thread` for
  exactly this reason (same pattern as the synchronous Claude call in
  `glue/pipeline.py`).

An unrecognized `kid` (already-rotated-out key, or a forged token that
invents one) fails resolution and the token is rejected -- it never falls
back to "try every key."

## Cross-tenant rejection at boundaries

This module produces `Identity`; it does not by itself filter retrieval or
authorization results. Enforcement happens where `Identity.tenant_id` is
handed to a boundary that already requires it:

- `glue.domain.require_same_tenant` -- generic guard for any contract
- `glue.onyx_client.OnyxClient.search(question, tenant_id=...)`
- `glue.openfga_client.OpenFgaFilter.filter_authorized(user_id, documents, tenant_id=...)`
- `glue.frappe_sync.SyncEngine.sync_all(tenant_id, records)` (rejects a
  record whose own `tenant_id` doesn't match)

`build_identity_dependency` produces the FastAPI dependency ready to
replace `authenticated_user` in `glue/app.py` and to pass its
`Identity.tenant_id` into each of the above once that wiring happens
(tracked separately so this doesn't collide with the in-flight API
foundation work -- see docs/AUTHENTICATION.md).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError
from pydantic import ValidationError

from .domain import Identity

logger = logging.getLogger(__name__)

DEFAULT_ALGORITHMS = ["RS256"]
DEFAULT_LEEWAY_SECONDS = 30
DEFAULT_TENANT_CLAIM = "tenant_id"
DEFAULT_USER_CLAIM = "sub"

KeyResolver = Callable[[str], "str | bytes"]


class TokenValidationError(Exception):
    """Any reason a token is not trusted: bad signature, expired, wrong
    issuer/audience, unknown key id, missing/blank claims, or malformed
    input. Deliberately one exception type -- callers (the FastAPI
    dependency) must not distinguish reasons in what they expose to the
    client; see `build_identity_dependency`."""


def static_key_resolver(keys: dict[str, str]) -> KeyResolver:
    """Fixed set of signing keys, keyed by `kid`. Non-blocking -- safe to
    call directly from async code."""

    def resolve(kid: str) -> str:
        try:
            return keys[kid]
        except KeyError as exc:
            raise TokenValidationError(f"unknown key id: {kid!r}") from exc

    return resolve


def jwks_key_resolver(jwks_url: str, cache_lifespan_seconds: float = 300) -> KeyResolver:
    """Resolve signing keys from a JWKS endpoint, with caching. **Blocking**
    (see module docstring) -- only call through `TokenVerifier.verify_async`."""
    client = PyJWKClient(jwks_url, cache_keys=True, lifespan=cache_lifespan_seconds)

    def resolve(kid: str):
        try:
            return client.get_signing_key(kid).key
        except PyJWKClientError as exc:
            raise TokenValidationError(f"unable to resolve signing key {kid!r}: {exc}") from exc

    return resolve


class TokenVerifier:
    def __init__(
        self,
        key_resolver: KeyResolver,
        issuer: str,
        audience: str,
        algorithms: list[str] | None = None,
        leeway_seconds: float = DEFAULT_LEEWAY_SECONDS,
        tenant_claim: str = DEFAULT_TENANT_CLAIM,
        user_claim: str = DEFAULT_USER_CLAIM,
    ) -> None:
        if not issuer.strip():
            raise ValueError("issuer must not be blank")
        if not audience.strip():
            raise ValueError("audience must not be blank")
        self._key_resolver = key_resolver
        self._issuer = issuer
        self._audience = audience
        self._algorithms = algorithms or list(DEFAULT_ALGORITHMS)
        self._leeway_seconds = leeway_seconds
        self._tenant_claim = tenant_claim
        self._user_claim = user_claim

    def verify(self, token: str) -> Identity:
        """Synchronous verification. See `verify_async` for use inside an
        async request handler -- this may block on key resolution."""
        try:
            header = jwt.get_unverified_header(token)
        except InvalidTokenError as exc:
            raise TokenValidationError(f"malformed token header: {exc}") from exc

        kid = header.get("kid")
        if not kid:
            raise TokenValidationError("token header is missing 'kid'")

        signing_key = self._key_resolver(kid)

        try:
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=self._algorithms,
                issuer=self._issuer,
                audience=self._audience,
                leeway=self._leeway_seconds,
                options={"require": ["exp", "iss", "aud", self._tenant_claim, self._user_claim]},
            )
        except InvalidTokenError as exc:
            raise TokenValidationError(f"token failed verification: {exc}") from exc

        try:
            return Identity(tenant_id=claims[self._tenant_claim], user_id=claims[self._user_claim])
        except ValidationError as exc:
            raise TokenValidationError(f"token claims did not produce a valid identity: {exc}") from exc

    async def verify_async(self, token: str) -> Identity:
        """Runs `verify` in a worker thread -- key resolution (JWKS fetch)
        and signature verification are both potentially blocking calls
        that must never run directly on the event loop."""
        return await asyncio.to_thread(self.verify, token)


def build_identity_dependency(verifier: TokenVerifier):
    """FastAPI dependency: verifies the `Authorization: Bearer <token>`
    header and returns a trusted `Identity`. The specific validation
    failure is logged server-side but never returned to the client --
    a 401 with a generic message either way, so a forged-token attempt
    can't be used to fingerprint *why* it failed (expired vs. wrong
    issuer vs. unknown key)."""

    async def get_identity(
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> Identity:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
            )
        token = authorization[len("Bearer ") :].strip()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
            )
        try:
            return await verifier.verify_async(token)
        except TokenValidationError as exc:
            logger.warning("token_rejected reason=%s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from exc

    return get_identity
