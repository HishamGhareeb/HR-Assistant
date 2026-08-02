"""PostgreSQL/RLS schema contract helpers.

The migration SQL is the source of truth. These helpers let tests assert that
the checked-in production persistence contract preserves tenant isolation and
the current suggestion/admin state-machine invariants.
"""

from __future__ import annotations

from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "migrations"
    / "0001_tenant_rls_foundation.sql"
)

TENANT_SCOPED_TABLES = (
    "tenant_users",
    "tenant_user_roles",
    "suggestions",
    "suggestion_decisions",
    "integration_sync_runs",
    "integration_source_statuses",
)


def load_tenant_rls_migration() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")
