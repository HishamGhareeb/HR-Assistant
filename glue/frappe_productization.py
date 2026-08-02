"""RAL-owned Frappe productization contract.

This module describes the Frappe extension layer RAL Technologies owns around
the HR Assistant product. It is intentionally deterministic metadata: builders
can generate Frappe fixtures, docs, and implementation tickets from the same
source of truth without asking an LLM to reinterpret product boundaries.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductSurface(StrEnum):
    """Where a product concept is expected to live."""

    FRAPPE_EXTENSION = "frappe_extension"
    HR_ASSISTANT_CORE = "hr_assistant_core"
    RAL_FRONTEND = "ral_frontend"
    EXTERNAL_SERVICE = "external_service"


class Ownership(StrEnum):
    """Who owns the implementation and commercial positioning."""

    RAL = "ral_technologies"
    CUSTOMER_TENANT = "customer_tenant"
    FRAPPE_UPSTREAM = "frappe_upstream"


class RalFrappeApp(BaseModel):
    """Installable Frappe app metadata for the RAL product layer."""

    model_config = ConfigDict(frozen=True)

    app_name: str = "ral_hrms"
    app_title: str = "RAL HRMS"
    app_publisher: str = "RAL Technologies"
    app_description: str = (
        "RAL-owned HRMS, AI assistant, compliance, and payroll localization "
        "layer built on a Frappe HR operations foundation."
    )
    app_email: str = "info@raltech.dev"
    app_url: str = "https://raltech.dev"
    app_license: str = "Proprietary RAL product layer; verify compatibility with installed Frappe apps"


class RalRole(BaseModel):
    """Tenant-scoped role that RAL provisions into Frappe/OpenFGA."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    openfga_relation: str | None = None
    tenant_scoped: bool = True


class RalDocType(BaseModel):
    """RAL-owned DocType or product entity planned for the Frappe extension."""

    model_config = ConfigDict(frozen=True)

    name: str
    module: str
    purpose: str
    surface: ProductSurface = ProductSurface.FRAPPE_EXTENSION
    owner: Ownership = Ownership.RAL
    tenant_required: bool = True
    source_of_truth: str
    may_mutate_frappe_hr: bool = False
    notes: tuple[str, ...] = Field(default_factory=tuple)


class RalWorkspace(BaseModel):
    """Frappe Desk workspace RAL should provide for operators/admins."""

    model_config = ConfigDict(frozen=True)

    name: str
    audience: str
    purpose: str
    required_roles: tuple[str, ...]


class RalCountryLawPack(BaseModel):
    """Country-law pack contract for deterministic payroll/compliance logic."""

    model_config = ConfigDict(frozen=True)

    country_code: str
    country_name: str
    first_supported: bool
    rules_are_deterministic: bool = True
    official_source_required: bool = True
    llm_may_compute: bool = False
    planned_rule_families: tuple[str, ...]


RAL_FRAPPE_APP = RalFrappeApp()

RAL_ROLES: tuple[RalRole, ...] = (
    RalRole(
        name="RAL Tenant Admin",
        description="Customer-side tenant administrator who manages tenant settings and user provisioning.",
        openfga_relation="system_admin",
    ),
    RalRole(
        name="RAL HR Admin",
        description="Customer HR administrator with access to HR-only records, review inboxes, and compliance workflows.",
        openfga_relation="hr_admin",
    ),
    RalRole(
        name="RAL Payroll Officer",
        description="Customer payroll operator for deterministic payroll runs, WPS exports, and payroll traces.",
        openfga_relation="hr_admin",
    ),
    RalRole(
        name="RAL Manager",
        description="People manager with team-scoped approvals, manager-only documents, and limited risk signals.",
        openfga_relation="manager",
    ),
    RalRole(
        name="RAL Employee",
        description="Employee self-service user with tenant-public/internal access only.",
        openfga_relation="employee",
    ),
)

RAL_DOCTYPES: tuple[RalDocType, ...] = (
    RalDocType(
        name="RAL Tenant",
        module="RAL Platform",
        purpose="Commercial customer/tenant container for isolation, provisioning, billing, and regional setup.",
        source_of_truth="RAL control plane",
    ),
    RalDocType(
        name="RAL Tenant Settings",
        module="RAL Platform",
        purpose="Tenant-specific HRMS configuration derived from onboarding and subscription state.",
        source_of_truth="RAL control plane",
    ),
    RalDocType(
        name="RAL Feature Entitlement",
        module="RAL Platform",
        purpose="Feature flags and subscription entitlements without relying on a third-party toggle service for MVP.",
        source_of_truth="RAL billing/provisioning layer",
    ),
    RalDocType(
        name="RAL Usage Meter",
        module="RAL Platform",
        purpose="Tenant-scoped AI/API usage metering for commercial plans and margin control.",
        source_of_truth="RAL metering layer",
    ),
    RalDocType(
        name="RAL AI Suggestion",
        module="RAL AI",
        purpose="Reviewable AI-generated HR suggestion linked to citations and tenant context.",
        surface=ProductSurface.HR_ASSISTANT_CORE,
        source_of_truth="HR Assistant suggestion service",
    ),
    RalDocType(
        name="RAL AI Suggestion Decision",
        module="RAL AI",
        purpose="Append-only human review decision for an AI suggestion.",
        surface=ProductSurface.HR_ASSISTANT_CORE,
        source_of_truth="HR Assistant suggestion service",
    ),
    RalDocType(
        name="RAL Document Access Classification",
        module="RAL AI",
        purpose="Tenant-scoped document classification mapping for pre-retrieval authorization.",
        source_of_truth="RAL provisioning/OpenFGA sync",
    ),
    RalDocType(
        name="RAL Policy Ingestion Job",
        module="RAL AI",
        purpose="Track tenant policy/document ingestion into retrieval and authorization systems.",
        source_of_truth="RAL ingestion pipeline",
    ),
    RalDocType(
        name="RAL Country Law Pack",
        module="RAL Compliance",
        purpose="Versioned country-law rule-pack container with official-source citations.",
        source_of_truth="RAL compliance engineering",
    ),
    RalDocType(
        name="RAL Payroll Rule Version",
        module="RAL Compliance",
        purpose="Effective-date payroll/compliance parameter set used by deterministic calculators.",
        source_of_truth="RAL compliance engineering",
    ),
    RalDocType(
        name="RAL Bahrain WPS Export",
        module="RAL Payroll",
        purpose="Tenant payroll export batch for Bahrain Wages Protection System workflows.",
        source_of_truth="RAL deterministic payroll engine",
    ),
    RalDocType(
        name="RAL Payroll Calculation Trace",
        module="RAL Payroll",
        purpose="Explainable, structured calculation trace produced by deterministic payroll logic.",
        source_of_truth="RAL deterministic payroll engine",
    ),
    RalDocType(
        name="RAL Compliance Citation",
        module="RAL Compliance",
        purpose="Official-source citation attached to legal/payroll/compliance rule versions.",
        source_of_truth="RAL compliance verification workflow",
    ),
    RalDocType(
        name="RAL Audit Event",
        module="RAL Security",
        purpose="Metadata-only audit event or external audit pointer for tenant actions and AI behavior.",
        source_of_truth="RAL audit layer",
        notes=("Must not contain raw prompts, answers, chunks, employee identifiers, or sensitive payloads.",),
    ),
    RalDocType(
        name="RAL Integration Sync Run",
        module="RAL Integrations",
        purpose="Tenant-scoped sync status for Frappe, Onyx, OpenFGA, and future source systems.",
        source_of_truth="RAL sync orchestration",
    ),
)

RAL_WORKSPACES: tuple[RalWorkspace, ...] = (
    RalWorkspace(
        name="RAL HR Command Center",
        audience="HR administrators",
        purpose="Operational home for HR actions, suggestions, policy status, and exceptions.",
        required_roles=("RAL HR Admin",),
    ),
    RalWorkspace(
        name="RAL Payroll Bahrain",
        audience="Payroll officers",
        purpose="Bahrain payroll runs, deterministic traces, and WPS export status.",
        required_roles=("RAL Payroll Officer", "RAL HR Admin"),
    ),
    RalWorkspace(
        name="RAL AI Review Inbox",
        audience="HR reviewers",
        purpose="Human-in-the-loop AI suggestions with citations and safe decision states.",
        required_roles=("RAL HR Admin",),
    ),
    RalWorkspace(
        name="RAL Compliance Center",
        audience="HR and compliance administrators",
        purpose="Country-law packs, official citations, rule versions, and audit exports.",
        required_roles=("RAL HR Admin", "RAL Payroll Officer"),
    ),
    RalWorkspace(
        name="RAL Tenant Admin",
        audience="Tenant administrators",
        purpose="Tenant setup, roles, entitlements, integrations, and access sync.",
        required_roles=("RAL Tenant Admin",),
    ),
)

BAHRAIN_LAW_PACK = RalCountryLawPack(
    country_code="BH",
    country_name="Bahrain",
    first_supported=True,
    planned_rule_families=(
        "GOSI/SIO contribution parameters",
        "Bahraini vs expatriate payroll treatment",
        "End-of-service benefit calculations",
        "WPS export schema and validation",
        "Leave/public-holiday statutory rules",
        "Official-source citations and effective dates",
    ),
)


def frappe_role_fixtures() -> list[dict[str, Any]]:
    """Build deterministic Frappe Role fixture records for the RAL app."""

    return [
        {
            "doctype": "Role",
            "name": role.name,
            "role_name": role.name,
            "desk_access": 1,
            "disabled": 0,
            "is_custom": 1,
            "two_factor_auth": 0,
            "description": role.description,
        }
        for role in RAL_ROLES
    ]


def frappe_workspace_fixtures() -> list[dict[str, Any]]:
    """Build deterministic Frappe Workspace fixture records for the RAL app."""

    fixtures: list[dict[str, Any]] = []
    for index, workspace in enumerate(RAL_WORKSPACES, start=1):
        fixtures.append(
            {
                "doctype": "Workspace",
                "name": workspace.name,
                "label": workspace.name,
                "title": workspace.name,
                "module": "RAL Platform",
                "public": 0,
                "is_standard": 1,
                "sequence_id": index,
                "for_user": "",
                "icon": "organization",
                "indicator_color": "blue",
                "content": json.dumps(
                    [
                        {
                            "id": f"{workspace.name.lower().replace(' ', '-')}-intro",
                            "type": "header",
                            "data": {"text": workspace.purpose, "col": 12},
                        }
                    ],
                    separators=(",", ":"),
                ),
                "roles": [
                    {
                        "doctype": "Has Role",
                        "role": role_name,
                        "parent": workspace.name,
                        "parenttype": "Workspace",
                        "parentfield": "roles",
                    }
                    for role_name in workspace.required_roles
                ],
            }
        )

    return fixtures


def validate_ral_productization_contract() -> list[str]:
    """Return contract violations that would weaken RAL product ownership."""

    violations: list[str] = []

    role_names = {role.name for role in RAL_ROLES}
    if len(role_names) != len(RAL_ROLES):
        violations.append("RAL roles must have unique names.")

    for role in RAL_ROLES:
        if not role.name.startswith("RAL "):
            violations.append(f"Role {role.name!r} must be RAL-branded.")
        if not role.tenant_scoped:
            violations.append(f"Role {role.name!r} must remain tenant-scoped.")

    doctype_names = {doctype.name for doctype in RAL_DOCTYPES}
    if len(doctype_names) != len(RAL_DOCTYPES):
        violations.append("RAL DocTypes must have unique names.")

    for doctype in RAL_DOCTYPES:
        if not doctype.name.startswith("RAL "):
            violations.append(f"DocType {doctype.name!r} must be RAL-branded.")
        if doctype.owner != Ownership.RAL:
            violations.append(f"DocType {doctype.name!r} must be owned by RAL.")
        if not doctype.tenant_required:
            violations.append(f"DocType {doctype.name!r} must carry tenant context.")
        if doctype.may_mutate_frappe_hr:
            violations.append(
                f"DocType {doctype.name!r} may not silently mutate Frappe HR records."
            )

    for workspace in RAL_WORKSPACES:
        if not workspace.name.startswith("RAL "):
            violations.append(f"Workspace {workspace.name!r} must be RAL-branded.")
        missing_roles = set(workspace.required_roles) - role_names
        if missing_roles:
            violations.append(
                f"Workspace {workspace.name!r} references unknown roles: {sorted(missing_roles)}."
            )

    if BAHRAIN_LAW_PACK.llm_may_compute:
        violations.append("Country-law packs must never allow LLM-computed payroll/compliance results.")
    if not BAHRAIN_LAW_PACK.official_source_required:
        violations.append("Country-law packs must require official-source verification.")

    return violations
