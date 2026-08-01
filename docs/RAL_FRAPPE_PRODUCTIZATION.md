# RAL Frappe Productization Plan

This track turns Frappe HR from an upstream HR operations system into one backend component inside a RAL Technologies commercial HRMS product.

RAL Technologies is the software vendor. The customer company is the tenant/employer. Tenant HR data belongs to the customer tenant and must remain isolated.

## Target position

```text
Customer employees, managers, HR admins, and payroll officers
        ↓
RAL product UI and APIs
        ↓
RAL AI, compliance, payroll, tenancy, billing, and audit layer
        ↓
Frappe HR operational records and workflows
```

Frappe is the engine room. RAL is the product.

## Implementation levels

### Level 1 — RAL-branded Frappe HR

- RAL login, product name, colors, support links, email templates, and print formats.
- RAL roles and workspaces.
- RAL onboarding defaults.
- RAL-branded HR documents and reports.

### Level 2 — RAL product layer on Frappe

- Dedicated `ral_hrms` Frappe app.
- RAL DocTypes for tenant provisioning, AI suggestions, compliance citations, WPS exports, payroll traces, feature entitlements, and usage metering.
- Frappe hooks that sync HR records into the HR Assistant retrieval and authorization systems.
- OpenFGA role synchronization from tenant-scoped Frappe roles.
- Deterministic Bahrain-first country-law packs.

### Level 3 — Frappe as hidden backend

- Customer-facing RAL employee, manager, HR admin, payroll, and tenant admin portals.
- Frappe Desk limited to internal operators or advanced system administrators.
- RAL APIs become the stable product contract.

## First productization slice

The first implementation slice is a scaffold and contract, not a full Frappe bench app:

- `glue.frappe_productization` defines the canonical RAL productization metadata.
- `integrations/frappe/ral_hrms` contains the planned Frappe app structure.
- Tests enforce that RAL roles, DocTypes, and workspaces stay branded, tenant-scoped, and deterministic.

## Frappe customization strategy

Use Frappe's intended extension mechanisms:

- custom app;
- hooks;
- fixtures;
- custom fields;
- roles and permissions;
- workspaces;
- print formats;
- workflow fixtures;
- DocType event hooks;
- whitelisted API methods where needed.

Avoid editing Frappe/Frappe HR core unless a hook/app extension cannot solve the problem.

## RAL-owned role model

- RAL Tenant Admin
- RAL HR Admin
- RAL Payroll Officer
- RAL Manager
- RAL Employee

These roles must be tenant-scoped and mapped into OpenFGA relations. Static JSON role maps in the current FastAPI app are transitional and should be replaced by durable tenant provisioning.

## RAL-owned product entities

The planned `ral_hrms` extension owns these product concepts:

- RAL Tenant
- RAL Tenant Settings
- RAL Feature Entitlement
- RAL Usage Meter
- RAL AI Suggestion
- RAL AI Suggestion Decision
- RAL Document Access Classification
- RAL Policy Ingestion Job
- RAL Country Law Pack
- RAL Payroll Rule Version
- RAL Bahrain WPS Export
- RAL Payroll Calculation Trace
- RAL Compliance Citation
- RAL Audit Event
- RAL Integration Sync Run

Frappe HR remains the operational source for HR records. RAL product entities provide tenancy, AI, compliance, audit, payroll localization, billing, and product control.

## Bahrain-first country-law pack

Bahrain is the first country pack. It must include:

- GOSI/SIO contribution parameters;
- Bahraini versus expatriate payroll treatment;
- end-of-service benefit logic;
- WPS export schema and validation;
- leave and public-holiday statutory rules;
- official-source citations and effective dates.

No Bahrain statutory number should be implemented until verified from official sources. The LLM may explain a deterministic calculation result, but it must not calculate payroll/compliance outcomes itself.

## Frappe-to-AI sync hooks

The Frappe app should eventually emit tenant-scoped sync events for:

- Employee create/update;
- Leave Application submit/cancel;
- Appraisal submit;
- Salary Slip submit;
- HR Policy upload/update.

These events should update Onyx documents and OpenFGA tuples through the HR Assistant API. They must be queued, idempotent, retryable, and audited.

## Non-negotiable boundaries

- Tenant ID comes from trusted tenant provisioning and signed identity context.
- `public` means tenant-public only.
- OpenFGA authorization remains required before retrieval and before LLM context construction.
- AI suggestion approval records a human decision only.
- Frappe HR mutations require separate explicit workflows.
- Payroll/compliance logic is deterministic and version-tested.
- Audit/tracing stays metadata-only.

## Recommended next PRs

1. Convert the scaffold into a generated fixture manifest for roles, workspaces, and custom fields.
2. Add durable tenant provisioning and role sync from Frappe/RAL tenants into OpenFGA.
3. Build the Bahrain country-law rule-pack schema with official-source citation fields.
4. Add deterministic WPS export payload contracts and tests.
5. Build the first RAL frontend API endpoints that hide raw Frappe surfaces from normal users.
