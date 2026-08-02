# Bahrain Payroll Effective-Date and Rate-Versioning Framework

Deliverable for **HIS-62**.

This framework prevents Bahrain payroll from becoming a pile of hardcoded
"current" numbers. Every deterministic payroll rule must ask a versioned
registry for the applicable rate by:

- worker category;
- contribution branch;
- payer;
- effective date;
- service-year band, where the legal rate is tiered by service.

If the registry has no source-backed rate for that exact context, the rule pack
must fail closed with a "not supported / needs HR review" style error instead of
guessing.

## Implemented in this ticket

- `glue.bahrain_payroll.rate_registry.BahrainPayrollRateRegistry`
- `BahrainPayrollRateLookup`
- explicit worker-category, contribution-branch, and payer enums
- effective date windows with optional end dates
- service-year bands for EOSB rates
- fail-closed lookup behavior
- integration of the existing non-Bahraini EOSB monthly contribution helper with
  the registry

## Rates registered now

Only rates already source-complete enough for deterministic use are registered:

| Code | Worker category | Branch | Payer | Effective from | Service band | Rate | Source |
|---|---|---|---|---|---|---|---|
| `non_bahraini_eosb_first_three_years` | Non-Bahraini private-sector | Expatriate EOSB | Employer | 2024-03-01 | `< 3 completed years` | 4.2% | `docs/BAHRAIN_PAYROLL_SOURCES.md` §2a |
| `non_bahraini_eosb_after_three_years` | Non-Bahraini private-sector | Expatriate EOSB | Employer | 2024-03-01 | `>= 3 completed years` | 8.4% | `docs/BAHRAIN_PAYROLL_SOURCES.md` §2a |

## Deliberately not registered yet

The following regimes are documented but not yet placed in executable registry
data because the merged research still contains unresolved current-rate or
scope questions:

- Bahraini old-age/disability/death SIO contributions: HIS-60 found the
  Article 33 structure, but the exact current phase-in trigger still needs
  current SIO operational confirmation before hardcoding.
- Employment-injury contribution rates: the old 3% figure is documented as not
  independently re-verified after amendments.
- Unemployment insurance split: sourced in HIS-61, but should be added with the
  complete worker-category matrix and contribution-flow handling so Tamkeen /
  Labour Fund payment responsibility is not confused with employer deduction.
- GCC nationals: still blocked on Law 68/2006 full official text.
- Domestic workers, Flexi/successor categories, public-sector, and optional
  self-employed categories: excluded/blocked/future according to the merged
  category matrix.

## Product invariant

HIS-59 must call this registry before exposing a payroll contribution endpoint.
If the registry has no matching rate, the API must return a safe unsupported
response and should name the missing regime/ticket instead of returning a
calculation.
