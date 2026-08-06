# Authentication

`glue/auth.py` replaces `docs/ARCHITECTURE.md`'s documented trust-boundary
gap: `X-User-ID` was "currently only an internal handoff and must not be
trusted from the public internet." This module verifies a signed JWT and
produces a trusted `glue.domain.Identity` instead.

## What's checked

`TokenVerifier.verify(token)` rejects the token unless all of these hold:

- signature verifies against a key resolved by the token's `kid` header
- `exp`, `iss`, `aud` are present and match the configured issuer/audience
  (within `leeway_seconds` of clock skew, default 30s)
- the tenant claim (default `tenant_id`) and user claim (default `sub`)
  are present and non-blank

A verified token produces `Identity(tenant_id=..., user_id=...)` — the
same contract `require_same_tenant` and the tenant-scoped
`OnyxClient`/`OpenFgaFilter` (HIS-12/13/14) already consume.

## Key rotation

Keys are resolved by `kid`, not hardcoded to a single key, so rotation is:
publish the new key alongside the old one (both resolvable) for an overlap
window covering the longest-lived outstanding token, then remove the old
key. Two resolvers:

- **`static_key_resolver(keys)`** — a fixed `{kid: PEM public key}` dict.
  Use when keys are distributed out-of-band (secrets manager + deploy)
  rather than served from an endpoint.
- **`jwks_key_resolver(jwks_url)`** — fetches and caches a JWKS document
  (the standard multi-key format most IdPs expose — Auth0, Okta, Cognito,
  a self-hosted one, etc.), refetching on a TTL (default 300s) so a newly
  rotated-in key is picked up without a restart.

An unrecognized `kid` fails resolution and the token is rejected outright
— there's no "try every key" fallback, so a forged token that invents a
`kid` gets the same rejection as one referencing an already-rotated-out
key.

**`jwks_key_resolver` performs a blocking HTTP call** (`PyJWKClient` uses
`urllib`, not an async client). Never call it directly inside an async
request handler — `TokenVerifier.verify_async` wraps `verify` in
`asyncio.to_thread` for exactly this reason, the same pattern already used
for the synchronous Claude call in `glue/pipeline.py`.

## Configuration

| Setting | Constructor arg | Notes |
|---|---|---|
| Issuer | `issuer` | must match `iss` exactly |
| Audience | `audience` | must match `aud` exactly |
| Algorithms | `algorithms` | default `["RS256"]` — asymmetric only; never enable `HS256` here unless you also change the key resolver to return a shared secret, which reintroduces the "anyone who can verify can also forge" problem RS256 avoids |
| Clock skew leeway | `leeway_seconds` | default 30 |
| Tenant claim name | `tenant_claim` | default `"tenant_id"` |
| User claim name | `user_claim` | default `"sub"` |

Wire these from environment variables the same way `glue/config.py` wires
the other API credentials (`AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_JWKS_URL`)
when this is connected in `glue/app.py`.

## Cross-tenant rejection at boundaries

`glue/auth.py` only produces `Identity` — it doesn't filter anything
itself. Enforcement happens wherever `Identity.tenant_id` is handed to a
boundary that already requires it:

- `glue.domain.require_same_tenant` — generic guard, raises `CrossTenantError`
- `glue.onyx_client.OnyxClient.search(question, tenant_id=...)`
- `glue.openfga_client.OpenFgaFilter.filter_authorized(user_id, documents, tenant_id=...)`
- `glue.hr_source_sync.SyncEngine.sync_all(tenant_id, records)`

`tests/test_auth.py::test_verified_identity_feeds_require_same_tenant_and_rejects_foreign_data`
exercises this chain end-to-end: a verified `Identity` for tenant `acme`
combined with a document tagged for tenant `globex` is rejected, even
though both are individually valid, correctly-shaped data.

Audit-boundary enforcement (the fourth boundary named in this ticket's
acceptance criteria) will consume the same `Identity` once HIS-18
(audit/observability) exists — nothing here needs to change for that; the
identity contract is already the thing audit logging would key off of.

## Wiring into the API (not in this ticket)

`build_identity_dependency(verifier)` returns a FastAPI dependency ready
to replace `authenticated_user` in `glue/app.py`, returning `Identity`
instead of a bare, unverified `user_id` string. That file has in-flight
work from the API-foundation ticket (HIS-11) at the time this was
written, so wiring it in is left as a follow-up rather than risking a
collision — see the "Status" pattern used in `docs/DOMAIN_CONTRACTS.md`
and `docs/ONYX_ADAPTER.md` for the same reasoning applied elsewhere in
this build sequence.

## Known gap

`jwks_key_resolver` has not been exercised against a real IdP's JWKS
endpoint — `tests/test_auth.py` covers it structurally via `PyJWKClient`
but doesn't hit a live URL. Verify against whichever IdP is chosen before
relying on it in a deployed environment.
