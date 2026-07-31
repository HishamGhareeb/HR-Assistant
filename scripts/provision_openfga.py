#!/usr/bin/env python
"""Reproducibly provision an OpenFGA store + authorization model, and
optionally seed local/dev tuples, against a running OpenFGA instance
(``docker compose -f docker/openfga/docker-compose.yml up`` per the
README).

Safe to re-run: finds-or-creates the store by name, only writes a new
model version when the transformed model differs from the latest one
already stored, and tolerates tuples that already exist when seeding.

Usage::

    OPENFGA_API_URL=http://localhost:8080 python scripts/provision_openfga.py
    OPENFGA_API_URL=http://localhost:8080 python scripts/provision_openfga.py --seed

Requires Docker running (already a hard prerequisite for this repo, see
README.md) -- ``openfga/model.fga``'s human-authored DSL is transformed to
the JSON the OpenFGA API actually accepts via the official
``openfga/cli`` image, so the DSL stays the single source of truth instead
of a hand-maintained JSON copy drifting out of sync with it.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import yaml
from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.models import ClientTuple
from openfga_sdk.models import CreateStoreRequest, WriteAuthorizationModelRequest

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("provision_openfga")

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENFGA_DIR = REPO_ROOT / "openfga"
MODEL_FILE = OPENFGA_DIR / "model.fga"
STORE_TESTS_FILE = OPENFGA_DIR / "store-tests.yaml"
DEFAULT_STORE_NAME = "hr-assistant-dev"


class ProvisionError(RuntimeError):
    pass


def transform_model_to_json(model_file: Path = MODEL_FILE) -> dict:
    """Transform the DSL model to the JSON shape the OpenFGA API accepts,
    via the official `openfga/cli` Docker image -- there is no maintained
    pure-Python DSL parser, and hand-transcribing the JSON would let it
    silently drift from `model.fga`."""
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{model_file.parent}:/openfga",
                "openfga/cli:latest",
                "model",
                "transform",
                "--file",
                f"/openfga/{model_file.name}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise ProvisionError(
            "docker is required to transform openfga/model.fga -- install/start Docker Desktop"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise ProvisionError(f"openfga/cli model transform failed: {exc.stderr}") from exc

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProvisionError(f"openfga/cli model transform returned non-JSON output: {exc}") from exc


async def find_or_create_store(client: OpenFgaClient, name: str) -> str:
    existing = await client.list_stores(options={"name": name})
    for store in existing.stores or []:
        if store.name == name:
            logger.info("using existing store %r (%s)", name, store.id)
            return store.id

    created = await client.create_store(CreateStoreRequest(name=name))
    logger.info("created store %r (%s)", name, created.id)
    return created.id


def _model_content_matches(existing_model, new_model_json: dict) -> bool:
    """Best-effort comparison: type_definitions is what actually encodes
    the model's relations. Not a guaranteed-exact diff -- server-side
    normalization can cause a semantically-unchanged model to compare as
    different, in which case a redundant (but harmless) new version gets
    written."""
    existing_types = [t.to_dict() for t in (existing_model.type_definitions or [])]
    new_types = new_model_json.get("type_definitions", [])
    return existing_types == new_types


async def ensure_model(client: OpenFgaClient, model_json: dict) -> str:
    latest = await client.read_latest_authorization_model()
    if latest is not None and _model_content_matches(latest, model_json):
        logger.info("authorization model unchanged, reusing %s", latest.id)
        return latest.id

    written = await client.write_authorization_model(WriteAuthorizationModelRequest(**model_json))
    logger.info("wrote new authorization model version %s", written.authorization_model_id)
    return written.authorization_model_id


def load_seed_tuples(store_tests_file: Path = STORE_TESTS_FILE) -> list[ClientTuple]:
    data = yaml.safe_load(store_tests_file.read_text())
    return [
        ClientTuple(user=t["user"], relation=t["relation"], object=t["object"])
        for t in data.get("tuples", [])
    ]


async def seed_tuples(client: OpenFgaClient, tuples: list[ClientTuple]) -> tuple[int, int]:
    """Write tuples one at a time so an already-existing tuple can be
    skipped without losing the rest of the batch. The seed set here is
    small (dev/demo fixtures), so per-tuple round trips are an acceptable
    trade for that simplicity -- do not reuse this loop for bulk sync."""
    created = 0
    skipped = 0
    for t in tuples:
        try:
            await client.write_tuples([t])
            created += 1
        except Exception as exc:  # noqa: BLE001 -- see docstring: distinguish duplicate vs real failure
            message = str(exc).lower()
            if "already exists" in message or "duplicate" in message:
                skipped += 1
                continue
            raise ProvisionError(f"failed to write tuple {t.user} {t.relation} {t.object}: {exc}") from exc
    return created, skipped


async def run(store_name: str, seed: bool) -> None:
    api_url = os.environ.get("OPENFGA_API_URL")
    if not api_url:
        raise ProvisionError("OPENFGA_API_URL must be set")

    model_json = transform_model_to_json()

    async with OpenFgaClient(ClientConfiguration(api_url=api_url)) as bootstrap_client:
        store_id = await find_or_create_store(bootstrap_client, store_name)

    async with OpenFgaClient(ClientConfiguration(api_url=api_url, store_id=store_id)) as client:
        model_id = await ensure_model(client, model_json)

        if seed:
            tuples = load_seed_tuples()
            created, skipped = await seed_tuples(client, tuples)
            logger.info("seeded tuples: %d created, %d already present", created, skipped)

    print(f"OPENFGA_STORE_ID={store_id}")
    print(f"OPENFGA_MODEL_ID={model_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--store-name",
        default=os.environ.get("OPENFGA_STORE_NAME", DEFAULT_STORE_NAME),
        help=f"OpenFGA store name to find or create (default: {DEFAULT_STORE_NAME})",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="also seed the local/dev tuples from openfga/store-tests.yaml",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run(args.store_name, args.seed))
    except ProvisionError as exc:
        logger.error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
