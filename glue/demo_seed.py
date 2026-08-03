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
class DemoEmployee:
    user_id: str
    display_name: str
    department: str
    title: str
    reports_to: str | None = None
    monthly_salary_bhd: int = 900
    employment_type: str = "Full-time"
    nationality_category: str = "non_bahraini_private_sector"


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


DEMO_COMPANY_NAME = "Pearl Horizon Trading W.L.L."


DEMO_EMPLOYEES: tuple[DemoEmployee, ...] = (
    DemoEmployee("layla", "Layla Al Haddad", "leadership", "Chief Executive Officer", monthly_salary_bhd=3200, nationality_category="bahraini_private_sector"),
    DemoEmployee("omar", "Omar Mahmood", "leadership", "Chief Operating Officer", reports_to="layla", monthly_salary_bhd=2700, nationality_category="bahraini_private_sector"),
    DemoEmployee("farah", "Farah Al Zayani", "engineering", "Engineering Manager", reports_to="omar", monthly_salary_bhd=2400, nationality_category="bahraini_private_sector"),
    DemoEmployee("priya", "Priya Nair", "engineering", "Senior Software Engineer", reports_to="farah", monthly_salary_bhd=1450),
    DemoEmployee("yusuf", "Yusuf Khan", "engineering", "Backend Engineer", reports_to="farah", monthly_salary_bhd=1250),
    DemoEmployee("noura", "Noura Al Khalifa", "engineering", "QA Automation Engineer", reports_to="farah", monthly_salary_bhd=1150, nationality_category="bahraini_private_sector"),
    DemoEmployee("daniel", "Daniel Mensah", "engineering", "DevOps Engineer", reports_to="farah", monthly_salary_bhd=1350),
    DemoEmployee("mariam", "Mariam Al Ansari", "product", "Product Manager", reports_to="omar", monthly_salary_bhd=1800, nationality_category="bahraini_private_sector"),
    DemoEmployee("ahmed", "Ahmed Saleh", "product", "Product Designer", reports_to="mariam", monthly_salary_bhd=1200, nationality_category="bahraini_private_sector"),
    DemoEmployee("sara", "Sara Haddad", "product", "Business Analyst", reports_to="mariam", monthly_salary_bhd=1100),
    DemoEmployee("khalid", "Khalid Al Noor", "sales", "Sales Manager", reports_to="omar", monthly_salary_bhd=1900, nationality_category="bahraini_private_sector"),
    DemoEmployee("fatima", "Fatima Jassim", "sales", "Account Executive", reports_to="khalid", monthly_salary_bhd=1000, nationality_category="bahraini_private_sector"),
    DemoEmployee("raj", "Raj Patel", "sales", "Account Executive", reports_to="khalid", monthly_salary_bhd=950),
    DemoEmployee("lina", "Lina Mansour", "sales", "Sales Development Representative", reports_to="khalid", monthly_salary_bhd=850),
    DemoEmployee("hassan", "Hassan Abbas", "customer-success", "Customer Success Manager", reports_to="omar", monthly_salary_bhd=1700, nationality_category="bahraini_private_sector"),
    DemoEmployee("amina", "Amina Noor", "customer-success", "Implementation Specialist", reports_to="hassan", monthly_salary_bhd=950),
    DemoEmployee("joel", "Joel Fernandes", "customer-success", "Support Specialist", reports_to="hassan", monthly_salary_bhd=780),
    DemoEmployee("reem", "Reem Al Saffar", "finance", "Finance Manager", reports_to="omar", monthly_salary_bhd=1750, nationality_category="bahraini_private_sector"),
    DemoEmployee("zainab", "Zainab Ali", "finance", "Payroll Specialist", reports_to="reem", monthly_salary_bhd=1050, nationality_category="bahraini_private_sector"),
    DemoEmployee("miguel", "Miguel Santos", "finance", "Accounts Officer", reports_to="reem", monthly_salary_bhd=900),
    DemoEmployee("hr-demo", "Demo HR Admin", "people-ops", "People Operations Lead", reports_to="omar", monthly_salary_bhd=1650, nationality_category="bahraini_private_sector"),
    DemoEmployee("salma", "Salma Yousif", "people-ops", "Recruiter", reports_to="hr-demo", monthly_salary_bhd=950, nationality_category="bahraini_private_sector"),
    DemoEmployee("ravi", "Ravi Menon", "people-ops", "HR Coordinator", reports_to="hr-demo", monthly_salary_bhd=820),
    DemoEmployee("tariq", "Tariq Al Rumaihi", "operations", "Operations Supervisor", reports_to="omar", monthly_salary_bhd=1200, nationality_category="bahraini_private_sector"),
    DemoEmployee("mei", "Mei Chen", "operations", "Office Administrator", reports_to="tariq", monthly_salary_bhd=760),
)


DEMO_PERSONAS: tuple[DemoPersona, ...] = (
    DemoPersona(
        user_id="priya",
        display_name="Priya Nair",
        department="engineering",
        role_description="Employee -- reports to Farah. Can see her own records and public policies.",
    ),
    DemoPersona(
        user_id="noura",
        display_name="Noura Al Khalifa",
        department="engineering",
        role_description="Employee -- Bahraini team member with leave and appraisal records.",
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
        user_id="reem",
        display_name="Reem Al Saffar",
        department="finance",
        role_description="Finance manager -- sees finance team HR records, but not salary records outside HR permissions.",
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
    """The full synthetic dataset, covering every record type
    ``glue.hr_source_sync`` maps and every classification tier: PUBLIC (HR
    Policy), INTERNAL (Employee, Leave Application), MANAGER_ONLY
    (Appraisal), HR_ONLY (Salary Slip)."""

    departments = sorted({employee.department for employee in DEMO_EMPLOYEES})
    records: list[HrSourceRecord] = [
        HrSourceRecord(
            doctype="Department",
            name=department,
            tenant_id=DEMO_TENANT_ID,
            fields={"department_name": department.replace("-", " ").title()},
        )
        for department in departments
    ]

    records.extend(
        HrSourceRecord(
            doctype="Employee",
            name=f"EMP-{employee.user_id}",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "user_id": employee.user_id,
                "department": employee.department,
                "employee_name": employee.display_name,
                "title": employee.title,
                "reports_to": employee.reports_to or "",
                "employment_type": employee.employment_type,
                "nationality_category": employee.nationality_category,
            },
        )
        for employee in DEMO_EMPLOYEES
    )

    leave_status_cycle = ("Approved", "Pending", "Approved", "Rejected")
    records.extend(
        HrSourceRecord(
            doctype="Leave Application",
            name=f"LA-{employee.user_id}-2026-{index + 1:02d}",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "employee_user_id": employee.user_id,
                "department": employee.department,
                "leave_type": "Annual Leave" if index % 5 else "Sick Leave",
                "status": leave_status_cycle[index % len(leave_status_cycle)],
            },
        )
        for index, employee in enumerate(DEMO_EMPLOYEES)
        if employee.user_id != "layla"
    )

    records.extend(
        HrSourceRecord(
            doctype="Appraisal",
            name=f"APP-{employee.user_id}-2026-h1",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "employee_user_id": employee.user_id,
                "department": employee.department,
                "summary": (
                    f"{employee.display_name}, {employee.title}, had a strong H1 2026 review. "
                    f"Key themes: reliable delivery, cross-team communication, and one development "
                    f"goal agreed with {employee.reports_to or 'leadership'} for the next cycle."
                ),
            },
        )
        for employee in DEMO_EMPLOYEES
        if employee.user_id not in {"layla", "omar"}
    )

    records.extend(
        HrSourceRecord(
            doctype="Salary Slip",
            name=f"SAL-{employee.user_id}-2026-07",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "employee_user_id": employee.user_id,
                "period": "July 2026",
                "monthly_salary_bhd": str(employee.monthly_salary_bhd),
                "worker_category": employee.nationality_category,
            },
        )
        for employee in DEMO_EMPLOYEES
    )

    records.extend(
        (
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
        HrSourceRecord(
            doctype="HR Policy",
            name="POL-bahrain-payroll",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "title": "Bahrain Payroll Compliance Policy",
                "body": (
                    "Payroll is processed monthly in Bahraini dinars. HR validates SIO contribution "
                    "coverage, WPS file readiness, and non-Bahraini end-of-service benefit treatment "
                    "before releasing payroll. Unsupported statutory combinations are escalated for "
                    "human payroll review rather than guessed."
                ),
            },
        ),
        HrSourceRecord(
            doctype="HR Policy",
            name="POL-data-access",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "title": "HR Data Access Policy",
                "body": (
                    "Employees may view their own HR records and tenant-wide policies. Managers may "
                    "view approved team HR and performance records needed for supervision, but salary "
                    "records remain HR-only."
                ),
            },
        ),
        HrSourceRecord(
            doctype="HR Policy",
            name="POL-probation",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "title": "Probation and Review Policy",
                "body": (
                    "New hires complete a structured probation review with their manager. People Ops "
                    "tracks review completion, missing documents, and any compliance-sensitive follow-up."
                ),
            },
        ),
        HrSourceRecord(
            doctype="HR Policy",
            name="POL-expense-claims",
            tenant_id=DEMO_TENANT_ID,
            fields={
                "title": "Expense Claims Policy",
                "body": (
                    "Business expenses require receipts and manager approval. Finance reviews claims "
                    "above BHD 250 and escalates unusual patterns to People Ops when they touch payroll."
                ),
            },
        ),
        )
    )

    return tuple(records)


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
