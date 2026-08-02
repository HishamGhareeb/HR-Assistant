import pytest

from glue.admin_controls import TenantRole
from glue.domain import Identity
from glue.frappe_sync import FrappeRecord, SyncConfig, SyncEngine
from glue.sqlite_admin_controls import SqliteAdminControlStore


class FakeDocumentIndex:
    def __init__(self, *, fail_next: bool = False) -> None:
        self.documents: dict[str, dict] = {}
        self.fail_next = fail_next

    async def upsert(self, *, document_id, semantic_identifier, text, metadata):
        if self.fail_next:
            self.fail_next = False
            raise ConnectionError("onyx unavailable")
        already_existed = document_id in self.documents
        self.documents[document_id] = {
            "semantic_identifier": semantic_identifier,
            "text": text,
            "metadata": metadata,
        }
        return already_existed

    async def delete(self, document_id):
        self.documents.pop(document_id, None)


class FakeTupleWriter:
    def __init__(self) -> None:
        self.tuples: set[tuple[str, str, str]] = set()

    async def write_tuples(self, tuples):
        self.tuples.update(tuples)

    async def delete_tuples(self, tuples):
        for tuple_ in tuples:
            self.tuples.discard(tuple_)


def identity(tenant_id: str = "acme", user_id: str = "hr-1") -> Identity:
    return Identity(tenant_id=tenant_id, user_id=user_id)


def hr_policy(tenant_id: str = "acme") -> FrappeRecord:
    return FrappeRecord(
        doctype="HR Policy",
        name="POL-1",
        tenant_id=tenant_id,
        fields={"title": "Leave Policy", "body": "Employees get 21 days of annual leave."},
    )


def sync_engine(index: FakeDocumentIndex | None = None) -> SyncEngine:
    return SyncEngine(index or FakeDocumentIndex(), FakeTupleWriter(), config=SyncConfig(hr_admin_user_ids=("hr-1",)))


def test_sqlite_admin_roles_persist_and_remain_tenant_scoped(tmp_path):
    path = tmp_path / "admin.sqlite3"
    store = SqliteAdminControlStore(path)
    store.set_role_assignment(
        identity=identity("acme", "hr-1"),
        user_id="sarah",
        roles=(TenantRole.EMPLOYEE, TenantRole.MANAGER),
    )
    store.set_role_assignment(
        identity=identity("globex", "hr-2"),
        user_id="sarah",
        roles=(TenantRole.HR_ADMIN,),
    )

    restored = SqliteAdminControlStore(path)

    acme = restored.list_role_assignments("acme")
    globex = restored.list_role_assignments("globex")
    assert [(assignment.user_id, assignment.roles) for assignment in acme] == [
        ("sarah", (TenantRole.EMPLOYEE, TenantRole.MANAGER))
    ]
    assert [(assignment.user_id, assignment.roles) for assignment in globex] == [
        ("sarah", (TenantRole.HR_ADMIN,))
    ]


@pytest.mark.asyncio
async def test_sqlite_admin_sync_runs_and_source_status_persist(tmp_path):
    path = tmp_path / "admin.sqlite3"
    index = FakeDocumentIndex()
    store = SqliteAdminControlStore(path)

    summary = await store.synthetic_resync(
        identity=identity(),
        source_id="synthetic-fixture",
        records=[hr_policy()],
        sync_engine=sync_engine(index),
    )

    restored = SqliteAdminControlStore(path)
    runs = restored.list_runs("acme")
    sources = restored.list_sources("acme")

    assert summary.status == "completed"
    assert [(run.run_id, run.source_id, run.status) for run in runs] == [
        (summary.run_id, "synthetic-fixture", "completed")
    ]
    assert [(source.source_id, source.last_run_id, source.last_status) for source in sources] == [
        ("synthetic-fixture", summary.run_id, "completed")
    ]


@pytest.mark.asyncio
async def test_sqlite_admin_failed_sync_is_durable_and_retryable(tmp_path):
    path = tmp_path / "admin.sqlite3"
    index = FakeDocumentIndex(fail_next=True)
    store = SqliteAdminControlStore(path)
    engine = sync_engine(index)

    failed = await store.synthetic_resync(
        identity=identity(),
        source_id="synthetic-fixture",
        records=[hr_policy()],
        sync_engine=engine,
    )
    retried = await SqliteAdminControlStore(path).synthetic_resync(
        identity=identity(),
        source_id="synthetic-fixture",
        records=[hr_policy()],
        sync_engine=engine,
    )

    restored = SqliteAdminControlStore(path)
    runs = restored.list_runs("acme")

    assert failed.status == "failed"
    assert failed.failed[0].name == "POL-1"
    assert retried.status == "completed"
    assert [run.status for run in runs] == ["completed", "failed"]


@pytest.mark.asyncio
async def test_sqlite_admin_revoke_updates_source_status_without_frappe_mutation(tmp_path):
    path = tmp_path / "admin.sqlite3"
    index = FakeDocumentIndex()
    store = SqliteAdminControlStore(path)
    engine = sync_engine(index)
    await store.synthetic_resync(
        identity=identity(),
        source_id="synthetic-fixture",
        records=[hr_policy()],
        sync_engine=engine,
    )

    revoked = await store.synthetic_revoke(
        identity=identity(),
        source_id="synthetic-fixture",
        doctype="HR Policy",
        name="POL-1",
        sync_engine=engine,
    )

    restored = SqliteAdminControlStore(path)
    assert revoked.deleted == 1
    assert restored.list_sources("acme")[0].last_action == "synthetic_revoke"
    assert restored.frappe_mutation_attempts == 0
