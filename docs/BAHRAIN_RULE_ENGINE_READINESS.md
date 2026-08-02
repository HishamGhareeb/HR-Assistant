# Bahrain rule-engine readiness

Cross-cutting deliverable spanning **HIS-64** (source-completeness gate),
**HIS-65** (labor-law entitlements), **HIS-66** (LMRA operations), and
**HIS-67** (employee-category matrix). This is the practical "can we build
this yet" reference — it does not introduce any new statutory citations
beyond what's already in `docs/BAHRAIN_PAYROLL_SOURCES.md` and
`docs/BAHRAIN_EMPLOYMENT_LAW_SOURCES.md`; it synthesizes them into a
decision table, a module map, and the product-safety invariants that should
gate implementation and API exposure.

---

## 1. Rule-area readiness table

| Rule area | Official source complete? | Arabic original obtained? | English translation obtained? | Statutory values identified? | Contradictions found? | Human review required? | Safe to implement deterministic rule? | Suggested Linear ticket | Priority |
|---|---|---|---|---|---|---|---|---|---|
| Bahraini SIO contributions | **No** | No | No | No | No | Yes, once sourced | **No — blocked** | HIS-60 | High |
| Non-Bahraini standard SIO (non-EOSB) | **No** | No | No | No | No | Yes, once sourced | **No — blocked** | HIS-61 | High |
| GCC unified SIO regime | **No — government has not published Law 68/2006 text** | No | No | No | No | Yes, once sourced | **No — blocked on government** | Tracked under HIS-58 decision, or a new ticket per its outcome | Medium (blocked, not actionable) |
| Non-Bahraini EOSB (SIO-funded, post 1 Mar 2024) | **Yes** | No (English official translation only) | Yes | Yes (4.2%/8.4%, wage÷2 formula) | No (interpretation question was resolved via human decision, not a source contradiction) | Already done (HIS-54 decision logged) | **Yes — implemented** (HIS-54, merged) | Done | — |
| Legacy (pre-SIO-scheme / Labour-Law Art. 116) gratuity | **Partial** — Article 116 text obtained, but which workers this still applies to today (workers "not subject to the Social Insurance Law") is not confirmed | No | Yes (LMRA PDF) | Yes (same "half a month/one month" formula) | **Possible overlap/ambiguity with the SIO EOSB scheme's population** — not resolved | Yes | **No — blocked pending HIS-63's pre/post-March-2024 split work and population clarification** | HIS-63 | High |
| WPS file validation | **Yes** | No | Yes (official manual) | Yes | No | No | **Yes — implemented** (HIS-55, merged) | Done | — |
| SIO wage-update rules | **Yes** | No | Yes (SIO guides) | Yes | No | No | **Yes — implemented** (HIS-56, merged) | Done | — |
| Wage payment timing | **Yes** | No | Yes | Yes (once/month min, 6–12% late penalty) | No | No | **Yes — not yet ticketed for implementation** | New ticket recommended (see §4 of the Linear proposal below) | Medium |
| Overtime | **Yes** | No | Yes | Yes (+25% day / +50% night / 150% rest-day) | No | No | **Yes — not yet ticketed** | New ticket recommended | Medium |
| Annual leave | **Yes** | No | Yes | Yes (30 days/yr, 2.5 days/month accrual) | No | No | **Yes — not yet ticketed** | New ticket recommended | Medium |
| Sick leave | **Yes** | No | Yes | Yes (15/20/20 split, 240-day cap) | No | No | **Yes — not yet ticketed** | New ticket recommended | Medium |
| Maternity leave | **Yes** | No | Yes | Yes (60 days full + 15 unpaid) | No | No | **Yes — not yet ticketed** | New ticket recommended | Medium |
| Public holidays | **Partial** — the entitlement rule (150% pay or substitute day) is sourced, but the actual holiday-date calendar (Council of Ministers Edict) is not located | No | Partial | Partial | No | No | **No — need the calendar instrument first** | Follow-up research item | Medium |
| Termination / notice period | **Yes** | No | Yes | Yes (30 days, compensation formulas) | No | No | **Yes — not yet ticketed** | New ticket recommended | High (touches money) |
| Unfair dismissal | **Yes** | No | Yes | Yes (grounds + 50% uplift) | No | Recommended given legal-liability exposure | **Yes, with review** | New ticket recommended | High |
| Probation | **Yes** | No | Yes | Yes (3/6 months, 1-day notice) | No | No | **Yes — not yet ticketed** | New ticket recommended | Low-medium |
| Work permits (issuance/renewal/cancellation) | **Partial** — fee schedule and domestic-worker permit fully sourced; general expatriate work-permit issuance/renewal procedural detail not yet researched | No | Partial | Partial | No | No | **No — needs HIS-66 follow-up** | HIS-66 | Medium |
| Domestic workers (full category treatment) | **Partial** — LMRA permit regulation sourced; Labour Law/SIO/WPS applicability not confirmed | No | Partial | Partial | No | Yes | **No — blocked pending HIS-66** | HIS-66 | Medium |
| LMRA fees (general) | **Yes** | No | Yes (Resolution 1/2017) | Yes | No | No | **Yes — not yet ticketed** (informational/employer-cost, not payroll) | Low priority, informational | Low |
| SIO/Labour-Law wage-discrimination clause | **Contradiction found — see below** | No | Partial (conflicting versions) | Partial | **Yes** — LMRA PDF's Article 39 does not show the "work of equal value" second paragraph that Decree 16/2021 (fully sourced) says was added | Yes | **No — blocked on human legal review of the contradiction** | New ticket recommended (see below) | High |
| Employee category classification | **Yes** (matrix built) | N/A | N/A | N/A | N/A | No | **Yes — the matrix itself is the deliverable** (HIS-67) | HIS-67 | High (gates everything else) |

---

## 2. HRMS module → legal-source mapping

For each module, what's legally required, what must stay deterministic
(never LLM-computed), and what should block until source-complete.

| Module | Required legal sources | Deterministic rules required | Required citations | Must never be LLM-computed | Block until source-complete? |
|---|---|---|---|---|---|
| **Employee profile** | Employee-category matrix (HIS-67) | Category classification logic | Category matrix | Category determination itself | Yes — category must be known before any downstream module runs |
| **Contract management** | Law 36/2012 Parts One, Three, Twelve | Contract-type determination (indefinite vs. definite vs. specific-work per Art. 98); probation validity (Art. 21) | Employment-law doc §2 | Contract-type edge cases | No, but probation-length validation should be rule-based |
| **Onboarding** | Employee-category matrix | Category-based module routing | Category matrix | — | Yes for category-dependent onboarding steps |
| **Work permits / immigration** | LMRA fee schedule, Order 4/2014 (domestic), general work-permit regulation (not yet sourced) | Fee calculation, permit-type routing | Payroll doc §2a-bis, §2c | Permit fee amounts | Yes for general expatriate permit logic pending HIS-66 |
| **Attendance** | Law 36/2012 Part Seven (hours/rest) | Max-hours validation, rest-period enforcement | Employment-law doc §2 | Overtime-rate calculation | No — sourced and ready |
| **Leave management** | Law 36/2012 Parts Five, Eight | Accrual, entitlement caps, pay rate per leave type | Employment-law doc §3 | Leave-balance/entitlement amounts | No — sourced and ready, except the public-holiday calendar |
| **Payroll** | Law 36/2012 Part Six, SIO wage-update rules (HIS-56) | Wage timing, late-payment penalty, salary-update constraints | Employment-law doc §5; payroll doc §2a-ter | Statutory rates/caps | No — sourced and ready for the parts already implemented |
| **WPS export** | Resolution 68/2019, WPS Manual | File schema, record cap, scheduling window | Payroll doc §2a-ter, §2c | — | No — implemented (HIS-55) |
| **SIO reporting** | Decree-Law 24/1976, Decision 109/2023, HIS-60/61 (pending) | Contribution-rate selection, wage-base rules | Payroll doc §2a | Contribution amounts for non-EOSB SIO | **Yes for non-EOSB SIO reporting, pending HIS-60/61** |
| **EOSB / gratuity** | Decision 109/2023, Legislative Decree 21/2020, Law 36/2012 Art. 116 | Rate selection, gratuity formula, pre/post-March-2024 handling | Payroll doc §2a; employment-law doc §5 | Gratuity amounts | No for the SIO-scheme (implemented, HIS-54); **Yes for legacy Art. 116 population until HIS-63 resolves it** |
| **Termination / offboarding** | Law 36/2012 Part Twelve | Notice validation, compensation formula, unfair-dismissal flagging | Employment-law doc §5 | Compensation amounts | No — sourced, not yet ticketed for implementation |
| **Document management** | Tenant-scoping invariants (architecture handoff) | Classification tiers (public/internal/manager-only/hr-only) | Architecture handoff | — | No — general platform concern, not Bahrain-specific |
| **HR admin alerts** | All of the above | Threshold-based alerting (leave-balance low, probation ending, notice-period active, etc.) | All above | — | Depends on underlying module readiness |
| **Audit logs** | Architecture handoff invariants | Metadata-only audit trail | Architecture handoff | — | No — general platform concern |
| **AI knowledge base / RAG citations** | All of the above | Retrieval-indexed citation format (already used across both Bahrain docs) | All above | **Any statutory number or legal claim answered by the LLM without a retrieval citation** | This is the enforcement point for the "LLM must not calculate/recall statutory facts" invariant — see §3 |

---

## 3. Product safety invariants

These carry forward and extend the citation-integrity discipline already
established in `docs/BAHRAIN_PAYROLL_SOURCES.md` §6 and enforced in code by
HIS-57's citation guard.

1. **The LLM may explain a rule in natural language, but must never
   calculate a statutory amount from memory.** Every payroll/entitlement
   number returned to a user must trace to a citation, exactly as HIS-57's
   CI check enforces for code-level constants.
2. **Payroll and entitlement calculations must be deterministic code**, not
   LLM-generated arithmetic, even when the underlying rule is simple.
3. **Every statutory number must have a source citation**, and every
   source-backed number must carry its **effective date** — this matters
   concretely for Bahrain given the confirmed 1 March 2024 EOSB effective
   date and the still-open pre/post split question (HIS-63).
4. **If a country-law rule area is not source-complete, the system must
   return "not supported / needs HR review" — never a best-guess
   extrapolation.** This is the behavior the readiness table in §1 above is
   meant to drive: any ❌/blocked row must map to this response, not a
   silent fallback.
5. **`PUBLIC` document classification means tenant-public only, never
   globally public** — carried over unchanged from the architecture
   handoff's core invariant; restated here because Bahrain legal-source
   documents (this one included) will eventually be ingested into the
   tenant-scoped knowledge base and must respect this.
6. **Employee category must be determined before any payroll or
   entitlement calculation runs.** The category matrix
   (`BAHRAIN_EMPLOYEE_CATEGORY_MATRIX.md`) is the lookup table; a category
   that isn't ✅ Supported in that matrix should short-circuit to the
   "not supported" response in invariant 4, not fall through to a default
   calculation path.
7. **The Bahrain payroll API (HIS-59) must not ship until category
   coverage is complete or an explicit waiver is recorded** — this is
   exactly why HIS-59 was made to depend on HIS-60 through HIS-64.
8. **Bahrain-first does not mean Bahrain-only.** Doc structure (source
   inventory → category matrix → readiness table → module map) is intended
   to be a repeatable pattern for future country packs, not a Bahrain-only
   one-off — worth keeping in mind if/when a second country is scoped.

---

## 4. Similar-gap audit — what else might be missing

Applying the "what neighboring regime could make this incomplete" check
explicitly, per instruction, to what's been sourced so far:

- **EOSB researched → checked**: ordinary SIO contributions (found the gap,
  now HIS-60/61), legacy Labour-Law gratuity (Art. 116, found — now flagged
  as a possible population overlap needing HIS-63 to resolve).
- **Payroll/WPS researched → checked**: wage timing and salary-update
  reporting (both sourced in this pass and the payroll doc).
- **Work permits researched → partially checked**: fees (sourced), domestic
  worker permit (sourced); renewals/cancellation/transfer/medical checks
  for the *general* (non-domestic) expatriate population — **not yet
  checked, this is a real gap for HIS-66**.
- **Leave researched → checked**: sick, maternity, marriage, bereavement,
  Hajj, paternity/birth all found; public holiday **calendar instrument**
  itself is the one piece still missing (the entitlement *rule* is sourced,
  the actual *dates* are not).
- **Bahraini employees researched → checked**: this surfaced that
  Bahraini-specific SIO contribution rates were never actually sourced
  anywhere in prior passes (everything SIO-related so far was non-Bahraini
  EOSB-specific) — this is the single most important gap this pass found,
  now HIS-60.
- **Non-Bahrainis researched → checked**: LMRA (extensive prior coverage),
  SIO work-injury/EOSB (found the EOSB/standard-contribution distinction,
  now HIS-61), WPS (sourced), domestic-worker distinction (partially
  checked, flagged as incomplete above).
- **Not yet audited this way**: the termination/unfair-dismissal area
  (Part Twelve) hasn't been cross-checked against SIO's disability/death
  provisions (Art. 113–114 reference "the Social Insurance Law" without
  detail) — worth a targeted follow-up before termination logic is built.
