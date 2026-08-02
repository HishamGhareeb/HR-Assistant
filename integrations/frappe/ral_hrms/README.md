# RAL HRMS Frappe Extension Scaffold

`ral_hrms` is the planned RAL Technologies Frappe extension app for turning a Frappe HR installation into a RAL-owned commercial HRMS product layer.

This scaffold is intentionally kept inside the HR Assistant repository until a dedicated Frappe bench/package repository is created. It defines the app boundary, naming, hooks, fixtures, and product surfaces that must be preserved when the real Frappe app is generated.

## Product boundary

Frappe HR is the HR operations engine. RAL owns:

- customer onboarding and tenant provisioning;
- RAL-branded workspaces, roles, dashboards, and print formats;
- Bahrain-first country-law and payroll rule packs;
- AI suggestion review and policy-ingestion workflows;
- OpenFGA role synchronization and document classification;
- WPS exports, compliance citations, and calculation traces;
- billing, feature entitlements, usage metering, support, and deployment.

Tenant data belongs to the customer tenant/employer. RAL provides and operates the product.

## Non-negotiable rules

- Do not modify Frappe/Frappe HR core unless a hook or app extension cannot solve the problem.
- All RAL-owned DocTypes and roles must be clearly RAL-branded.
- Every RAL-owned object must carry tenant context.
- `public` access always means tenant-public, never global.
- AI suggestion approval must not silently mutate Frappe HR records.
- Payroll and compliance calculations must be deterministic and official-source verified.
- The LLM may explain deterministic outputs; it must not calculate statutory results.

## Real Frappe app target

When moved into a Frappe bench, this scaffold should become an installable app:

```text
apps/ral_hrms
├── pyproject.toml
├── README.md
└── ral_hrms
    ├── hooks.py
    ├── modules.txt
    ├── patches.txt
    ├── config
    ├── fixtures
    ├── public
    └── ral_hrms
```

The canonical metadata source in this repository is `glue.frappe_productization`.
