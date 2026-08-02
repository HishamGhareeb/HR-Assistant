"""Tenant role assignment synchronization into OpenFGA.

RAL/Frappe tenant roles become enforceable AI retrieval permissions only after
they are reflected in the OpenFGA tenant object. This module keeps that mapping
deterministic and tenant-scoped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .admin_controls import AccessRoleAssignment, TenantRole
from .openfga_client import tenant_object_id


class TenantRoleAssignmentStore(Protocol):
    def list_role_assignments(self, tenant_id: str) -> list[AccessRoleAssignment]: ...


class TupleWriter(Protocol):
    async def write_tuples(self, tuples: list[tuple[str, str, str]]) -> None: ...
    async def delete_tuples(self, tuples: list[tuple[str, str, str]]) -> None: ...


class TenantRoleSyncer(Protocol):
    async def sync_tenant_roles(
        self,
        *,
        tenant_id: str,
        store: TenantRoleAssignmentStore,
    ) -> "TenantRoleSyncResult": ...


OPENFGA_TENANT_ROLE_RELATIONS: dict[TenantRole, str] = {
    TenantRole.EMPLOYEE: "employee",
    TenantRole.MANAGER: "manager",
    TenantRole.HR_ADMIN: "hr_admin",
    TenantRole.SYSTEM_ADMIN: "system_admin",
}


@dataclass(frozen=True)
class TenantRoleSyncPlan:
    tenant_id: str
    desired_tuples: tuple[tuple[str, str, str], ...]
    stale_tuples: tuple[tuple[str, str, str], ...]

    @property
    def writes(self) -> int:
        return len(self.desired_tuples)

    @property
    def deletes(self) -> int:
        return len(self.stale_tuples)


@dataclass(frozen=True)
class TenantRoleSyncResult:
    tenant_id: str
    written: int
    deleted: int


class OpenFgaTenantRoleSyncer:
    """Sync tenant role assignments using an OpenFGA tuple writer."""

    def __init__(
        self,
        tuple_writer: TupleWriter,
        *,
        existing_tuples: set[tuple[str, str, str]] | None = None,
    ) -> None:
        self._tuple_writer = tuple_writer
        self._existing_tuples = existing_tuples

    async def sync_tenant_roles(
        self,
        *,
        tenant_id: str,
        store: TenantRoleAssignmentStore,
    ) -> TenantRoleSyncResult:
        return await sync_tenant_roles(
            tenant_id=tenant_id,
            store=store,
            tuple_writer=self._tuple_writer,
            existing_tuples=self._existing_tuples,
        )


def tenant_role_tuples(assignments: list[AccessRoleAssignment]) -> tuple[tuple[str, str, str], ...]:
    """Convert tenant role assignments into OpenFGA tenant relation tuples."""

    tuples: set[tuple[str, str, str]] = set()
    for assignment in assignments:
        tenant_object = tenant_object_id(assignment.tenant_id)
        for role in assignment.roles:
            relation = OPENFGA_TENANT_ROLE_RELATIONS[role]
            tuples.add((f"user:{assignment.user_id}", relation, tenant_object))
    return tuple(sorted(tuples))


def plan_tenant_role_sync(
    *,
    tenant_id: str,
    assignments: list[AccessRoleAssignment],
    existing_tuples: set[tuple[str, str, str]] | None = None,
) -> TenantRoleSyncPlan:
    """Create a tenant-scoped OpenFGA role-sync plan.

    `existing_tuples` is optional because some tuple writers can tolerate
    duplicate writes. When supplied, stale tenant-role tuples for this tenant
    are deleted and desired tuples are written. Foreign-tenant tuples are
    ignored even if they look similar.
    """

    desired = set(tenant_role_tuples(assignments))
    tenant_object = tenant_object_id(tenant_id)
    existing_for_tenant = {
        tuple_
        for tuple_ in (existing_tuples or set())
        if tuple_[2] == tenant_object and tuple_[1] in OPENFGA_TENANT_ROLE_RELATIONS.values()
    }

    stale = existing_for_tenant - desired
    to_write = desired if existing_tuples is None else desired - existing_for_tenant

    return TenantRoleSyncPlan(
        tenant_id=tenant_id,
        desired_tuples=tuple(sorted(to_write)),
        stale_tuples=tuple(sorted(stale)),
    )


async def sync_tenant_roles(
    *,
    tenant_id: str,
    store: TenantRoleAssignmentStore,
    tuple_writer: TupleWriter,
    existing_tuples: set[tuple[str, str, str]] | None = None,
) -> TenantRoleSyncResult:
    """Apply current tenant role assignments to OpenFGA."""

    assignments = store.list_role_assignments(tenant_id)
    plan = plan_tenant_role_sync(
        tenant_id=tenant_id,
        assignments=assignments,
        existing_tuples=existing_tuples,
    )
    await tuple_writer.delete_tuples(list(plan.stale_tuples))
    await tuple_writer.write_tuples(list(plan.desired_tuples))
    return TenantRoleSyncResult(
        tenant_id=tenant_id,
        written=plan.writes,
        deleted=plan.deletes,
    )
