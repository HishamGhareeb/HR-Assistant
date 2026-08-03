"""Tests for the deterministic synthetic demo organization (HIS-24):
dataset shape/coverage, persona/sample-question consistency, and an
end-to-end sync against fake Onyx/OpenFGA adapters.
"""
from __future__ import annotations

import pytest

from glue.demo_seed import (
    DEMO_EMPLOYEES,
    DEMO_PERSONAS,
    DEMO_SAMPLE_QUESTIONS,
    DEMO_TENANT_ID,
    build_demo_records,
    demo_admin_authorizer_map,
    demo_feedback_authorizer_map,
    demo_hr_admin_user_ids,
    demo_review_authorizer_map,
    seed_demo_organization,
)
from glue.domain import DocumentClassification
from glue.hr_source_sync import HrSourceMappingError, SyncConfig, SyncEngine, map_record


class FakeDocumentIndex:
    def __init__(self) -> None:
        self.documents: dict[str, dict] = {}

    async def upsert(self, *, document_id, semantic_identifier, text, metadata):
        already_existed = document_id in self.documents
        self.documents[document_id] = {"semantic_identifier": semantic_identifier, "text": text, "metadata": metadata}
        return already_existed

    async def delete(self, document_id):
        self.documents.pop(document_id, None)


class FakeTupleWriter:
    def __init__(self) -> None:
        self.tuples: set[tuple[str, str, str]] = set()

    async def write_tuples(self, tuples):
        self.tuples.update(tuples)

    async def delete_tuples(self, tuples):
        for t in tuples:
            self.tuples.discard(t)


# --- dataset shape ------------------------------------------------------


def test_every_record_is_scoped_to_the_demo_tenant():
    records = build_demo_records()
    assert records  # non-empty
    assert all(record.tenant_id == DEMO_TENANT_ID for record in records)


def test_demo_company_has_twenty_five_people_and_full_record_coverage():
    records = build_demo_records()
    assert len(DEMO_EMPLOYEES) == 25
    assert sum(1 for record in records if record.doctype == "Employee") == 25
    assert sum(1 for record in records if record.doctype == "Salary Slip") == 25
    assert sum(1 for record in records if record.doctype == "Leave Application") >= 20
    assert sum(1 for record in records if record.doctype == "Appraisal") >= 20
    assert sum(1 for record in records if record.doctype == "HR Policy") >= 7


def test_every_record_maps_without_error():
    """Every seeded record must be mappable by the real hr_source_sync rules
    -- a demo dataset that fails to map is worse than no demo at all."""
    config = SyncConfig(hr_admin_user_ids=demo_hr_admin_user_ids())
    for record in build_demo_records():
        map_record(record, config)  # raises HrSourceMappingError on failure


def test_dataset_covers_every_classification_tier():
    config = SyncConfig(hr_admin_user_ids=demo_hr_admin_user_ids())
    classifications = {
        map_record(record, config).document.classification
        for record in build_demo_records()
        if map_record(record, config).document is not None
    }
    assert classifications == {
        DocumentClassification.PUBLIC,
        DocumentClassification.INTERNAL,
        DocumentClassification.MANAGER_ONLY,
        DocumentClassification.HR_ONLY,
    }


def test_record_names_are_unique():
    records = build_demo_records()
    names = [(r.doctype, r.name) for r in records]
    assert len(names) == len(set(names))


# --- personas / sample questions consistency --------------------------


def test_every_sample_question_persona_is_a_scripted_persona():
    persona_ids = {p.user_id for p in DEMO_PERSONAS}
    assert all(q.persona_user_id in persona_ids for q in DEMO_SAMPLE_QUESTIONS)


def test_sample_questions_only_use_answered_or_no_info_outcomes():
    # The demo dataset is designed to never trigger a blocked/error path --
    # a guided walkthrough should never accidentally hit BLOCKED_RESPONSE.
    assert all(q.expected_outcome in {"answered", "no_info"} for q in DEMO_SAMPLE_QUESTIONS)


def test_authorizer_maps_are_keyed_by_demo_tenant_and_include_hr_persona():
    for build_map in (demo_review_authorizer_map, demo_admin_authorizer_map, demo_feedback_authorizer_map):
        result = build_map()
        assert set(result.keys()) == {DEMO_TENANT_ID}
        assert "hr-demo" in result[DEMO_TENANT_ID]


# --- end-to-end sync ------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_demo_organization_creates_every_record_with_no_failures():
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples, config=SyncConfig(hr_admin_user_ids=demo_hr_admin_user_ids()))

    report = await seed_demo_organization(engine)

    assert report.failed == []
    assert report.created == len(build_demo_records())
    assert report.tenant_id == DEMO_TENANT_ID


@pytest.mark.asyncio
async def test_seed_demo_organization_is_idempotent():
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples, config=SyncConfig(hr_admin_user_ids=demo_hr_admin_user_ids()))

    await seed_demo_organization(engine)
    second = await seed_demo_organization(engine)

    assert second.failed == []
    assert second.created == 0
    assert second.unchanged == len(build_demo_records())


@pytest.mark.asyncio
async def test_seeded_salary_slip_is_not_visible_via_manager_department_tuple():
    """Mirrors DEMO_SAMPLE_QUESTIONS' farah/salary walkthrough point:
    confirms at the tuple level that Priya's manager gets no viewer path
    to her salary_record, only priya (owner) and hr-demo (hr_admin) do."""
    index = FakeDocumentIndex()
    tuples = FakeTupleWriter()
    engine = SyncEngine(index, tuples, config=SyncConfig(hr_admin_user_ids=demo_hr_admin_user_ids()))

    await seed_demo_organization(engine)

    salary_tuples = [t for t in tuples.tuples if t[2].split("__", 1)[-1] == "SAL-priya-2026-07"]
    users_with_access = {t[0] for t in salary_tuples}
    assert users_with_access == {"user:priya", "user:hr-demo"}
    assert "user:farah" not in users_with_access
