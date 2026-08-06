# Product roadmap

## Product promise

A secure HR copilot that answers employee questions from company-approved data,
respects each user's permissions, and surfaces reviewable HR suggestions without
making autonomous changes.

## Release gates

### Gate 1 — Runnable secure core

- Versioned HTTP API and health endpoint
- Real Onyx adapter with a stable document metadata contract
- OpenFGA model deployment and authorization integration tests
- RAL HRMS-to-Onyx/OpenFGA synthetic-data sync
- Authentication and tenant context
- Failure-safe behavior, audit events, and automated tests

### Gate 2 — Usable pilot

- Employee web chat
- HR admin portal and suggestion review inbox
- Policy and employee-data ingestion controls
- Source citations, answer feedback, and escalation
- Docker-based local and hosted deployment
- Seeded demo organization and guided setup

### Gate 3 — Sellable product

- Multi-tenant isolation and customer administration
- Subscription plans, usage metering, billing, and limits
- Bahrain-first payroll support with modular, versioned country-law rule packs
- Branding, onboarding, legal pages, DPA, retention, and deletion workflows
- WhatsApp integration and configurable notifications
- Monitoring, backups, disaster recovery, SLOs, and support runbooks
- Security review, adversarial suite, privacy review, and pilot sign-off

### Gate 4 — Commercial scale

- SSO/SCIM, regional deployment, advanced analytics, and connector marketplace
- Repeatable sales demo, implementation playbook, pricing, and support tiers

## Immediate build sequence

1. Make the core service runnable and testable.
2. Define the canonical retrieved-document and identity/tenant contracts.
3. Complete the Onyx connector against a pinned Onyx version.
4. Build synthetic RAL HRMS ingestion and authorization tuple sync.
5. Add real authentication and strict tenant isolation.
6. Build the smallest end-to-end employee chat and HR review workflow.

## Payroll and country-law direction

Payroll must be designed as a deterministic, jurisdiction-aware capability. Bahrain
is the first required market, but the product should not hard-code Bahrain logic
into the general request path. Country-specific labor and payroll rules should live
in modular, versioned rule packs with effective dates, source/reference metadata,
tests, and audit-safe explanations. Future country changes should be handled by
adding or updating a country-law rule version with minimal changes to core API or
chat code.

LLMs may explain payroll outputs and cite approved sources, but payroll
calculations and legal-rule evaluation must come from deterministic rules rather
than model guesses.
