"""Unit tests for the parts of scripts/provision_openfga.py that don't
need Docker or a live OpenFGA instance: seed-tuple parsing, idempotent
model-version comparison, and duplicate-tolerant tuple seeding.

transform_model_to_json / find_or_create_store / run() are intentionally
not covered here -- they're thin wiring around `docker run` and a live
OpenFGA API and are exercised manually per docs/OPENFGA_PROVISIONING.md.
"""
from __future__ import annotations

import pytest

from openfga_sdk.client.models import ClientTuple
from openfga_sdk.exceptions import NotFoundException

from scripts.provision_openfga import (
    ProvisionError,
    _model_content_matches,
    ensure_model,
    load_seed_tuples,
    seed_tuples,
)


# --- load_seed_tuples -------------------------------------------------


def test_load_seed_tuples_reads_store_tests_yaml():
    tuples = load_seed_tuples()
    assert len(tuples) > 0
    assert all(isinstance(t, ClientTuple) for t in tuples)
    assert any(t.object == "leave_record:acme__sarah_leave" for t in tuples)


# --- _model_content_matches ---------------------------------------------


class FakeTypeDef:
    def __init__(self, data: dict) -> None:
        self._data = data

    def to_dict(self) -> dict:
        return self._data


class FakeExistingModel:
    def __init__(self, type_definitions: list[dict]) -> None:
        self.type_definitions = [FakeTypeDef(d) for d in type_definitions]


def test_model_content_matches_identical_type_definitions():
    types = [{"type": "user"}, {"type": "department", "relations": {}}]
    existing = FakeExistingModel(types)
    new_model = {"type_definitions": types}
    assert _model_content_matches(existing, new_model) is True


def test_model_content_matches_detects_a_changed_relation():
    existing = FakeExistingModel([{"type": "user"}])
    new_model = {"type_definitions": [{"type": "user"}, {"type": "department"}]}
    assert _model_content_matches(existing, new_model) is False


# --- ensure_model ---------------------------------------------------------


class FakeWrittenModel:
    def __init__(self, model_id: str) -> None:
        self.authorization_model_id = model_id


class FakeReadAuthorizationModelResponse:
    """Mirrors the real SDK's ReadAuthorizationModelResponse -- the actual
    model lives on .authorization_model, it isn't the response itself
    (this file's ensure_model tests used to assume otherwise and passed
    against a shape the real SDK never returns -- see provision_openfga.py's
    ensure_model docstring)."""

    def __init__(self, authorization_model) -> None:
        self.authorization_model = authorization_model


class FakeModelClient:
    def __init__(self, latest=None, on_write_id: str = "new-model-id") -> None:
        self._latest = latest
        self._on_write_id = on_write_id
        self.write_calls = 0

    async def read_latest_authorization_model(self):
        if self._latest is None:
            # The real API 404s (raises NotFoundException) when the store
            # has no model yet -- it never returns a bare None.
            raise NotFoundException(status=404, reason="no authorization model")
        return FakeReadAuthorizationModelResponse(self._latest)

    async def write_authorization_model(self, body):
        self.write_calls += 1
        return FakeWrittenModel(self._on_write_id)


@pytest.mark.asyncio
async def test_ensure_model_writes_new_version_when_no_existing_model():
    client = FakeModelClient(latest=None)
    model_id = await ensure_model(client, {"schema_version": "1.1", "type_definitions": []})
    assert model_id == "new-model-id"
    assert client.write_calls == 1


@pytest.mark.asyncio
async def test_ensure_model_reuses_existing_model_when_content_matches():
    types = [{"type": "user"}]
    existing = FakeExistingModel(types)
    existing.id = "existing-model-id"
    client = FakeModelClient(latest=existing)

    model_id = await ensure_model(client, {"schema_version": "1.1", "type_definitions": types})

    assert model_id == "existing-model-id"
    assert client.write_calls == 0


@pytest.mark.asyncio
async def test_ensure_model_writes_new_version_when_content_differs():
    existing = FakeExistingModel([{"type": "user"}])
    existing.id = "existing-model-id"
    client = FakeModelClient(latest=existing, on_write_id="updated-model-id")

    model_id = await ensure_model(
        client, {"schema_version": "1.1", "type_definitions": [{"type": "user"}, {"type": "department"}]}
    )

    assert model_id == "updated-model-id"
    assert client.write_calls == 1


# --- seed_tuples ------------------------------------------------------------


class FakeSeedClient:
    def __init__(self, failing_objects: set[str] | None = None, error_message: str = "already exists") -> None:
        self._failing_objects = failing_objects or set()
        self._error_message = error_message
        self.written: list[ClientTuple] = []

    async def write_tuples(self, tuples: list[ClientTuple]):
        for t in tuples:
            if t.object in self._failing_objects:
                raise RuntimeError(f"{self._error_message}: {t.object}")
            self.written.append(t)


@pytest.mark.asyncio
async def test_seed_tuples_creates_all_when_none_exist():
    tuples = [
        ClientTuple(user="user:sarah", relation="owner", object="leave_record:acme__sarah_leave"),
        ClientTuple(user="user:david", relation="owner", object="leave_record:acme__david_leave"),
    ]
    client = FakeSeedClient()

    created, skipped = await seed_tuples(client, tuples)

    assert created == 2
    assert skipped == 0
    assert len(client.written) == 2


@pytest.mark.asyncio
async def test_seed_tuples_skips_ones_that_already_exist():
    tuples = [
        ClientTuple(user="user:sarah", relation="owner", object="leave_record:acme__sarah_leave"),
        ClientTuple(user="user:david", relation="owner", object="leave_record:acme__david_leave"),
    ]
    client = FakeSeedClient(failing_objects={"leave_record:acme__sarah_leave"})

    created, skipped = await seed_tuples(client, tuples)

    assert created == 1
    assert skipped == 1


@pytest.mark.asyncio
async def test_seed_tuples_raises_provision_error_on_a_real_failure():
    tuples = [ClientTuple(user="user:sarah", relation="owner", object="leave_record:acme__sarah_leave")]
    client = FakeSeedClient(
        failing_objects={"leave_record:acme__sarah_leave"}, error_message="internal server error"
    )

    with pytest.raises(ProvisionError):
        await seed_tuples(client, tuples)
