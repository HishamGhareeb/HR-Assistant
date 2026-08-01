from datetime import datetime, timezone

import pytest

from glue.admin_controls import AccessRoleAssignment, TenantRole
from glue.tenant_role_sync import (
    plan_tenant_role_sync,
    sync_tenant_roles,
    tenant_role_tuples,
)


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeAssignmentStore:
    def __init__(self, assignments):
        self._assignments = assignments

    def list_role_assignments(self, tenant_id: str):
        return [assignment for assignment in self._assignments if assignment.tenant_id == tenant_id]


class FakeTupleWriter:
    def __init__(self):
        self.writes = []
        self.deletes = []

    async def write_tuples(self, tuples):
        self.writes.append(list(tuples))

    async def delete_tuples(self, tuples):
        self.deletes.append(list(tuples))


def assignment(tenant_id="acme", user_id="sarah", roles=(TenantRole.EMPLOYEE,)):
    return AccessRoleAssignment(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=roles,
        updated_by="hr-1",
        updated_at=NOW,
    )


def test_tenant_role_tuples_map_assignments_to_tenant_object_relations():
    tuples = tenant_role_tuples(
        [
            assignment(roles=(TenantRole.EMPLOYEE, TenantRole.MANAGER)),
            assignment(user_id="morgan", roles=(TenantRole.HR_ADMIN,)),
        ]
    )

    assert tuples == (
        ("user:morgan", "hr_admin", "tenant:acme"),
        ("user:sarah", "employee", "tenant:acme"),
        ("user:sarah", "manager", "tenant:acme"),
    )


def test_sync_plan_ignores_foreign_tenant_existing_tuples():
    existing = {
        ("user:sarah", "employee", "tenant:globex"),
        ("user:old", "employee", "tenant:acme"),
    }

    plan = plan_tenant_role_sync(
        tenant_id="acme",
        assignments=[assignment()],
        existing_tuples=existing,
    )

    assert plan.desired_tuples == (("user:sarah", "employee", "tenant:acme"),)
    assert plan.stale_tuples == (("user:old", "employee", "tenant:acme"),)


def test_sync_plan_is_incremental_when_existing_tuples_are_supplied():
    existing = {
        ("user:sarah", "employee", "tenant:acme"),
        ("user:sarah", "manager", "tenant:acme"),
        ("user:old", "employee", "tenant:acme"),
    }

    plan = plan_tenant_role_sync(
        tenant_id="acme",
        assignments=[assignment(roles=(TenantRole.EMPLOYEE, TenantRole.HR_ADMIN))],
        existing_tuples=existing,
    )

    assert plan.desired_tuples == (("user:sarah", "hr_admin", "tenant:acme"),)
    assert plan.stale_tuples == (
        ("user:old", "employee", "tenant:acme"),
        ("user:sarah", "manager", "tenant:acme"),
    )


@pytest.mark.asyncio
async def test_sync_tenant_roles_applies_deletes_before_writes():
    store = FakeAssignmentStore([assignment(roles=(TenantRole.EMPLOYEE, TenantRole.HR_ADMIN))])
    writer = FakeTupleWriter()
    existing = {
        ("user:sarah", "employee", "tenant:acme"),
        ("user:sarah", "manager", "tenant:acme"),
    }

    result = await sync_tenant_roles(
        tenant_id="acme",
        store=store,
        tuple_writer=writer,
        existing_tuples=existing,
    )

    assert writer.deletes == [[("user:sarah", "manager", "tenant:acme")]]
    assert writer.writes == [[("user:sarah", "hr_admin", "tenant:acme")]]
    assert result.written == 1
    assert result.deleted == 1


@pytest.mark.asyncio
async def test_sync_tenant_roles_without_existing_snapshot_writes_all_desired_tuples():
    store = FakeAssignmentStore(
        [
            assignment("acme", "sarah", (TenantRole.EMPLOYEE,)),
            assignment("globex", "sarah", (TenantRole.HR_ADMIN,)),
        ]
    )
    writer = FakeTupleWriter()

    result = await sync_tenant_roles(
        tenant_id="acme",
        store=store,
        tuple_writer=writer,
    )

    assert writer.deletes == [[]]
    assert writer.writes == [[("user:sarah", "employee", "tenant:acme")]]
    assert result.tenant_id == "acme"
    assert result.written == 1
    assert result.deleted == 0
