#!/usr/bin/env python
"""One-command local bootstrap: start OpenFGA, provision its store/model,
fill in every secret the backend needs (prompting only for the ones that
must be a real external credential), install dependencies, best-effort
seed the demo organization, and run the API + frontend together.

Usage::

    uv run python scripts/run_local.py

Safe to re-run: every step is idempotent (OpenFGA store/model lookup,
`.env` fills only missing keys without touching ones you already set,
`uv sync`/`npm install` are no-ops when already satisfied, demo-org sync
diffs against its checkpoint).

## What this script can and cannot fully automate

It can stand up, from nothing: Docker-based OpenFGA, its authorization
model, a dev-only signed-JWT identity (see glue/dev_auth.py -- never used
in a real deployment), the audit/suggestion/feedback stores, and both the
API and the web/ frontend, running together.

It **cannot** stand up Onyx or Frappe HR for you -- those are external
systems with their own installers (see README.md's Stage 0 setup), not
something a single script in this repo should reach out and clone/build.
If you already have an Onyx instance running, point this script at it
(it will ask). If you don't, this script still gets you a fully working
API + frontend where every surface *except* the retrieval-backed chat
answer works end-to-end against real data (suggestion inbox, admin
console, feedback/quality dashboard, role assignment) -- chat questions
will fail closed with a safe "service is temporarily unavailable"
message rather than pretending to answer from documents that were never
indexed.

## Windows Firewall

Every server this script starts -- OpenFGA (compose.yaml already binds it
to 127.0.0.1 only), the API, and the frontend -- is bound explicitly to
the loopback interface (`127.0.0.1`), never `0.0.0.0`/all-interfaces.
Windows Firewall's "allow this app" prompt is triggered by a process
accepting inbound connections from a network interface; loopback traffic
never crosses that boundary, so nothing here should ever trigger one. If
a prompt still appears (e.g. a corporate policy that reclassifies the
Docker/WSL2 vEthernet adapter as a "Public" network), it's Docker
Desktop's networking being prompted, not this script -- allow it once and
it won't ask again.
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
WEB_DIR = REPO_ROOT / "web"

sys.path.insert(0, str(REPO_ROOT))


class BootstrapError(RuntimeError):
    pass


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd or REPO_ROOT, check=check)


def _prompt(label: str, *, default: str = "", secret: bool = False, required: bool = False) -> str:
    if not sys.stdin.isatty():
        return default
    suffix = " (required)" if required and not default else f" [{default}]" if default else ""
    while True:
        if secret:
            import getpass

            value = getpass.getpass(f"{label}{suffix}: ").strip()
        else:
            value = input(f"{label}{suffix}: ").strip()
        if not value:
            if default:
                return default
            if not required:
                return ""
            print("  This value is required.")
            continue
        return value


# --- step 1: Docker + OpenFGA ------------------------------------------


_DOCKER_DESKTOP_PATHS = [
    Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe"),
    Path(os.environ.get("LOCALAPPDATA", "")) / "Docker" / "Docker Desktop.exe" if os.environ.get("LOCALAPPDATA") else None,
]


def _docker_ready() -> bool:
    return subprocess.run(["docker", "version"], capture_output=True, text=True).returncode == 0


def ensure_docker(timeout_seconds: float = 90.0) -> None:
    if shutil.which("docker") is None:
        raise BootstrapError("Docker is required (Docker Desktop, WSL2 backend) -- install it and try again.")
    if _docker_ready():
        return

    if sys.platform.startswith("win"):
        docker_desktop = next((p for p in _DOCKER_DESKTOP_PATHS if p and p.exists()), None)
        if docker_desktop is not None:
            print("Docker isn't running -- starting Docker Desktop...")
            subprocess.Popen([str(docker_desktop)])
        else:
            print("Docker isn't running -- start Docker Desktop manually.")
    else:
        print("Docker isn't running -- start it (e.g. `open -a Docker` on macOS).")

    print("Waiting for the Docker daemon to come up (this can take a minute the first time)...")
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _docker_ready():
            print("Docker is ready.")
            return
        time.sleep(3)
    raise BootstrapError("Docker did not become ready in time -- start Docker Desktop yourself and re-run this script.")


def ensure_openfga_running(timeout_seconds: float = 90.0) -> None:
    _run(["docker", "compose", "up", "-d", "openfga"])
    print("Waiting for OpenFGA to become healthy...")
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "compose", "ps", "openfga", "--format", "json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                status = json.loads(result.stdout.splitlines()[0])
            except json.JSONDecodeError:
                status = {}
            if "healthy" in str(status.get("Health", "")).lower():
                print("OpenFGA is healthy.")
                return
        time.sleep(2)
    raise BootstrapError("OpenFGA did not become healthy in time -- check `docker compose logs openfga`.")


def provision_openfga() -> tuple[str, str]:
    """Returns (store_id, model_id). Reuses provision_openfga.py's own
    functions rather than re-implementing store/model creation."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import asyncio

    import provision_openfga as provisioner
    from openfga_sdk import ClientConfiguration, OpenFgaClient

    async def _provision() -> tuple[str, str]:
        api_url = "http://127.0.0.1:8080"
        model_json = provisioner.transform_model_to_json()
        async with OpenFgaClient(ClientConfiguration(api_url=api_url)) as bootstrap_client:
            store_id = await provisioner.find_or_create_store(bootstrap_client, provisioner.DEFAULT_STORE_NAME)
        async with OpenFgaClient(ClientConfiguration(api_url=api_url, store_id=store_id)) as client:
            model_id = await provisioner.ensure_model(client, model_json)
        return store_id, model_id

    return asyncio.run(_provision())


# --- step 2: .env -----------------------------------------------------


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


# python-dotenv only unescapes literal \n sequences into real newlines
# inside a double-quoted value -- an unquoted value is taken verbatim, so
# a PEM key written as raw text with \n escapes stays as two-character
# backslash-n and fails to parse. AUTH_STATIC_KEYS_JSON doesn't need this:
# it's parsed with json.loads(), which does its own \n-unescaping inside
# JSON strings regardless of how dotenv passed the surrounding text through.
_DOUBLE_QUOTE_KEYS = {"DEV_AUTH_PRIVATE_KEY_PEM"}


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    lines = [
        f'{key}="{value}"' if key in _DOUBLE_QUOTE_KEYS else f"{key}={value}"
        for key, value in values.items()
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_dev_auth_keys() -> tuple[str, str]:
    """Returns (private_pem, public_pem), one-line-escaped for .env."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

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


def ensure_env(openfga_store_id: str, openfga_model_id: str) -> dict[str, str]:
    env = _parse_env_file(ENV_PATH)
    changed = False

    def fill(key: str, value: str) -> None:
        nonlocal changed
        if key not in env:
            env[key] = value
            changed = True

    def fill_from_env_or_prompt(key: str, *, label: str, secret: bool = False, required: bool = False, default: str = "") -> None:
        nonlocal changed
        if key in env:
            return  # already in .env (even if intentionally blank) -- never overwritten
        from_shell = os.environ.get(key)
        if from_shell:
            env[key] = from_shell
            changed = True
            print(f"{label}: using {key} from your shell environment.")
            return
        env[key] = _prompt(label, secret=secret, required=required, default=default)
        changed = True

    print("\n--- Required: Anthropic (Claude reasoning) ---")
    print("Pre-fill this by exporting ANTHROPIC_API_KEY in your shell before running this script.")
    fill_from_env_or_prompt("ANTHROPIC_API_KEY", label="Anthropic API key", secret=True, required=True)
    fill("CLAUDE_MODEL", "claude-sonnet-4-6")

    print("\n--- Optional: Onyx (document retrieval) ---")
    print("Leave blank to skip -- chat will fail closed with a safe message instead of retrieving real documents.")
    print("Pre-fill by exporting ONYX_API_URL / ONYX_API_KEY in your shell before running this script.")
    fill_from_env_or_prompt("ONYX_API_URL", label="Onyx API URL", default="http://localhost:3002")
    if env.get("ONYX_API_URL"):
        fill_from_env_or_prompt("ONYX_API_KEY", label="Onyx API key", secret=True)

    fill("OPENFGA_API_URL", "http://127.0.0.1:8080")
    fill("OPENFGA_STORE_ID", openfga_store_id)
    fill("OPENFGA_MODEL_ID", openfga_model_id)

    fill("LANGFUSE_PUBLIC_KEY", "")
    fill("LANGFUSE_SECRET_KEY", "")
    fill("LANGFUSE_HOST", "http://localhost:3001")

    fill("AUTH_ISSUER", "https://auth.hr-assistant.local")
    fill("AUTH_AUDIENCE", "hr-assistant-api")
    fill("AUTH_JWKS_URL", "")

    fill("AUDIT_PRIVACY_KEY", secrets.token_urlsafe(32))
    fill("AUDIT_LOG_PATH", ".tmp/audit.jsonl")

    fill("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

    fill("SUGGESTION_STORE_PATH", ".tmp/suggestions.jsonl")
    fill("FEEDBACK_STORE_PATH", ".tmp/feedback.jsonl")
    demo_reviewer_map = json.dumps({"demo-org": ["hr-demo"]})
    fill("HR_REVIEWERS_JSON", demo_reviewer_map)
    fill("HR_ADMINS_JSON", demo_reviewer_map)
    fill("HR_FEEDBACK_REVIEWERS_JSON", demo_reviewer_map)

    if env.get("DEV_AUTH_ENABLED", "").lower() != "true" or not env.get("DEV_AUTH_PRIVATE_KEY_PEM"):
        print("\nGenerating a dev-only signing key so the frontend can authenticate locally...")
        private_pem, public_pem = generate_dev_auth_keys()
        env["DEV_AUTH_ENABLED"] = "true"
        env["DEV_AUTH_KID"] = "dev-key-1"
        env["DEV_AUTH_PRIVATE_KEY_PEM"] = private_pem.replace("\n", "\\n")
        env["DEV_AUTH_TOKEN_TTL_SECONDS"] = "28800"

        existing_keys: dict[str, str] = {}
        if env.get("AUTH_STATIC_KEYS_JSON"):
            try:
                existing_keys = json.loads(env["AUTH_STATIC_KEYS_JSON"])
            except json.JSONDecodeError:
                existing_keys = {}
        existing_keys["dev-key-1"] = public_pem
        env["AUTH_STATIC_KEYS_JSON"] = json.dumps(existing_keys)
        changed = True
    else:
        fill("AUTH_STATIC_KEYS_JSON", "{}")

    if changed:
        _write_env_file(ENV_PATH, env)
        print(f"\nWrote {ENV_PATH}")
    else:
        print(f"\n{ENV_PATH} already has everything needed -- left unchanged.")

    return env


# --- step 3: dependencies -----------------------------------------------


def install_python_deps() -> None:
    _run(["uv", "sync", "--extra", "dev"])


def install_frontend_deps() -> None:
    if not (WEB_DIR / "node_modules").exists():
        _run(["npm", "install"], cwd=WEB_DIR)
    else:
        print("web/node_modules already present -- skipping npm install.")


# --- step 4: best-effort demo seed --------------------------------------


def _onyx_reachable(api_url: str, timeout_seconds: float = 3.0) -> bool:
    """Fast preflight so an unreachable Onyx fails in ~3s, not the minutes
    it'd take for every one of the ~25 demo records to individually time
    out through the full sync path."""
    import urllib.error
    import urllib.request

    try:
        urllib.request.urlopen(api_url, timeout=timeout_seconds)
        return True
    except urllib.error.HTTPError:
        return True  # reachable -- any HTTP response (even 404/401) means something is listening
    except Exception:
        return False


def seed_demo_org(env: dict[str, str]) -> None:
    if not env.get("ONYX_API_URL") or not env.get("ONYX_API_KEY"):
        print("\nOnyx is not configured -- skipping demo-org seed. Run scripts/seed_demo_org.py yourself once it is.")
        return

    if not _onyx_reachable(env["ONYX_API_URL"]):
        print(
            f"\nOnyx at {env['ONYX_API_URL']} isn't reachable -- skipping demo-org seed. "
            "Run scripts/seed_demo_org.py yourself once it's up."
        )
        return

    print("\nSeeding the demo organization (glue/demo_seed.py)...")
    for key, value in env.items():
        os.environ.setdefault(key, value)
    try:
        import asyncio

        from glue.demo_seed import demo_hr_admin_user_ids, seed_demo_organization
        from glue.hr_source_sync import SyncConfig, SyncEngine
        from glue.onyx_indexer import OnyxIndexer
        from glue.openfga_client import OpenFgaTupleWriter

        onyx = OnyxIndexer(env["ONYX_API_URL"], env["ONYX_API_KEY"])
        tuple_writer = OpenFgaTupleWriter(env["OPENFGA_API_URL"], env["OPENFGA_STORE_ID"], env.get("OPENFGA_MODEL_ID", ""))
        engine = SyncEngine(onyx, tuple_writer, config=SyncConfig(hr_admin_user_ids=demo_hr_admin_user_ids()))
        report = asyncio.run(seed_demo_organization(engine))
        print(
            f"Demo org seeded: {report.created} created, {report.updated} updated, "
            f"{report.unchanged} unchanged, {len(report.failed)} failed"
        )
    except Exception as exc:  # noqa: BLE001 -- best-effort step, must not abort the whole bootstrap
        print(f"Demo-org seed failed ({exc}) -- continuing without it. You can retry with scripts/seed_demo_org.py.")


# --- step 5: run everything ---------------------------------------------


def _stream(prefix: str, pipe) -> None:
    for line in iter(pipe.readline, ""):
        if not line:
            break
        print(f"[{prefix}] {line.rstrip()}")


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if sys.platform.startswith("win"):
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
    else:
        process.terminate()


def run_servers() -> None:
    print("\nStarting API on http://127.0.0.1:8000 and frontend on http://127.0.0.1:5173 (Ctrl+C stops both)...")
    # --host 127.0.0.1 on both: loopback-only binding is what keeps Windows
    # Firewall from ever prompting (see module docstring).
    api_process = subprocess.Popen(
        ["uv", "run", "uvicorn", "glue.app:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    web_process = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
        cwd=WEB_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=sys.platform.startswith("win"),
    )

    threads = [
        threading.Thread(target=_stream, args=("api", api_process.stdout), daemon=True),
        threading.Thread(target=_stream, args=("web", web_process.stdout), daemon=True),
    ]
    for t in threads:
        t.start()

    def _open_browser() -> None:
        time.sleep(3)
        webbrowser.open("http://localhost:5173")

    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        while True:
            if api_process.poll() is not None:
                raise BootstrapError("The API process exited unexpectedly -- see [api] output above.")
            if web_process.poll() is not None:
                raise BootstrapError("The frontend process exited unexpectedly -- see [web] output above.")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        _terminate(api_process)
        _terminate(web_process)


def main() -> None:
    try:
        ensure_docker()
        ensure_openfga_running()
        store_id, model_id = provision_openfga()
        env = ensure_env(store_id, model_id)
        install_python_deps()
        install_frontend_deps()
        seed_demo_org(env)
        run_servers()
    except BootstrapError as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
