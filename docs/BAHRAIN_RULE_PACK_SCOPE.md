# Bahrain rule-pack scope decisions

This document records explicit scope decisions for Bahrain payroll/labor-law
logic so unresolved source gaps do not silently become product behavior.

Source inventory: `docs/BAHRAIN_PAYROLL_SOURCES.md`

## Current implementation gate

The current Bahrain deterministic rule-pack gate may include:

- WPS submission/workflow validation based on the WPS User Manual and
  Resolution 68/2019.
- SIO wage-update validation based on the parsed SIO employer wage-reporting
  guides.
- EOSB logic for non-Bahraini private-sector employees, using the human
  payroll/legal interpretation recorded on 2026-08-02 that Decision 109/2023
  Article 9's "half a month's wages" means monthly wage divided by two, not
  daily wage multiplied by 15.

The current gate must not include unsupported Flexi Permit or Law 68/2006
logic.

## Decision 1: Flexi Permit / flexible-worker regulation

Decision: **excluded from current gate scope**.

Reasoning:

- HIS-50 confirmed Flexi Permit / flexible-worker status as a real LMRA permit
  category, but did not locate a founding regulation.
- The research pass checked LMRA Board of Directors Resolutions, Resolutions of
  Other Entities Related to LMRA Duties, Cabinet Resolutions Regarding LMRA
  Fees, and on-site search attempts.
- The only surfaced reference, Resolution 108/2017, was a residency-status
  correction reference, not a reliable founding regulation for rule-pack logic.

Product rule:

- Do not add Flexi Permit calculations, eligibility checks, or special-case
  payroll behavior to the Bahrain rule pack until an official founding source is
  located and added to `docs/BAHRAIN_PAYROLL_SOURCES.md`.
- If a customer asks for Flexi Permit support before that source exists, treat it
  as a legal-source discovery task, not an implementation task.

## Decision 2: Law No. (68) of 2006 — GCC social insurance protection

Decision: **excluded from current gate scope**.

Reasoning:

- HIS-50 confirmed SIO has a dedicated page naming Law No. (68) of 2006.
- SIO's own page says the content will be published soon, so the blocker is
  government/source publication, not lack of research effort.
- Without the full official text, implementing GCC social insurance protection
  rules would violate the architecture invariant that statutory numbers and
  compliance logic must be official-source backed.

Product rule:

- Do not add Law 68/2006 logic to the Bahrain rule pack until SIO or another
  official primary source publishes the full text and it is added to
  `docs/BAHRAIN_PAYROLL_SOURCES.md`.
- Existing Bahrain WPS and SIO wage-update validators intentionally exclude GCC
  social-insurance-protection logic.

## Decision 3: EOSB "half a month's wages" interpretation

Decision: **monthly wage ÷ 2**.

Reasoning:

- Decision No. (109) of 2023 Article 9 uses the statutory/regulatory wording
  "half a month's wages" for each of the first three years of employment.
- SIO's FAQ paraphrases the same period as "15 days' salary," but the
  regulation text is the primary source.
- Hisham logged the human payroll/legal interpretation on 2026-08-02: implement
  "half a month's wages" as monthly-wage based, not daily-rate based.

Product rule:

- Do not implement the first-three-years EOSB formula as daily wage × 15.
- Implement it as monthly wage ÷ 2, with source citation to
  `docs/BAHRAIN_PAYROLL_SOURCES.md` §2a / Decision 109/2023 Article 9 and the
  2026-08-02 human interpretation note on HIS-54.

## Re-opening either exclusion

Either exclusion can be reopened only when:

1. an official primary source is located;
2. `docs/BAHRAIN_PAYROLL_SOURCES.md` is updated with the citation, retrieval
   date, and ready/not-ready status; and
3. a new implementation ticket is opened that explicitly references the updated
   source section.
