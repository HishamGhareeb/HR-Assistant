"""Tenant-scoped HR admin controls for ingestion, sync visibility, and
access mapping.

These controls are intentionally synthetic/read-only: they can run the
existing RAL HRMS -> Onyx/OpenFGA sync engine against supplied records or a
synthetic deletion record, but they do not contain a RAL HRMS client and
cannot mutate RAL HRMS. They are operator controls around the ingestion
pipeline, not a source-system write path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import threading
from typing import Protocol
from uuid import uuid4

from .domain import Identity
from .hr_source_sync import HrSourceRecord, ReconciliationReport, SyncEngine


class AdminAuthorizationError(PermissionError):
    pass


class AdminSyncNotConfiguredError(RuntimeError):
    pass


class TenantRole(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR_ADMIN = "hr_admin"
    SYSTEM_ADMIN = "system_admin"


class HrAdminAuthorizer(Protocol):
    def authorize(self, identity: Identity) -> None: ...


class StaticHrAdminAuthorizer:
    """Tenant-scoped admin map.

    A user listed for one tenant has no authority in another tenant unless
    that tenant has its own explicit entry. There is no global admin or
    reviewer bypass.
    """

    def __init__(self, admins_by_tenant: dict[str, set[str] | list[str] | tuple[str, ...]]) -> None:
        self._admins_by_tenant = {
            tenant.strip(): {user.strip() for user in users if user.strip()}
            for tenant, users in admins_by_tenant.items()
            if tenant.strip()
        }

    def authorize(self, identity: Identity) -> None:
        if identity.user_id not in self._admins_by_tenant.get(identity.tenant_id, set()):
            raise AdminAuthorizationError("caller is not authorized for HR admin controls")


@dataclass(frozen=True)
class AccessRoleAssignment:
    tenant_id: str
    user_id: str
    roles: tuple[TenantRole, ...]
    updated_by: str
    updated_at: datetime


@dataclass(frozen=True)
class AdminRecordFailure:
    doctype: str
    name: str
    reason: str


@dataclass(frozen=True)
class SyncRunSummary:
    run_id: str
    tenant_id: str
    source_id: str
    action: str
    status: str
    created: int
    updated: int
    deleted: int
    unchanged: int
    failed: tuple[AdminRecordFailure, ...]
    started_at: datetime
    finished_at: datetime | None

    @classmethod
    def from_report(cls, *, source_id: str, action: str, report: ReconciliationReport) -> "SyncRunSummary":
        failures = tuple(AdminRecordFailure(f.doctype, f.name, f.reason) for f in report.failed)
        return cls(
            run_id=uuid4().hex,
            tenant_id=report.tenant_id,
            source_id=source_id,
            action=action,
            status="failed" if failures else "completed",
            created=report.created,
            updated=report.updated,
            deleted=report.deleted,
            unchanged=report.unchanged,
            failed=failures,
            started_at=report.started_at,
            finished_at=report.finished_at,
        )


@dataclass(frozen=True)
class SourceStatus:
    tenant_id: str
    source_id: str
    last_action: str
    last_status: str
    last_run_id: str
    updated_at: datetime


class AdminControlStore(Protocol):
    def list_sources(self, tenant_id: str) -> list[SourceStatus]: ...
    def list_runs(self, tenant_id: str) -> list[SyncRunSummary]: ...
    async def synthetic_resync(
        self,
        *,
        identity: Identity,
        source_id: str,
        records: list[HrSourceRecord],
        sync_engine: SyncEngine,
    ) -> SyncRunSummary: ...
    async def synthetic_revoke(
        self,
        *,
        identity: Identity,
        source_id: str,
        doctype: str,
        name: str,
        sync_engine: SyncEngine,
    ) -> SyncRunSummary: ...
    def list_role_assignments(self, tenant_id: str) -> list[AccessRoleAssignment]: ...
    def set_role_assignment(
        self,
        *,
        identity: Identity,
        user_id: str,
        roles: tuple[TenantRole, ...],
    ) -> AccessRoleAssignment: ...


class InMemoryAdminControlStore:
    def __init__(self) -> None:
        self._sources: dict[tuple[str, str], SourceStatus] = {}
        self._runs: list[SyncRunSummary] = []
        self._roles: dict[tuple[str, str], AccessRoleAssignment] = {}
        self._lock = threading.Lock()
        # Tests can assert this remains zero; the store has no RAL HRMS write
        # dependency and never increments it.
        self.source_mutation_attempts = 0

    def list_sources(self, tenant_id: str) -> list[SourceStatus]:
        with self._lock:
            statuses = [status for status in self._sources.values() if status.tenant_id == tenant_id]
        return sorted(statuses, key=lambda status: status.updated_at, reverse=True)

    def list_runs(self, tenant_id: str) -> list[SyncRunSummary]:
        with self._lock:
            runs = [run for run in self._runs if run.tenant_id == tenant_id]
        return list(reversed(runs))

    async def synthetic_resync(
        self,
        *,
        identity: Identity,
        source_id: str,
        records: list[HrSourceRecord],
        sync_engine: SyncEngine,
    ) -> SyncRunSummary:
        safe_source_id = _clean(source_id)
        tenant_records = [
            HrSourceRecord(
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
        record = HrSourceRecord(
            doctype=_clean(doctype),
            name=_clean(name),
            tenant_id=identity.tenant_id,
            deleted=True,
        )
        report = await sync_engine.sync_all(identity.tenant_id, [record])
        return self._record_run(source_id=safe_source_id, action="synthetic_revoke", report=report)

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
        with self._lock:
            self._runs.append(summary)
            self._sources[(summary.tenant_id, source_id)] = status
        return summary

    def list_role_assignments(self, tenant_id: str) -> list[AccessRoleAssignment]:
        with self._lock:
            assignments = [assignment for assignment in self._roles.values() if assignment.tenant_id == tenant_id]
        return sorted(assignments, key=lambda assignment: assignment.user_id)

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
        with self._lock:
            self._roles[(identity.tenant_id, safe_user_id)] = assignment
        return assignment


def _clean(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value
