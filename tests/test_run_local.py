"""Unit tests for the pure .env-merging logic in scripts/run_local.py.

Docker/OpenFGA/uv/npm/server-launch steps are thin subprocess wrappers,
exercised manually (see the module docstring) rather than here. This file
covers the parts that had real bugs during manual testing: idempotency of
repeated runs, and PEM-value quoting so python-dotenv actually unescapes
the embedded newlines.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import run_local  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_env_path(tmp_path, monkeypatch):
    monkeypatch.setattr(run_local, "ENV_PATH", tmp_path / ".env")
    yield tmp_path / ".env"


# --- _parse_env_file / _write_env_file round trip --------------------------


def test_parse_env_file_missing_file_returns_empty_dict(tmp_path):
    assert run_local._parse_env_file(tmp_path / "does-not-exist.env") == {}


def test_write_then_parse_round_trips_plain_values(tmp_path):
    path = tmp_path / ".env"
    run_local._write_env_file(path, {"FOO": "bar", "EMPTY": "", "URL": "http://localhost:8000"})

    parsed = run_local._parse_env_file(path)

    assert parsed == {"FOO": "bar", "EMPTY": "", "URL": "http://localhost:8000"}


def test_parse_env_file_ignores_comments_and_blank_lines(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# a comment\n\nFOO=bar\n   \nBAZ=qux\n", encoding="utf-8")

    assert run_local._parse_env_file(path) == {"FOO": "bar", "BAZ": "qux"}


# --- PEM quoting (regression: python-dotenv only unescapes \n inside ------
# --- double-quoted values, not bare ones) -----------------------------------


def test_dev_auth_private_key_pem_is_double_quoted_on_write(tmp_path):
    path = tmp_path / ".env"
    run_local._write_env_file(path, {"DEV_AUTH_PRIVATE_KEY_PEM": "line1\\nline2", "OTHER": "plain"})

    raw = path.read_text(encoding="utf-8")

    assert 'DEV_AUTH_PRIVATE_KEY_PEM="line1\\nline2"' in raw
    assert "OTHER=plain" in raw  # unrelated keys stay unquoted


def test_dev_auth_private_key_pem_unescapes_via_dotenv(tmp_path):
    """The actual regression: dotenv_values must turn the literal \\n
    sequence into a real newline, matching what jwt.encode() needs -- this
    is exactly what a bare, unquoted value fails to do."""
    from dotenv import dotenv_values

    path = tmp_path / ".env"
    run_local._write_env_file(path, {"DEV_AUTH_PRIVATE_KEY_PEM": "-----BEGIN KEY-----\\nAA==\\n-----END KEY-----"})

    values = dotenv_values(path)

    assert values["DEV_AUTH_PRIVATE_KEY_PEM"] == "-----BEGIN KEY-----\nAA==\n-----END KEY-----"


# --- ensure_env idempotency (regression: fill() treated an intentionally ---
# --- blank value, e.g. LANGFUSE_PUBLIC_KEY=, as "missing" and rewrote it ---
# --- -- and therefore reported a change -- on every single run) ------------


def test_ensure_env_first_run_writes_every_expected_key(monkeypatch, _isolated_env_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ONYX_API_URL", "")  # explicit skip
    monkeypatch.delenv("ONYX_API_KEY", raising=False)

    env = run_local.ensure_env("store-1", "model-1")

    assert env["ANTHROPIC_API_KEY"] == "sk-test"
    assert env["OPENFGA_STORE_ID"] == "store-1"
    assert env["OPENFGA_MODEL_ID"] == "model-1"
    assert env["DEV_AUTH_ENABLED"] == "true"
    assert env["DEV_AUTH_PRIVATE_KEY_PEM"]
    assert _isolated_env_path.exists()


def test_ensure_env_second_run_reports_no_change(monkeypatch, _isolated_env_path, capsys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ONYX_API_URL", "")

    run_local.ensure_env("store-1", "model-1")
    written_at_first_run = _isolated_env_path.read_text(encoding="utf-8")
    capsys.readouterr()

    run_local.ensure_env("store-1", "model-1")

    assert _isolated_env_path.read_text(encoding="utf-8") == written_at_first_run
    assert "already has everything needed -- left unchanged" in capsys.readouterr().out


def test_ensure_env_never_overwrites_a_value_already_in_the_file(monkeypatch, _isolated_env_path):
    run_local._write_env_file(
        _isolated_env_path,
        {"ANTHROPIC_API_KEY": "sk-existing", "ONYX_API_URL": "", "AUDIT_PRIVACY_KEY": "existing-privacy-key"},
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-be-used")

    env = run_local.ensure_env("store-1", "model-1")

    assert env["ANTHROPIC_API_KEY"] == "sk-existing"
    assert env["AUDIT_PRIVACY_KEY"] == "existing-privacy-key"


def test_ensure_env_prefers_shell_env_var_over_prompting(monkeypatch, _isolated_env_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-shell")
    monkeypatch.setenv("ONYX_API_URL", "")

    env = run_local.ensure_env("store-1", "model-1")

    assert env["ANTHROPIC_API_KEY"] == "sk-from-shell"


# --- _onyx_reachable ---------------------------------------------------------


def test_onyx_reachable_is_false_for_a_closed_port():
    assert run_local._onyx_reachable("http://127.0.0.1:1", timeout_seconds=1.0) is False
