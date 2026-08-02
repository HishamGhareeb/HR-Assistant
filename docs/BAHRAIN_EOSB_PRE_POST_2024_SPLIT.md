# Non-Bahraini EOSB — pre/post 1 March 2024 liability split

Research deliverable for **HIS-63**. **No calculation code is added by
this document.**

**The core open question** (from `docs/BAHRAIN_SIO_CONTRIBUTION_RATES.md`
§1 and §4, HIS-60): non-Bahraini private-sector employees were covered
under the general Article 33 old-age/disability/death SIO pension branch
before being carved out into the SIO-funded EOSB gratuity scheme
(Decision 109/2023, effective 1 March 2024). What happens to a
non-Bahraini employee's **pre-1-March-2024 accrued entitlement**?

**Answer, sourced directly from Decision 109/2023's own transition
articles**: it is **not** converted into the SIO fund at all. It stays
governed by a **different, separate legal regime** — the Labour Law's own
gratuity provision.

---

## 1. The split, stated explicitly by the Regulation itself

Decision No. (109) of 2023's attached Regulation contains two transition
articles that directly resolve this:

| Field | Value |
|---|---|
| **Article 14 — "Duration of Service Prior to the Enforcement of the Provisions of this Regulation"** | **"The Remuneration of the Insured Person for the period of service prior to the entry into force of this Regulation shall apply to the provisions of the Private Sector Labor Act promulgated by Law No. (36) of 2012."** |
| **Source** | https://www.sio.gov.bh/en/end-of-service-benefits (modal `#law-no21`, same source as `BAHRAIN_PAYROLL_SOURCES.md` §2a) |
| **Retrieved** | 2026-08-02 |

**What this means in practice**: a non-Bahraini employee's total gratuity
at termination is **split into two separately-calculated, separately-liable
portions**:

1. **Pre-1-March-2024 service**: calculated under **Law 36/2012 Article
   116** — already fully sourced in `docs/BAHRAIN_EMPLOYMENT_LAW_SOURCES.md`
   §5: *"half a month's wage for each of the first three years of
   employment and one month's wage for each of the following years in
   service."* This is a **direct employer liability** under the Labour
   Law, not something accrued via monthly SIO contributions — the
   employer owes and pays this portion itself, the same way it always did
   before Decision 109/2023 existed. **Note**: this is the *same numeric
   formula wording* ("half a month's wage") as the post-2024 SIO scheme —
   so the two regimes happen to compute at the same rate, but they are
   legally distinct liabilities with different payers/funding mechanisms,
   not one continuous accrual.
2. **Post-1-March-2024 service**: calculated and funded under **Decision
   109/2023** itself — monthly employer contributions (4.2%/8.4%, per
   Article 5) accrue into the SIO-managed "Retirement and Social Insurance
   Fund" (established by Legislative Decree 21/2020, per HIS-60's
   finding), and the gratuity for this period is paid out from that fund.

**This is not a conversion or a rollover — it's two coexisting legal
regimes applying to two different date ranges of the same person's
service.** A rule pack must calculate both portions separately and sum
them, not treat the employee's entire tenure as one continuous formula.

---

## 2. The contribution-rate transition rule (Article 13)

For employees who **already had more than 3 years of service** with their
employer before Decision 109/2023 took effect:

| Field | Value |
|---|---|
| **Article 13 — "Contributions From Employers' Insured Persons Prior to The Entry into Force of the Provisions of this Regulation"** | **"...if the Insured Person is employed by the Employer for a period exceeding three years before the entry into force of the provisions of this Regulation, the Contribution to which the Employer is obliged for the Insured Person from the beginning of the provisions of this Regulation until the end of service is (8.4%) of the wage."** |
| **Effect** | These employees' monthly SIO contribution **skips straight to the 8.4% rate** from 1 March 2024 onward — they do not get a fresh "first 3 years at 4.2%" phase-in, because Article 5's 4.2%-then-8.4% schedule is keyed to years of employment, and these employees already passed the 3-year mark before the scheme even started. Employees with **≤3 years** of pre-2024 service presumably continue on the normal Article 5 schedule (4.2% until they collectively reach 3 years of service, counting pre- and post-2024 time together) — this specific sub-case is not explicitly spelled out in Article 13's text and is an inference, not a direct quote; flagged for confirmation. |
| **Source** | Same as §1 |

---

## 3. What is NOT addressed by the text read so far

- **Exactly how "3 years" is measured for Article 13's threshold** — from
  the employee's original hire date presumably, but this is an inference,
  not explicitly restated in Article 13 itself.
- **Whether the pre-2024 Labour-Law-formula portion (§1, item 1) is paid
  out at the same time as the post-2024 SIO-fund portion** (i.e., both at
  final termination) **or on a different schedule** — the text implies
  "at end of service" for both but doesn't explicitly confirm simultaneity.
- **Whether an employer who already paid out some pre-2024 gratuity
  liability under the old system** (e.g., a employee who left and was
  rehired, or an interim settlement) **gets any credit or offset** — not
  addressed in the articles read.
- **The relationship between this split and Legislative Decree 21/2020's
  fund merger** (which combined the Government Employees Retirement Fund
  and the Social Insurance Fund into one "Retirement and Social Insurance
  Fund," per HIS-60) — Decision 109/2023 is dated *after* that 2020 merger,
  so the post-2024 EOSB contributions presumably flow into the
  already-merged fund, but this specific linkage was not independently
  re-verified in this pass.

---

## 4. Explicit rejection of AI-generated statutory numbers

Both Article 13 and Article 14 are direct quotes from the official SIO-
hosted text of Decision No. (109) of 2023, already partially quoted in
`BAHRAIN_PAYROLL_SOURCES.md` §2a but not previously analyzed for their
transition-mechanism implications. The cross-reference to Law 36/2012
Article 116 is likewise a direct quote already sourced in
`BAHRAIN_EMPLOYMENT_LAW_SOURCES.md` §5. The two inferences flagged in §2
and §3 are explicitly marked as inferences, not verified figures — they
must not be hardcoded into a rule pack without further confirmation.
