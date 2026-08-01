"""Regression checks for the local container and CI delivery contract."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_api_image_uses_locked_project_dependencies() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY pyproject.toml uv.lock ./" in dockerfile
    assert "uv sync --locked --no-dev --no-install-project" in dockerfile
    assert "requirements" not in dockerfile


def test_no_legacy_requirements_manifests_are_tracked() -> None:
    assert not list(ROOT.glob("requirements*.txt"))


def test_local_compose_ports_are_loopback_only() -> None:
    compose_ports = {
        "compose.yaml": ("8080", "8081", "3000", "8000"),
        "docker/openfga/docker-compose.yml": ("8080", "8081", "3000"),
    }

    for relative_path, ports in compose_ports.items():
        compose_file = (ROOT / relative_path).read_text(encoding="utf-8")
        for port in ports:
            assert f'"127.0.0.1:{port}:{port}"' in compose_file


def test_stage_zero_instructions_use_the_resolved_external_directory() -> None:
    setup_script = (ROOT / "scripts" / "stage0_setup.ps1").read_text(encoding="utf-8")

    assert "Join-Path $external 'hrms/docker'" in setup_script
    assert "bash $onyxInstall" in setup_script
    assert "cd external/hrms/docker" not in setup_script


def test_openfga_healthchecks_probe_the_live_api() -> None:
    expected_probe = "/usr/local/bin/grpc_health_probe"
    for relative_path in ("compose.yaml", "docker/openfga/docker-compose.yml"):
        compose_file = (ROOT / relative_path).read_text(encoding="utf-8")
        assert expected_probe in compose_file
        assert '"-addr=:8081"' in compose_file
        assert '"version"' not in compose_file


def test_ci_installs_dev_extra_and_checks_the_built_image() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "uv sync --locked --extra dev" in workflow
    assert "docker build --tag hr-assistant-api:ci ." in workflow
    assert "http://localhost:8000/health" in workflow
