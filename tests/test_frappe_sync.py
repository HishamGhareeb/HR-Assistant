"""Synthetic end-to-end tests for the Frappe -> Onyx/OpenFGA sync, per
HIS-15's acceptance criteria ("Synthetic end-to-end tests only"). No live
Frappe, Onyx, or OpenFGA -- FakeDocumentIndex/FakeTupleWriter stand in for
glue.onyx_indexer.OnyxIndexer / glue.openfga_client.OpenFgaTupleWriter.
"""
from __future__ import annotations

import pytest

from glue.domain import DocumentType
from glue.frappe_sync import (
    FrappeMappingError,
    FrappeRecord,
    InMemoryCheckpointStore,
    SyncConfig,
    SyncEngine,
    document_object_id,
    map_record,
)
from glue.openfga_client import scoped_object_id


class FakeDocumentIndex:
    def __init__(self) -> None:
        self.documents: dict[str, dict] = {}
        self.upsert_calls = 0
        self.delete_calls = 0

    async def upsert(self, *, document_id, semantic_identifier, text, metadata):
        already_existed = document_id in self.documents
        self.upsert_calls += 1
        self.documents[document_id] = {
            "semantic_identifier": semantic_identifier,
            "text": text,
            "metadata": metadata,
        }
        return already_existed

    async def delete(self, document_id):
        self.delete_calls += 1
        self.documents.pop(document_id, None)


class FakeTupleWriter:
    def __init__(self) -> None:
        self.tuples: set[tuple[str, str, str]] = set()
        self.write_calls: list[list[tuple]] = []
        self.delete_calls: list[list[tuple]] = []

    async def write_tuples(self, tuples):
        self.write_calls.append(list(tuples))
        self.tuples.update(tuples)

    async def delete_tuples(self, tuples):
        self.delete_calls.append(list(tuples))
        for t in tuples:
            self.tuples.discard(t)


def employee(user_id="sarah", department="engineering", tenant_id="acme", reports_to=None, name="EMP-sarah"):
    return FrappeRecord(
        doctype="Employee",
        name=name,
        tenant_id=tenant_id,
        fields={"user_id": user_id, "department": department, "employee_name": user_id.title(), **({"reports_to": reports_to} if reports_to else {})},
    )


def leave_application(name="LA-1", user_id="sarah", department="engineering", tenant_id="acme", status="approved"):
    return FrappeRecord(
        doctype="Leave Application",
        name=name,
        tenant_id=tenant_id,
        fields={"employee_user_id": user_id, "department": department, "leave_type": "annual", "status": status},
    )


def salary_slip(name="SAL-1", user_id="sarah", tenant_id="acme"):
    return FrappeRecord(
        doctype="Salary Slip",
        name=name,
        tenant_id=tenant_id,
        fields={"employee_user_id": user_id, "period": "2026-01"},
    )


def appraisal(name="APP-1", user_id="sarah", department="engineering", tenant_id="acme"):
    return FrappeRecord(
        doctype="Appraisal",
        name=name,
        tenant_id=tenant_id,
        fields={"employee_user_id": user_id, "department": department, "summary": "Performance review on file."},
    )


def hr_policy(name="POL-1", tenant_id="acme"):
    return FrappeRecord(
        doctype="HR Policy",
        name=name,
        tenant_id=tenant_id,
        fields={"title": "Leave Policy", "body": "Employees get 21 days of annual leave."},
    )


# --- map_record: pure mapping -------------------------------------------


def test_map_employee_produces_department_membership_tuple():
    result = map_record(employee(), SyncConfig())
    assert result.document.object_type == DocumentType.EMPLOYEE_RECORD
    tuple_fields = [(t.user, t.relation, t.object_type, t.object_local_id) for t in result.tuples]
    assert ("user:sarah", "member", "department", "engineering") in tuple_fields


def test_map_employee_with_manager_adds_manager_tuple():
    result = map_record(employee(reports_to="morgan"), SyncConfig())
    tuple_fields = [(t.user, t.relation, t.object_type, t.object_local_id) for t in result.tuples]
    assert ("user:morgan", "manager", "department", "engineering") in tuple_fields


def test_map_employee_missing_user_id_raises():
    bad = FrappeRecord(doctype="Employee", name="EMP-x", tenant_id="acme", fields={"department": "engineering"})
    with pytest.raises(FrappeMappingError):
        map_record(bad, SyncConfig())


def test_map_department_produces_no_document_or_tuples():
    department = FrappeRecord(doctype="Department", name="engineering", tenant_id="acme", fields={})
    result = map_record(department, SyncConfig())
    assert result.document is None
    assert result.tuples == ()


def test_map_leave_application_includes_hr_admin_tuples():
    config = SyncConfig(hr_admin_user_ids=("hr_admin1",))
    result = map_record(leave_application(), config)
    tuple_fields = [(t.user, t.relation, t.object_type, t.object_local_id) for t in result.tuples]
    assert ("user:sarah", "owner", "leave_record", "LA-1") in tuple_fields
    assert ("leave_record:LA-1", "department", "department", "engineering") in tuple_fields
    assert ("user:hr_admin1", "hr_admin", "leave_record", "LA-1") in tuple_fields


def test_map_salary_slip_has_no_department_tuple():
    result = map_record(salary_slip(), SyncConfig())
    object_types_for_department_relation = [t.object_local_id for t in result.tuples if t.relation == "department"]
    assert object_types_for_department_relation == []


def test_map_hr_policy_grants_public_viewer():
    result = map_record(hr_policy(), SyncConfig())
    tuple_fields = [(t.user, t.relation, t.object_type, t.object_local_id) for t in result.tuples]
    assert ("user:*", "viewer", "policy_document", "POL-1") in tuple_fields


def test_map_record_rejects_unsupported_doctype():
    weird = FrappeRecord(doctype="Something Else", name="x", tenant_id="acme", fields={})
    with pytest.raises(FrappeMappingError):
        map_record(weird, SyncConfig())


# --- SyncEngine: idempotent upsert -------------------------------------


@pytest.mark.asyncio
async def test_sync_all_creates_documents_and_tuples():
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples, config=SyncConfig(hr_admin_user_ids=("hr_admin1",)))

    records = [employee(), leave_application(), appraisal(), salary_slip(), hr_policy()]
    report = await engine.sync_all("acme", records)

    assert report.created == 5
    assert report.updated == 0
    assert report.failed == []
    assert len(index.documents) == 5  # employee, leave, appraisal, salary, policy all index
    assert scoped_object_id("leave_record", "acme", "LA-1") in {t[2] for t in tuples.tuples}
    metadata_by_type = {doc["metadata"]["record_type"]: doc["metadata"] for doc in index.documents.values()}
    assert metadata_by_type["policy_document"]["classification"] == "public"
    assert metadata_by_type["performance_record"]["classification"] == "manager_only"
    assert metadata_by_type["salary_record"]["classification"] == "hr_only"


@pytest.mark.asyncio
async def test_sync_all_is_idempotent_on_a_second_identical_run():
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples)
    records = [employee(), leave_application()]

    first = await engine.sync_all("acme", records)
    second = await engine.sync_all("acme", records)

    assert first.created == 2
    assert second.created == 0
    assert second.updated == 0
    assert second.unchanged == 2
    # No redundant upserts/writes on the unchanged second pass: 2 write
    # calls total (one per record), both from the first run.
    assert index.upsert_calls == 2
    assert len(tuples.write_calls) == 2


@pytest.mark.asyncio
async def test_changed_record_triggers_update_not_recreate():
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples)

    await engine.sync_all("acme", [leave_application(status="pending")])
    report = await engine.sync_all("acme", [leave_application(status="approved")])

    assert report.updated == 1
    assert report.created == 0
    doc_id = document_object_id(leave_application(), map_record(leave_application(), SyncConfig()).document)
    assert "approved" in index.documents[doc_id]["text"]


@pytest.mark.asyncio
async def test_employee_moving_departments_retracts_old_department_tuple():
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples)

    await engine.sync_all("acme", [employee(department="engineering")])
    assert scoped_object_id("department", "acme", "engineering") in {t[2] for t in tuples.tuples}

    await engine.sync_all("acme", [employee(department="sales")])

    active_objects = {t[2] for t in tuples.tuples}
    assert scoped_object_id("department", "acme", "sales") in active_objects
    assert scoped_object_id("department", "acme", "engineering") not in active_objects


# --- SyncEngine: deletion -------------------------------------------------


@pytest.mark.asyncio
async def test_deleted_record_is_retracted_from_index_and_tuples():
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples, config=SyncConfig(hr_admin_user_ids=("hr_admin1",)))

    await engine.sync_all("acme", [leave_application()])
    assert len(index.documents) == 1
    assert len(tuples.tuples) > 0

    deleted_record = FrappeRecord(doctype="Leave Application", name="LA-1", tenant_id="acme", deleted=True)
    report = await engine.sync_all("acme", [deleted_record])

    assert report.deleted == 1
    assert index.documents == {}
    assert tuples.tuples == set()


@pytest.mark.asyncio
async def test_deleting_an_already_deleted_record_is_a_no_op():
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples)

    deleted_record = FrappeRecord(doctype="Leave Application", name="LA-1", tenant_id="acme", deleted=True)
    report = await engine.sync_all("acme", [deleted_record])

    assert report.deleted == 0
    assert report.unchanged == 1


# --- SyncEngine: retryable checkpoints on failure -------------------------


class FlakyDocumentIndex(FakeDocumentIndex):
    def __init__(self, fail_times: int) -> None:
        super().__init__()
        self._fail_times = fail_times

    async def upsert(self, *, document_id, semantic_identifier, text, metadata):
        if self._fail_times > 0:
            self._fail_times -= 1
            raise ConnectionError("onyx unreachable")
        return await super().upsert(
            document_id=document_id, semantic_identifier=semantic_identifier, text=text, metadata=metadata
        )


@pytest.mark.asyncio
async def test_failed_record_does_not_advance_checkpoint_and_is_retried():
    index = FlakyDocumentIndex(fail_times=1)
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples)
    records = [leave_application()]

    first = await engine.sync_all("acme", records)
    assert first.failed[0].name == "LA-1"
    assert first.created == 0
    assert index.documents == {}

    second = await engine.sync_all("acme", records)
    assert second.failed == []
    assert second.created == 1
    assert len(index.documents) == 1


@pytest.mark.asyncio
async def test_one_failed_record_does_not_block_the_rest_of_the_batch():
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples)

    bad = FrappeRecord(doctype="Employee", name="EMP-bad", tenant_id="acme", fields={})  # missing user_id
    good = leave_application()

    report = await engine.sync_all("acme", [bad, good])

    assert len(report.failed) == 1
    assert report.failed[0].name == "EMP-bad"
    assert report.created == 1


@pytest.mark.asyncio
async def test_record_with_mismatched_tenant_is_rejected_not_synced():
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples)

    wrong_tenant_record = leave_application(tenant_id="globex")
    report = await engine.sync_all("acme", [wrong_tenant_record])

    assert report.created == 0
    assert len(report.failed) == 1
    assert index.documents == {}


# --- reconciliation report -------------------------------------------------


@pytest.mark.asyncio
async def test_report_totals_and_timestamps():
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples)

    report = await engine.sync_all("acme", [employee(), leave_application(), salary_slip()])

    assert report.tenant_id == "acme"
    assert report.total_processed == 3
    assert report.started_at is not None
    assert report.finished_at is not None
    assert report.finished_at >= report.started_at
