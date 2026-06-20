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
        self.onyx_api_key = os.environ.get("ONYX_API_KEY", "")

        self.openfga_api_url = _required("OPENFGA_API_URL")
        self.openfga_store_id = _required("OPENFGA_STORE_ID")
        self.openfga_model_id = os.environ.get("OPENFGA_MODEL_ID", "")

        self.langfuse_public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        self.langfuse_secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
        self.langfuse_host = os.environ.get("LANGFUSE_HOST", "http://localhost:3001")
