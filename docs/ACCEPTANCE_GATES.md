# Pilot acceptance gates

Six gates a pilot must clear before go-live: five are automated and
enforced in CI on every PR (`.github/workflows`, `uv run pytest -q`); the
sixth is a human decision this document tracks but cannot automate.

## Pass/fail criteria

| Gate | What it verifies | Automated tests | Pass criterion |
|---|---|---|---|
| 1. Prompt injection | Text embedded in a retrieved document cannot cause unauthorized content to reach the model, cannot forge extra response fields the code acts on, and a hijacked/malformed model response fails closed | `tests/test_acceptance_gates.py::test_gate_prompt_injection_*` (3 tests) | 100% pass, zero tolerance |
| 2. PII leakage | Every model response is scanned before delivery; the client receives the scanner's sanitized text, never the raw output; a scanner rejection withholds the answer entirely; the audit trail never carries raw question/answer/PII content, even on a blocked response | `tests/test_acceptance_gates.py::test_gate_pii_leakage_*` (4 tests) | 100% pass, zero tolerance |
| 3. Cross-user / cross-tenant isolation | A misbehaving retrieval adapter that returns another tenant's document is still contained by the authorization layer (defense in depth); identical local object IDs in two tenants never collide; every pipeline call requires a verified `Identity` | `tests/test_acceptance_gates.py::test_gate_cross_*` (3 tests) — plus the broader tenant-isolation coverage already in `tests/test_app.py`, `tests/test_suggestions.py`, `tests/test_feedback.py` | 100% pass, zero tolerance |
| 4. Hallucination containment | With zero authorized documents, the model is never invoked at all (it cannot hallucinate from nothing); a suggestion missing its required grounding field fails schema validation and blocks the whole response rather than being silently admitted | `tests/test_acceptance_gates.py::test_gate_hallucination_*` (2 tests) | 100% pass, zero tolerance |
| 5. Outage resilience | Onyx, OpenFGA, Claude, and the output scanner each fail closed with a safe, non-crashing response on failure/timeout, and exactly one audit event is emitted regardless of which dependency failed | `tests/test_acceptance_gates.py::test_gate_outage_*` (5 tests) — plus dependency-failure coverage in `tests/test_pipeline.py` | 100% pass, zero tolerance |
| 6. Regression | Every existing behavior across the codebase continues to work | The full suite: `uv run pytest -q` | 100% pass. As of this gate's introduction: 407 tests |

Run the automated gates:

```bash
uv run pytest tests/test_acceptance_gates.py -v   # gates 1-5, individually
uv run pytest -q                                  # gate 6, the full regression baseline
```

## What these gates deliberately do not cover

- **Live PII detection accuracy.** `glue/llm_guard_scan.py`'s `OutputScanner`
  wraps a third-party ML model (`llm-guard`'s `Sensitive` scanner); the
  automated gates above fake that scanner's `is_valid`/sanitized output to
  keep the suite fast and deterministic, and instead prove the *pipeline*
  always calls it, always delivers its sanitized output, and always fails
  closed if it errors. Whether the real model actually catches a given
  novel PII pattern is a live-model concern, not a pipeline-wiring
  concern — see the manual smoke-test item in the sign-off checklist below.
- **Semantic hallucination** (a technically well-formed, schema-valid
  answer that still misstates something true about the retrieved context).
  The automated gate proves the *structural* containment (no context, no
  model call; ungrounded suggestion shape rejected) — judging whether a
  fluent answer is factually faithful to its context needs a human or an
  LLM-judge eval, not a deterministic unit test.

## Human pilot sign-off

A pilot may not go live until a named approver has completed and dated
every item below. This is a manual gate by design — no amount of
automated testing substitutes for a human deciding the product is ready
for a real customer's data.

- [ ] All five automated gates pass in CI on the exact commit being piloted.
- [ ] The regression baseline (`uv run pytest -q`) passes with zero
      failures on the exact commit being piloted.
- [ ] **Manual PII smoke test**: ask the live (non-faked) system 5-10
      questions designed to surface real PII (CPR numbers, salary figures,
      SSN-shaped strings) against the seeded demo organization
      (`docs/DEMO_ORGANIZATION.md`) or a pilot-specific dataset, and confirm
      the real `OutputScanner` redacts/blocks as expected — not just the
      faked-scanner unit tests.
- [ ] **Manual cross-tenant smoke test**: with two provisioned tenants,
      confirm a user authenticated for tenant A cannot retrieve any
      tenant B content through the live API, not just the fake-adapter
      unit tests.
- [ ] `HR_REVIEWERS_JSON` / `HR_ADMINS_JSON` / `HR_FEEDBACK_REVIEWERS_JSON`
      are provisioned with the pilot's real reviewers, not demo/test values.
- [ ] Audit log (`AUDIT_LOG_PATH`) and its privacy key
      (`AUDIT_PRIVACY_KEY`) are provisioned for the pilot's own storage,
      not a shared/dev location.
- [ ] Approver name, role, and date recorded below.

| Approver | Role | Date | Commit SHA piloted |
|---|---|---|---|
| _(unsigned)_ | | | |
