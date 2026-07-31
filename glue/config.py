"""Environment-driven configuration for the glue pipeline. No defaults for
secrets -- missing values fail fast instead of silently hitting localhost
or empty credentials in a deployed environment."""
import os

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


class Config:
    def __init__(self) -> None:
        self.anthropic_api_key = _required("ANTHROPIC_API_KEY")
        self.claude_model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

        self.onyx_api_url = _required("ONYX_API_URL")
        # The admin search endpoint requires an API key (see
        # glue/onyx_client.py) -- unlike the old stub, this is no longer
        # optional.
        self.onyx_api_key = _required("ONYX_API_KEY")

        self.openfga_api_url = _required("OPENFGA_API_URL")
        self.openfga_store_id = _required("OPENFGA_STORE_ID")
        self.openfga_model_id = os.environ.get("OPENFGA_MODEL_ID", "")

        self.langfuse_public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        self.langfuse_secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
        self.langfuse_host = os.environ.get("LANGFUSE_HOST", "http://localhost:3001")

        # Signed authentication (glue/auth.py) -- exactly one key source
        # must be configured; validated in glue/app.py's build_token_verifier
        # rather than here, so a JWKS-URL deployment doesn't need to also
        # set the static-keys variable (or vice versa).
        self.auth_issuer = _required("AUTH_ISSUER")
        self.auth_audience = _required("AUTH_AUDIENCE")
        self.auth_jwks_url = os.environ.get("AUTH_JWKS_URL", "")
        # JSON object: {"<kid>": "<PEM public key>", ...}
        self.auth_static_keys_json = os.environ.get("AUTH_STATIC_KEYS_JSON", "")

        # Audit (glue/audit.py) -- privacy_key pseudonymizes the actor
        # reference; losing/rotating it starts a new correlation epoch,
        # see docs/AUDIT_AND_OBSERVABILITY.md.
        self.audit_privacy_key = _required("AUDIT_PRIVACY_KEY").encode("utf-8")
        self.audit_log_path = os.environ.get("AUDIT_LOG_PATH", ".tmp/audit.jsonl")
