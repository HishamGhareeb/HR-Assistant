"""SQLite-backed durable HR admin control store.

This preserves the AdminControlStore boundary while making role assignments,
synthetic sync runs, and source status survive process restarts. It is a
single-node bridge toward the production PostgreSQL/RLS store; it is not the
final multi-tenant database architecture.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .admin_controls import (
    AccessRoleAssignment,
    AdminRecordFailure,
    SourceStatus,
    SyncRunSummary,
    TenantRole,
)
from .domain import Identity
from .frappe_sync import FrappeRecord, ReconciliationReport, SyncEngine


class SqliteAdminControlStore:
    """Durable implementation of the HR admin controls protocol."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # The store still has no Frappe write dependency. Existing tests and
        # future audit checks can assert this remains zero.
        self.frappe_mutation_attempts = 0
        self._init_schema()

    def list_sources(self, tenant_id: str) -> list[SourceStatus]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM source_statuses
                WHERE tenant_id = ?
                ORDER BY updated_at DESC, source_id ASC
                """,
                (tenant_id,),
            ).fetchall()
        return [_load_source_status(row["payload_json"]) for row in rows]

    def list_runs(self, tenant_id: str) -> list[SyncRunSummary]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM sync_runs
                WHERE tenant_id = ?
                ORDER BY started_at DESC, run_id DESC
                """,
                (tenant_id,),
            ).fetchall()
        return [_load_sync_run(row["payload_json"]) for row in rows]

    async def synthetic_resync(
        self,
        *,
        identity: Identity,
        source_id: str,
        records: list[FrappeRecord],
        sync_engine: SyncEngine,
    ) -> SyncRunSummary:
        safe_source_id = _clean(source_id)
        tenant_records = [
            FrappeRecord(
                doctype=record.doctype,
                name=record.name,
                tenant_id=identity.tenant_id,
                fields=dict(record.fields),
                deleted=record.deleted,
            )
            for record in records
        ]
        report = await sync_engine.sync_all(identity.tenant_id, tenant_records)
        return self._record_run(source_id=safe_source_id, action="synthetic_resync", report=report)

    async def synthetic_revoke(
        self,
        *,
        identity: Identity,
        source_id: str,
        doctype: str,
        name: str,
        sync_engine: SyncEngine,
    ) -> SyncRunSummary:
        safe_source_id = _clean(source_id)
        record = FrappeRecord(
            doctype=_clean(doctype),
            name=_clean(name),
            tenant_id=identity.tenant_id,
            deleted=True,
        )
        report = await sync_engine.sync_all(identity.tenant_id, [record])
        return self._record_run(source_id=safe_source_id, action="synthetic_revoke", report=report)

    def list_role_assignments(self, tenant_id: str) -> list[AccessRoleAssignment]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM access_role_assignments
                WHERE tenant_id = ?
                ORDER BY user_id ASC
                """,
                (tenant_id,),
            ).fetchall()
        return [_load_role_assignment(row["payload_json"]) for row in rows]

    def set_role_assignment(
        self,
        *,
        identity: Identity,
        user_id: str,
        roles: tuple[TenantRole, ...],
    ) -> AccessRoleAssignment:
        safe_user_id = _clean(user_id)
        unique_roles = tuple(dict.fromkeys(roles))
        assignment = AccessRoleAssignment(
            tenant_id=identity.tenant_id,
            user_id=safe_user_id,
            roles=unique_roles,
            updated_by=identity.user_id,
            updated_at=datetime.now(timezone.utc),
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO access_role_assignments (
                    tenant_id,
                    user_id,
                    updated_at,
                    payload_json
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(tenant_id, user_id)
                DO UPDATE SET updated_at = excluded.updated_at, payload_json = excluded.payload_json
                """,
                (
                    assignment.tenant_id,
                    assignment.user_id,
                    assignment.updated_at.isoformat(),
                    _dump_role_assignment(assignment),
                ),
            )
            conn.commit()
        return assignment

    def _record_run(self, *, source_id: str, action: str, report: ReconciliationReport) -> SyncRunSummary:
        summary = SyncRunSummary.from_report(source_id=source_id, action=action, report=report)
        status = SourceStatus(
            tenant_id=summary.tenant_id,
            source_id=source_id,
            last_action=action,
            last_status=summary.status,
            last_run_id=summary.run_id,
            updated_at=summary.finished_at or datetime.now(timezone.utc),
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_runs (
                    tenant_id,
                    run_id,
                    source_id,
                    action,
                    status,
                    started_at,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.tenant_id,
                    summary.run_id,
                    summary.source_id,
                    summary.action,
                    summary.status,
                    summary.started_at.isoformat(),
                    _dump_sync_run(summary),
                ),
            )
            conn.execute(
                """
                INSERT INTO source_statuses (
                    tenant_id,
                    source_id,
                    updated_at,
                    payload_json
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(tenant_id, source_id)
                DO UPDATE SET updated_at = excluded.updated_at, payload_json = excluded.payload_json
                """,
                (
                    status.tenant_id,
                    status.source_id,
                    status.updated_at.isoformat(),
                    _dump_source_status(status),
                ),
            )
            conn.commit()
        return summary

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS access_role_assignments (
                    tenant_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_runs (
                    tenant_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, run_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_statuses (
                    tenant_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, source_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sync_runs_tenant_started
                ON sync_runs (tenant_id, started_at)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_source_statuses_tenant_updated
                ON source_statuses (tenant_id, updated_at)
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn


def _dump_role_assignment(assignment: AccessRoleAssignment) -> str:
    return _dump_json(
        {
            "tenant_id": assignment.tenant_id,
            "user_id": assignment.user_id,
            "roles": [role.value for role in assignment.roles],
            "updated_by": assignment.updated_by,
            "updated_at": assignment.updated_at.isoformat(),
        }
    )


def _load_role_assignment(payload: str) -> AccessRoleAssignment:
    data = json.loads(payload)
    return AccessRoleAssignment(
        tenant_id=data["tenant_id"],
        user_id=data["user_id"],
        roles=tuple(TenantRole(role) for role in data["roles"]),
        updated_by=data["updated_by"],
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


def _dump_sync_run(summary: SyncRunSummary) -> str:
    data = asdict(summary)
    data["started_at"] = summary.started_at.isoformat()
    data["finished_at"] = summary.finished_at.isoformat() if summary.finished_at else None
    return _dump_json(data)


def _load_sync_run(payload: str) -> SyncRunSummary:
    data = json.loads(payload)
    return SyncRunSummary(
        run_id=data["run_id"],
        tenant_id=data["tenant_id"],
        source_id=data["source_id"],
        action=data["action"],
        status=data["status"],
        created=data["created"],
        updated=data["updated"],
        deleted=data["deleted"],
        unchanged=data["unchanged"],
        failed=tuple(AdminRecordFailure(**failure) for failure in data["failed"]),
        started_at=datetime.fromisoformat(data["started_at"]),
        finished_at=datetime.fromisoformat(data["finished_at"]) if data["finished_at"] else None,
    )


def _dump_source_status(status: SourceStatus) -> str:
    data = asdict(status)
    data["updated_at"] = status.updated_at.isoformat()
    return _dump_json(data)


def _load_source_status(payload: str) -> SourceStatus:
    data = json.loads(payload)
    return SourceStatus(
        tenant_id=data["tenant_id"],
        source_id=data["source_id"],
        last_action=data["last_action"],
        last_status=data["last_status"],
        last_run_id=data["last_run_id"],
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


def _dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _clean(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value
