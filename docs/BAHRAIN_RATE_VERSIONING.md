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
| `bahraini_pension_employee_initial` | Bahraini private-sector | Old-age/disability/death | Employee | 2022-04-19 | — | 6% (until 2022-12-31) | `docs/BAHRAIN_SIO_CONTRIBUTION_RATES.md` §1 |
| `bahraini_pension_employee_target` | Bahraini private-sector | Old-age/disability/death | Employee | 2023-01-01 | — | 7% | `docs/BAHRAIN_SIO_CONTRIBUTION_RATES.md` §1 |
| `{category}_unemployment_employee` | Bahraini and non-Bahraini private-sector | Unemployment | Employee | 2006-11-23 | — | 1% | `docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md` §1 |
| `{category}_unemployment_labour_fund` | Bahraini and non-Bahraini private-sector | Unemployment | Labour Fund (Tamkeen) | 2006-11-23 | — | 1% | `docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md` §1 |
| `{category}_unemployment_government` | Bahraini and non-Bahraini private-sector | Unemployment | Government | 2006-11-23 | — | 1% | `docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md` §1 |

**Note on the unemployment-insurance payer**: the private-sector "employer
share" is registered under `BahrainContributionPayer.LABOUR_FUND`, not
`EMPLOYER` — Law 78/2006 Article 6 states the Labour Fund (Tamkeen) pays
this share on the private-sector employer's behalf. There is deliberately
no `EMPLOYER`-payer row for the unemployment branch; requesting one fails
closed by design (see `tests/test_bahrain_sio_contributions.py`).

Added in HIS-68/HIS-69 (implementation for HIS-60/HIS-61's research).

## Deliberately not registered yet

The following regimes are documented but not yet placed in executable registry
data because the merged research still contains unresolved current-rate or
scope questions:

- **Bahraini old-age/disability/death SIO contributions — employer share only.**
  HIS-60 found the Article 33 structure and the employee share's rates are now
  registered (see above). The **employer** share's exact annual step-up
  trigger date (11% → 17%, +1 point/year) is not source-confirmed — the
  amendment text says "increases annually by a rate of 1%" without stating
  the calendar convention, unlike the employee share's explicit "beginning of
  the year following" wording. Needs a human/payroll reviewer to confirm the
  trigger date before this can be added.
- **Employment-injury contribution rates (3%, Decree-Law 24/1976 Article 47).**
  The rate and its original citation are documented in
  `docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md` §1, but its amendment currency is
  not fully confirmed — LLOC's amendment-list pagination for this law could
  not be fully traversed (9 older amendments, pre-2009, unreachable).
- GCC nationals: still blocked on Law 68/2006 full official text.
- Domestic workers, Flexi/successor categories, public-sector, and optional
  self-employed categories: excluded/blocked/future according to the merged
  category matrix.

## Product invariant

HIS-59 must call this registry before exposing a payroll contribution endpoint.
If the registry has no matching rate, the API must return a safe unsupported
response and should name the missing regime/ticket instead of returning a
calculation.
