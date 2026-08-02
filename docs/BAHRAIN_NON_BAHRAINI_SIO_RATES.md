# Non-Bahraini standard (non-EOSB) SIO contribution rates

Research deliverable for **HIS-61**. **No calculation code is added by
this document.**

**Relationship to other docs**: `docs/BAHRAIN_SIO_CONTRIBUTION_RATES.md`
(HIS-60) established that the old-age/disability/death pension branch
(Article 33 of Decree-Law 24/1976) applies to Bahraini employees today,
after non-Bahrainis were carved out into the EOSB gratuity scheme
(Decision 109/2023, effective 1 March 2024). This document covers what
non-Bahraini private-sector employees **still** contribute to, separate
from EOSB — this is the actual scope of "standard non-EOSB SIO
contributions" the ticket asks about.

---

## 1. The core finding — two branches remain, both nationality-neutral

Both of the branches below apply to Bahraini **and** non-Bahraini workers
identically, because their scope articles are tied to the base Social
Insurance Law's Article 2, which applies **"without discrimination as to
sex, nationality, or age"** (already confirmed in
`BAHRAIN_SIO_CONTRIBUTION_RATES.md` §1/§3). Neither branch has a
non-Bahraini-specific carve-out the way the pension branch does.

### Employment injury insurance (Decree-Law 24/1976, Article 47)

| Field | Value |
|---|---|
| **Rate** | **3% of monthly wages, employer-only.** |
| **Source text** | "The social insurance against employment injuries shall be financed by the following:- the monthly contributions which the employer shall be required to pay to the General Organisation at the rate of 3% of the monthly wages of his workers. The employer alone shall be responsible for the payment of this contribution." |
| **Source** | https://www.sio.gov.bh/en/law-no-24-of-1976 (modal, same as HIS-50/§2a and HIS-60) |
| **Retrieved** | 2026-08-02 |
| **⚠ Currency status** | **Not fully confirmed as current.** Article 47 is not among the articles replaced by Law 14/2022 (the most substantial recent amendment, confirmed in HIS-60), nor is it targeted by any of the 10 most-recent amendments visible on LLOC's amendment list for this law (2009–2026). However, **LLOC's amendment-list pagination is broken** (page 2, covering 9 older amendments back to the 1970s/80s/90s, could not be reached — tried click, JS click, query param, and path param, all failed). It is **plausible but not certain** that 3% remains current. |

### Unemployment insurance (Law 78/2006, Article 6)

| Field | Value |
|---|---|
| **Rates** | **1% of wage from the insured employee, 1% from the employer, 1% from the Government**, all monthly. |
| **Notable detail** | "The Labour Fund shall pay the employers' share for the insureds employed in the private sector" — i.e. **Tamkeen (the Labour Fund) covers the private-sector employer's 1% share**, not the employer directly. This is a materially different payment-flow model than the other branches and worth getting right in any implementation — the "employer contribution" for this branch is not actually paid by the employer for private-sector workers. |
| **Scope (Article 2)** | Applies to "Private sector workers who are covered by the provisions of insurance against employment injuries according to the provisions of the Law on Social Insurance" — i.e. coverage is derived from employment-injury coverage (Article 47 above), which is itself nationality-neutral. |
| **Source** | https://www.sio.gov.bh/en/insurance-against-unemployment → https://www.sio.gov.bh/en/law-no-13-of-1975-818549 (same modal already used for the full-text retrieval in `BAHRAIN_PAYROLL_SOURCES.md` §2a-ter — that pass quoted the preamble/closing only; this pass extracted the operative subscription-rate article) |
| **Retrieved** | 2026-08-02 |
| **Status** | **Verified — full article text read, no amendment-currency concern found** (Law 78/2006 was not checked against its own LLOC amendment list in this pass — flagged as a residual gap, see §3). |

---

## 2. What this means for a non-Bahraini employee's total standard SIO burden (structural summary, not a formula)

For a non-Bahraini private-sector employee **today** (post-1-March-2024),
the branches that apply are:

1. **EOSB gratuity** (replaces the old-age/disability/death branch):
   employer-only, 4.2% (first 3 years) / 8.4% (thereafter) — already fully
   sourced and implemented (HIS-54).
2. **Employment injury**: employer-only, 3% (currency not fully confirmed,
   see §1).
3. **Unemployment insurance**: 1% employee + 1% employer-share-paid-by-
   Tamkeen-not-employer + 1% government — sourced this pass.

**Not found**: a sickness/maternity temporary-disability branch
contribution rate — Article 1 of the base law lists this as a branch, but
no rate was located for it in any pass so far (same gap noted for
Bahrainis in HIS-60).

This is a narrower and more specific answer than the ticket's original
"4% / 3% / 1%" framing (which appears to have been an unverified estimate
per the ticket's own text) — the actual sourced figures are 3% (injury)
and 1%/1%/1% (unemployment), not 4%/3%/1%. **Do not carry the ticket's
original percentages forward** — they don't match what was found.

---

## 3. Still open

- **Article 47's currency** — cannot be confirmed without reaching page 2
  of Decree-Law 24/1976's amendment list (broken pagination, see §1).
- **Law 78/2006's own amendment history** — not checked against LLOC's
  amendment list the way Decree-Law 24/1976 was; the 1%/1%/1% rates above
  could themselves be superseded by an amendment not yet located.
- **Sickness/maternity temporary-disability branch rate** — not located in
  any pass.
- **Wage cap/floor for either branch** — not located.

---

## 4. Explicit rejection of AI-generated statutory numbers

Both rates in §1 are direct quotes from official SIO-hosted full-text law
documents retrieved in this session, not recalled from training data or
the ticket's own unverified estimate. The currency caveats in §1 and §3
are stated explicitly because LLOC's amendment-list pagination could not
be fully traversed — this is a disclosed limitation, not a silent gap.
