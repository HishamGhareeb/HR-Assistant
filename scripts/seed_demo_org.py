#!/usr/bin/env python
"""Guided pilot setup: seed the deterministic synthetic demo organization
(``glue.demo_seed``) into a running Onyx + OpenFGA stack, then print the
scripted personas and sample questions a pilot walkthrough can use.

No real employee data is involved -- every record, persona, and question
here is fixed and fictional (``glue/demo_seed.py``).

Usage::

    ONYX_API_URL=... ONYX_API_KEY=... OPENFGA_API_URL=... OPENFGA_STORE_ID=... \\
        python scripts/seed_demo_org.py

Safe to re-run: ``SyncEngine`` diffs against its checkpoint store and only
re-applies what changed (nothing, the second time).

This does not touch ``HR_REVIEWERS_JSON`` / ``HR_ADMINS_JSON`` /
``HR_FEEDBACK_REVIEWERS_JSON`` in your running deployment -- it prints the
JSON snippets for the demo tenant's ``hr-demo`` persona so you can merge
them into whichever of those environment variables your deployment already
uses, rather than silently overwriting a real reviewer/admin map with demo
values.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

from glue.demo_seed import (
    DEMO_PERSONAS,
    DEMO_SAMPLE_QUESTIONS,
    DEMO_TENANT_ID,
    demo_admin_authorizer_map,
    demo_feedback_authorizer_map,
    demo_hr_admin_user_ids,
    demo_review_authorizer_map,
    seed_demo_organization,
)
from glue.frappe_sync import SyncConfig, SyncEngine
from glue.onyx_indexer import OnyxIndexer
from glue.openfga_client import OpenFgaTupleWriter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_demo_org")


class SeedDemoOrgError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SeedDemoOrgError(f"missing required environment variable: {name}")
    return value


async def run() -> None:
    onyx = OnyxIndexer(_required_env("ONYX_API_URL"), _required_env("ONYX_API_KEY"))
    tuple_writer = OpenFgaTupleWriter(
        _required_env("OPENFGA_API_URL"),
        _required_env("OPENFGA_STORE_ID"),
        os.environ.get("OPENFGA_MODEL_ID", ""),
    )
    engine = SyncEngine(onyx, tuple_writer, config=SyncConfig(hr_admin_user_ids=demo_hr_admin_user_ids()))

    report = await seed_demo_organization(engine)

    print(f"\nDemo tenant: {DEMO_TENANT_ID}")
    print(
        f"Sync result: {report.created} created, {report.updated} updated, "
        f"{report.unchanged} unchanged, {report.deleted} deleted, {len(report.failed)} failed"
    )
    if report.failed:
        for failure in report.failed:
            logger.error("failed: %s %s -- %s", failure.doctype, failure.name, failure.reason)
        raise SeedDemoOrgError(f"{len(report.failed)} demo record(s) failed to sync -- see above")

    print("\nScripted personas:")
    for persona in DEMO_PERSONAS:
        print(f"  - {persona.user_id} ({persona.display_name}, {persona.department}): {persona.role_description}")

    print("\nSample questions for a guided walkthrough:")
    for sample in DEMO_SAMPLE_QUESTIONS:
        print(f'  - [{sample.persona_user_id}] "{sample.question}"')
        print(f"      expected: {sample.expected_outcome} -- {sample.note}")

    print(
        "\nMerge the hr-demo persona into your deployment's tenant-scoped "
        "reviewer/admin maps (not overwritten automatically):"
    )
    print(f"  HR_REVIEWERS_JSON entry:          {json.dumps(demo_review_authorizer_map())}")
    print(f"  HR_ADMINS_JSON entry:             {json.dumps(demo_admin_authorizer_map())}")
    print(f"  HR_FEEDBACK_REVIEWERS_JSON entry: {json.dumps(demo_feedback_authorizer_map())}")


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        asyncio.run(run())
    except SeedDemoOrgError as exc:
        logger.error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
