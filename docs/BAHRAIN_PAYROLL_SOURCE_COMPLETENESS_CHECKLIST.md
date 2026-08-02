# Bahrain payroll source-completeness checklist

Deliverable for **HIS-64**. This is the gate that **HIS-59** (Bahrain
payroll rule-pack API endpoints) depends on. Its job is narrow and
specific: for every capability the API would expose, state plainly whether
it's Ready, Excluded, or Blocked — and specify the exact behavior the API
must have for anything that isn't Ready. This document does not do new
research; it indexes and enforces decisions already made in
`docs/BAHRAIN_PAYROLL_SOURCES.md`, `docs/BAHRAIN_EMPLOYMENT_LAW_SOURCES.md`,
`docs/BAHRAIN_EMPLOYEE_CATEGORY_MATRIX.md`, and
`docs/BAHRAIN_RULE_ENGINE_READINESS.md`.

---

## 1. Capability → ticket → status map

| API capability (what HIS-59 would expose) | Backing rule-pack ticket | Status | Source |
|---|---|---|---|
| WPS compliance validation | HIS-55 (merged, PR #22) | ✅ **Ready** | `BAHRAIN_PAYROLL_SOURCES.md` §2a-ter, §2c |
| SIO wage-update validation | HIS-56 (merged, PR #23) | ✅ **Ready** | `BAHRAIN_PAYROLL_SOURCES.md` §2a-ter |
| Non-Bahraini EOSB calculation (post 1 Mar 2024) | HIS-54 (merged, PR #25) | ✅ **Ready** | `BAHRAIN_PAYROLL_SOURCES.md` §2a |
| Non-Bahraini EOSB — pre/post March-2024 liability split | HIS-63 | ❌ **Blocked — not yet implemented** | `BAHRAIN_RULE_ENGINE_READINESS.md` §1 |
| Bahraini SIO contributions | HIS-60 | ❌ **Blocked — not yet sourced or implemented** | `BAHRAIN_EMPLOYEE_CATEGORY_MATRIX.md` (Bahraini row) |
| Non-Bahraini standard (non-EOSB) SIO contributions | HIS-61 | ❌ **Blocked — not yet sourced or implemented** | `BAHRAIN_EMPLOYEE_CATEGORY_MATRIX.md` (non-Bahraini row) |
| GCC national SIO contributions | Not yet ticketed — depends on Law 68/2006 being published | ❌ **Blocked on government** | `BAHRAIN_PAYROLL_SOURCES.md` §2a-bis, §5 |
| Versioned/effective-dated rate lookup (any of the above) | HIS-62 | ❌ **Blocked — framework not yet built** | New requirement; without this, any of the ✅ Ready rows above are still only correct for whatever rate is currently hardcoded, not date-aware |
| Labour Law entitlements (leave/hours/termination) as API-exposed calculations | Not yet ticketed (see HIS-65's proposed follow-up tickets) | ❌ **Not implemented** (sourced, not built) | `BAHRAIN_EMPLOYMENT_LAW_SOURCES.md` §2, §3, §5 |
| Domestic worker payroll (any regime) | Not yet ticketed | ❌ **Blocked — category applicability unresolved** | `BAHRAIN_EMPLOYEE_CATEGORY_MATRIX.md` (domestic worker row) |
| Flexi Permit worker payroll | Excluded per HIS-58 | ❌ **Excluded (deliberate, not a gap)** | `BAHRAIN_PAYROLL_SOURCES.md` §2a-ter, §8 |
| Public-sector employee payroll | Explicitly out of scope | ❌ **Out of scope (deliberate)** | `BAHRAIN_EMPLOYEE_CATEGORY_MATRIX.md` (public-sector row) |

**Reading this table**: HIS-59 cannot expose a capability whose row above is
❌. Concretely, that means **HIS-59 cannot ship a general "calculate SIO
contributions" or "calculate EOSB" endpoint today** — only the specific,
already-scoped combination of *non-Bahraini, post-1-March-2024, EOSB-only*
calculation is actually Ready. Everything else must either not exist as an
endpoint yet, or exist and return the explicit safe-error contract in §3.

---

## 2. Employee-category readiness (mirrors `BAHRAIN_EMPLOYEE_CATEGORY_MATRIX.md`)

| Category | Ready for API exposure? |
|---|---|
| Bahraini private-sector employee | ❌ No — SIO contribution rates not sourced (HIS-60) |
| Non-Bahraini private-sector employee | ⚠️ **Partial** — EOSB only (HIS-54, done); standard SIO contributions not sourced (HIS-61) |
| GCC national | ❌ No — blocked on Law 68/2006 publication |
| Domestic worker | ❌ No — Labour Law/SIO/WPS applicability unresolved |
| Public-sector employee | ❌ **Deliberately out of scope**, not a gap |
| Self-employed/optional/partner | ❌ No — not yet classified |
| Flexi Permit worker | ❌ **Deliberately excluded** per HIS-58, not a gap |
| Temporary/part-time/casual | ❌ No — not yet classified |
| Remote/outside-Bahrain worker | ❌ No — not yet researched |

**Per HIS-64's own acceptance criteria**: this table is the enforcement
point for "the general payroll API cannot be marked ready while Bahraini
and non-Bahraini contribution regimes are incomplete." As of this writing,
**zero categories are fully ✅ Ready** — non-Bahraini is the closest, at
partial (EOSB only, standard contributions still blocked).

---

## 3. Required safe-error contract for unsupported capabilities

This is the specific behavior HIS-59 must implement for every ❌ row above,
and it's a **binding requirement on HIS-59's implementation**, not just
documentation:

- If a request targets an employee category or rule area marked ❌ in §1/§2,
  the API **must return an explicit "not supported" response** — a
  distinct error type/status, not a 500, not a silently-wrong number, and
  not a partial calculation with missing components silently zeroed out.
- The response should be specific enough to be actionable: which category
  or rule area is unsupported, and (where applicable) which ticket is
  tracking the gap — e.g. "Bahraini SIO contribution calculation is not
  yet supported; tracked in HIS-60."
- This mirrors the product-safety invariant already stated in
  `BAHRAIN_RULE_ENGINE_READINESS.md` §3, invariant 4: *"If a country-law
  rule area is not source-complete, the system must return 'not supported /
  needs HR review,' never a guessed extrapolation."* HIS-64's job is to
  make sure HIS-59 actually implements that invariant at the API boundary,
  not just in prose.
- **Suggested test requirement for HIS-59** (for whoever implements it):
  a test that submits a request for each ❌ category/capability combination
  in §1/§2 and asserts the safe-error response, not just tests for the ✅
  happy paths. This is the same "verify the negative case, not just the
  positive one" discipline HIS-57's citation guard applies to statutory
  numbers.

---

## 4. What would need to change for a row to move from ❌ to ✅

For transparency on the actual unblock path per open ticket:

- **HIS-60 / HIS-61** (Bahraini / non-Bahraini standard SIO): needs a
  research pass locating and verifying official SIO contribution rates for
  these two populations, the same way Decision 109/2023 was verified for
  non-Bahraini EOSB — full text, quoted figures, effective dates.
- **HIS-62** (rate versioning): needs a framework decision + implementation
  (not just sourcing) — even once HIS-60/61's rates are known, they need to
  be stored with effective dates so a rate change doesn't silently break
  historical payroll runs.
- **HIS-63** (EOSB pre/post split): needs the population and liability-split
  question actually resolved — who bears legacy pre-March-2024 EOSB
  liability, and how the SIO-funded scheme interacts with it. Not yet
  researched.
- **GCC / Law 68/2006**: blocked on the Bahrain government publishing the
  text — not something more research can unblock; re-check periodically
  per `BAHRAIN_PAYROLL_SOURCES.md` §5.
- **Domestic workers, Flexi Permit, public sector, self-employed,
  temporary, remote**: each needs its own scope decision (research +
  explicit Ready/Excluded/Blocked call) before it can move off this table's
  ❌ default.
