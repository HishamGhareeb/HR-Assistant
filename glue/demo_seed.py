"""Deterministic synthetic demo organization and guided pilot setup (HIS-24).

Produces a working pilot without any real employee data: a small, fixed
set of `glue.hr_source_sync.HrSourceRecord` rows for a fictional demo tenant,
scripted personas with known credentials, and a curated list of sample
questions that exercise the pipeline's classification tiers (public,
internal, manager-only, HR-only) and its safe "I don't have information on
that" fallback.

This module contains no I/O -- it only builds `HrSourceRecord`s and hands
them to whatever `glue.hr_source_sync.SyncEngine` the caller already has
(real Onyx/OpenFGA in production, fakes in tests). It deliberately does
not invent a parallel ingestion path: seeding a demo organization is just
running the same sync every other RAL HRMS record goes through, per
`docs/hr_source_sync.md`, with synthetic input instead of a real RAL HRMS
source.

See `scripts/seed_demo_org.py` for the guided, runnable setup path and
`docs/DEMO_ORGANIZATION.md` for what it produces.
"""
from __future__ import annotations

from dataclasses import dataclass

from .hr_source_sync import HrSourceRecord, ReconciliationReport, SyncEngine

DEMO_TENANT_ID = "demo-org"


@dataclass(frozen=True)
class DemoPersona:
    """One scripted demo user. ``role_description`` is documentation for
    whoever is running the pilot, not an authorization construct -- actual
    access is entirely determined by the OpenFGA tuples the seeded records
    produce (owner / department-manager / hr_admin), same as any other
    tenant."""

    user_id: str
    display_name: str
    department: str
    role_description: str


DEMO_PERSONAS: tuple[DemoPersona, ...] = (
    DemoPersona(
        user_id="priya",
        display_name="Priya Nair",
        department="engineering",
        role_description="Employee -- reports to Farah. Can see her own records and public policies.",
    ),
    DemoPersona(
        user_id="farah",
        display_name="Farah Al Zayani",
        department="engineering",
        role_description=(
            "Engineering manager -- sees her department's employee/leave/performance "
            "records via 'manager from department', but never salary data."
        ),
    ),
    DemoPersona(
        user_id="hr-demo",
        display_name="Demo HR Admin",
        department="people-ops",
        role_description=(
            "HR admin/reviewer -- full visibility across the demo tenant's records, "
            "and authorized for the suggestion review inbox, admin controls, and "
            "answer-feedback quality dashboard."
        ),
    ),
)


def demo_hr_admin_user_ids() -> tuple[str, ...]:
    """Passed as ``SyncConfig.hr_admin_user_ids`` so seeded leave/appraisal/
    salary records get an ``hr_admin`` OpenFGA tuple for the HR persona."""
    return ("hr-demo",)


def _demo_reviewer_map() -> dict[str, list[str]]:
    return {DEMO_TENANT_ID: ["hr-demo"]}


def demo_review_authorizer_map() -> dict[str, list[str]]:
    """Shape for ``HR_REVIEWERS_JSON`` (suggestion review inbox)."""
    return _demo_reviewer_map()


def demo_admin_authorizer_map() -> dict[str, list[str]]:
    """Shape for ``HR_ADMINS_JSON`` (admin controls)."""
    return _demo_reviewer_map()


def demo_feedback_authorizer_map() -> dict[str, list[str]]:
    """Shape for ``HR_FEEDBACK_REVIEWERS_JSON`` (answer feedback/quality)."""
    return _demo_reviewer_map()


def build_demo_records() -> tuple[HrSourceRecord, ...]:
    """The full synthetic dataset, covering every doctype
    ``glue.hr_source_sync`` maps and every classification tier: PUBLIC (HR
    Policy), INTERNAL (Employee, Leave Application), MANAGER_ONLY
    (Appraisal), HR_ONLY (Salary Slip)."""

    return (
        HrSourceRecord(
            doctype="Employee",
            name="EMP-farah",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "user_id": "farah",
                "department": "engineering",
                "employee_name": "Farah Al Zayani",
            },
        ),
        HrSourceRecord(
            doctype="Employee",
            name="EMP-priya",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "user_id": "priya",
                "department": "engineering",
                "employee_name": "Priya Nair",
                "reports_to": "farah",
            },
        ),
        HrSourceRecord(
            doctype="Leave Application",
            name="LA-priya-1",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "employee_user_id": "priya",
                "department": "engineering",
                "leave_type": "Annual Leave",
                "status": "Approved",
            },
        ),
        HrSourceRecord(
            doctype="Appraisal",
            name="APP-priya-2026-h1",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "employee_user_id": "priya",
                "department": "engineering",
                "summary": (
                    "Priya exceeded expectations in H1 2026, with strong delivery on "
                    "the payroll integration project and consistently positive peer feedback."
                ),
            },
        ),
        HrSourceRecord(
            doctype="Salary Slip",
            name="SAL-priya-2026-07",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "employee_user_id": "priya",
                "period": "July 2026",
            },
        ),
        HrSourceRecord(
            doctype="HR Policy",
            name="POL-annual-leave",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "title": "Annual Leave Policy",
                "body": (
                    "Employees accrue 30 days of annual leave per year, consistent with "
                    "Bahrain's Labour Law. Leave requests must be submitted at least 5 "
                    "working days in advance through the HR portal."
                ),
            },
        ),
        HrSourceRecord(
            doctype="HR Policy",
            name="POL-remote-work",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "title": "Remote Work Policy",
                "body": (
                    "Employees may work remotely up to 2 days per week with their "
                    "manager's approval. Core collaboration hours are 10am-3pm Bahrain time."
                ),
            },
        ),
        HrSourceRecord(
            doctype="HR Policy",
            name="POL-public-holidays",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "title": "Public Holiday Calendar",
                "body": (
                    "The company observes every official Bahrain public holiday as "
                    "published annually by the Ministry of Labour."
                ),
            },
        ),
    )


@dataclass(frozen=True)
class DemoSampleQuestion:
    """One scripted question for a guided pilot walkthrough.
    ``expected_outcome`` is a ``glue.pipeline.PipelineResult.model_outcome``
    value -- ``"answered"`` or ``"no_info"`` for every entry here, since the
    demo dataset never triggers a blocked/error outcome by design."""

    persona_user_id: str
    question: str
    expected_outcome: str
    note: str


DEMO_SAMPLE_QUESTIONS: tuple[DemoSampleQuestion, ...] = (
    DemoSampleQuestion(
        persona_user_id="priya",
        question="How many days of annual leave do employees get per year?",
        expected_outcome="answered",
        note="Public policy -- visible to every authenticated demo user.",
    ),
    DemoSampleQuestion(
        persona_user_id="priya",
        question="What is the remote work policy?",
        expected_outcome="answered",
        note="Public policy.",
    ),
    DemoSampleQuestion(
        persona_user_id="priya",
        question="What did my last performance review say?",
        expected_outcome="answered",
        note="Priya is the record's owner, so she can see her own MANAGER_ONLY appraisal.",
    ),
    DemoSampleQuestion(
        persona_user_id="farah",
        question="What is Priya's salary?",
        expected_outcome="no_info",
        note=(
            "Authorization boundary demo, not a bug: salary_record has no "
            "'manager from department' relation in openfga/model.fga by design, "
            "so even Priya's own manager cannot see it."
        ),
    ),
    DemoSampleQuestion(
        persona_user_id="hr-demo",
        question="What is Priya's salary?",
        expected_outcome="answered",
        note="HR admin has hr_admin viewer access to every seeded record.",
    ),
    DemoSampleQuestion(
        persona_user_id="priya",
        question="Do we offer unlimited sabbaticals?",
        expected_outcome="no_info",
        note=(
            "Not covered by the seeded policies -- demonstrates the safe "
            "\"I don't have information on that\" fallback, and gets logged as an "
            "UnansweredQuestion for the HR quality dashboard (HIS-23)."
        ),
    ),
)


async def seed_demo_organization(sync_engine: SyncEngine) -> ReconciliationReport:
    """Runs the full synthetic dataset through the given sync engine.
    Idempotent: re-running against the same engine/checkpoint store reports
    the records as unchanged rather than re-creating them."""

    return await sync_engine.sync_all(DEMO_TENANT_ID, list(build_demo_records()))
