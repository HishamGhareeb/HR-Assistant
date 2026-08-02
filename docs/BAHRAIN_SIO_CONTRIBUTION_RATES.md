# Bahrain SIO contribution rates — Bahraini and standard non-Bahraini

Research deliverable for **HIS-60** (Bahraini SIO contribution rule pack)
and **HIS-61** (non-Bahraini standard SIO contribution rule pack), with
direct structural implications for **HIS-63** (EOSB pre/post-March-2024
split) and **HIS-66/HIS-67** (domestic-worker scope). **No calculation code
is added by this document.**

**Relationship to existing docs**: `docs/BAHRAIN_PAYROLL_SOURCES.md` §2a
already has the full text of Decree-Law 24/1976 (base Social Insurance Law)
and Decision 109/2023 (non-Bahraini EOSB, 4.2%/8.4%). This document adds
the contribution-*rate* articles within Decree-Law 24/1976 itself (not
previously extracted in detail) plus its amendment history, which turns out
to be the actual answer to HIS-60's question and reframes HIS-61's and
HIS-63's scope.

**Source discipline**: same standing rule as all Bahrain research in this
repo — official sources only (LLOC, SIO, LMRA), Arabic Gazette text
authoritative, English is reference-only. Per the lesson learned in HIS-65
(§4 of `BAHRAIN_EMPLOYMENT_LAW_SOURCES.md`): **no single "full text" LLOC
document self-consolidates amendments.** This pass explicitly checked the
base law's amendment list before treating any rate as current — the base
1976 text's original rates (11% employer / 7% employee) are **confirmed
superseded**, not current.

---

## 1. The central finding — Article 33 is the current rate-setting provision

Decree-Law 24/1976 has **19 official amendments** on LLOC
(https://www.lloc.gov.bh/En/Legislation/Amendments/L2476, base law
identifier `L2476`). The most recent rate-setting amendment is:

| Field | Value |
|---|---|
| **Title** | Law No. (14) of 2022 amending Some Provisions of the Social Insurance Law promulgated by Legislative Decree No. (24) of 1976 |
| **Full text** | **Downloaded and parsed in full** — replaces Articles 4(1)(5), 33(1)(2), 34, 39, 41, 43, 45, 88(1st para), 104, 135(4th para); adds new provisions via Articles Two–Eleven of the amendment itself. |
| **Source** | https://www.lloc.gov.bh/FullEn/K1422.docx (LLOC identifier `K1422`) |
| **Retrieved** | 2026-08-02 |
| **Issued** | 18 April 2022, in force the day after Official Gazette publication (Gazette No. 3599) |

### Current contribution rates (old-age/disability/death branch — Article 33)

| Party | Target (fully phased-in) rate | Phase-in schedule (Article Four of the amendment) |
|---|---|---|
| **Employer** | **17%** of insured individuals' wages | Starts at **11%** upon the law's 2022 enforcement, **increases by 1 percentage point annually** until reaching 17%. Schedule (start of year, assuming annual step-up from April 2022 enforcement): 2022=11%, 2023=12%, 2024=13%, 2025=14%, **2026=15%** (current year per this session), 2027=16%, 2028=17%. |
| **Insured individual (employee)** | **7%** of monthly wage | Starts at **6%** upon enforcement, increases to the full 7% "at the beginning of the year following the entry into force of the law" — i.e. **7% from 2023 onward**, already fully phased in as of the current date. |

**⚠ Important caveat on the phase-in schedule**: the amendment text specifies
"increases annually by a rate of 1%" but does **not** state the exact
calendar trigger date (e.g., 1 January vs. the law's anniversary date) in
the portion read. The 2026=15% figure above is an inference from "annual
1% step starting from 11% in 2022" assuming calendar-year steps — **this
inference should be verified against SIO's own current published rate
(e.g., a current employer-facing rate card or FAQ) before being hardcoded**,
since getting the exact trigger date wrong would misstate the rate for part
of any given year. This is flagged as the concrete next step, not resolved
by this document alone.

### Scope — this branch is not Bahraini-exclusive by law text, but is now Bahraini-*de facto* since 2024

Article 2 of the base law states the Social Insurance Law applies
**"without discrimination as to sex, nationality, or age"** to all workers
under an employment contract — so Article 33's rates are not, by their own
text, restricted to Bahrainis. **However**, this same 2022 amendment
(Article Ten) separately establishes:

> "Non-Bahraini workers shall be subject to an end-of-service gratuity
> system, and a decision specifying the contribution rates, conditions and
> terms for calculating the end-of-service gratuity shall be issued by a
> decision from the Prime Minister..."

This is the **enabling provision** for what became **Decision No. (109) of
2023** (already fully sourced in `BAHRAIN_PAYROLL_SOURCES.md` §2a) —
effective **1 March 2024**. In other words:

- **Before this carve-out took effect**: non-Bahraini private-sector
  workers were covered under the *same* Article 33 old-age/disability/death
  branch as Bahrainis (both paying into the same pension scheme).
- **From 1 March 2024 onward**: non-Bahrainis are moved out of the Article
  33 pension branch and into the separate EOSB gratuity scheme (4.2%/8.4%,
  no employee share) instead.
- **As a practical matter today (2026)**: **Article 33's 17%/7%
  (currently ~15%/7%) rates apply to Bahraini private-sector employees.**
  This is the HIS-60 answer.

**This also directly answers HIS-63's pre/post-March-2024 question**: the
"legacy" pre-March-2024 liability for non-Bahraini workers is their
accrued entitlement under the **Article 33 old-age/disability/death
scheme** (the same scheme Bahrainis remain in), not a separate legacy
gratuity system — they were simply in the general pension scheme before
being carved out into EOSB. Whether/how that pre-2024 accrued pension
entitlement converts to or coexists with the new EOSB gratuity is **not
addressed in the text read so far** — flagged as the next concrete
question for HIS-63, not resolved by this document.

---

## 2. Employer-family coverage (2022 amendment, informational)

**Law No. (21) of 2022** (identifier `K2122`, same amendment list),
retrieved and parsed in full — adds a second paragraph to Article 2
extending coverage to "members of the employer's family who work with
him" (per Minister's conditions), and repeals Clause (9) of Article 3
Paragraph One (one of the exclusion categories — the specific repealed
clause's content was not independently re-extracted from the base law
text in this pass, flagged as a minor gap). Not directly a contribution-
rate change; noted for completeness since it's the other 2022 amendment
found alongside Law 14/2022.

---

## 3. Base-law exclusions (Article 3) — direct relevance to domestic workers

Decree-Law 24/1976 Article 3 excludes the following categories from SIO
coverage **entirely** (subject to Ministerial Order override):

1. Bahraini government employees on established posts (covered instead by
   the separate civil-service pension law).
2. Defense Force / Public Security members.
3. Certain public-institution employees excluded by other legal provisions.
4. Diplomatic-mission employees of the same nationality as the mission.
5. International-mission employees.
6. Sea-going vessel officers/engineers/crew.
7. **Domestic servants — but excluding chauffeurs, guards, liftmen,
   gardeners, and similar occupations** (i.e. those specific occupations
   *are* covered even within a domestic/household employment context).
8. Agricultural workers, with carve-back exceptions for processing/
   marketing agricultural establishments and mechanical-equipment
   operators/repairers.
9. Casual/temporary workers whose engagement is ≤3 months and not normally
   part of the employer's business.
10. Non-citizen workers on ≤12-month training delegations from a foreign
    parent company or branch.

**Direct answer to an open HIS-66/HIS-67 question**: general domestic
servants are excluded from SIO (and by extension, from the Article 33
pension branch and likely from EOSB — Decision 109/2023's own Article 3
exceptions already referenced "categories in Article 3 of the Law," which
is *this* article) — **but the specific occupations listed (chauffeur,
guard, liftman, gardener) are NOT excluded**, even when employed in a
household/domestic context. This is a meaningfully more precise answer
than the category matrix's prior "not yet independently confirmed" status
for domestic workers' SIO applicability — worth updating
`BAHRAIN_EMPLOYEE_CATEGORY_MATRIX.md` accordingly in a follow-up commit.

---

## 4. Still open — not resolved by this pass

- **Exact phase-in calendar trigger** for Article 33's employer rate
  (11%→17% over what is presumably 6 years) — needs a current SIO-published
  rate figure to confirm the 2026 value is actually 15% and not some other
  figure due to a different trigger-date convention.
- **Employment injury branch contribution rate** — the original 1976 text
  states 3% (employer-only), but given 19 amendments exist to this law,
  this rate has **not been independently re-verified as current** the way
  Article 33 now has been. Do not treat 3% as current without checking
  the amendment list for an Article-48-adjacent or injury-branch-specific
  amendment (note: Law 14/2022 Article Nine explicitly **repeals Article
  48** of the base law — Article 48 was the general contribution-percentage
  provision cross-referenced in the original text; its repeal likely
  affects how the injury/other-branch percentages are now set, but this
  was not traced further in this pass).
  **Operational note**: SIO's own FAQ page
  (https://www.sio.gov.bh/en/the-insured-within-the-kingdom-of-bahrain) has
  a "Work Injury Insurance" tab that would likely answer this directly, but
  its tab-switching JavaScript did not respond to a real click, a synthetic
  click, or a URL query parameter in this session — appears to be broken on
  SIO's own site (every other tab/modal interaction pattern used
  successfully elsewhere in this repo's research failed identically here).
  Worth retrying in a future pass in case it's a transient issue, or via
  the Arabic-language version of the page.
- **Unemployment insurance contribution rate** — Law 78/2006's full text is
  in `BAHRAIN_PAYROLL_SOURCES.md` §2a-ter, but the specific contribution
  percentage was not extracted in that pass; needs a targeted re-read. The
  same broken "Unemployment insurance and benefit" FAQ tab noted above was
  also attempted and failed the same way.
- **Sickness/maternity temporary-disability branch rate** — not yet located
  anywhere.
- **Wage cap/floor for contribution purposes** — not yet located; the
  amendment text references "wages" and "average monthly wages" repeatedly
  without a stated ceiling/floor figure in the sections read.
- **What happens to non-Bahrainis' pre-March-2024 accrued Article-33
  pension entitlement** post-carve-out — the structural relationship is now
  clear (see §1), but the actual disposition (converted to EOSB credit?
  frozen and paid out separately? forfeited?) is not stated in either Law
  14/2022 or Decision 109/2023 as read so far. **This is the single most
  important remaining question for HIS-63.**
- **The repealed Clause (9) of Article 3 Paragraph One** (via Law 21/2022) —
  its original content (what category it excluded) was not independently
  retrieved from the base law text in this pass.

---

## 5. Explicit rejection of AI-generated statutory numbers

Every figure in §1–§3 above is a direct quote or close paraphrase of text
read from official LLOC documents in this session (the base law `L2476`
and its amendments `K1422`/`K2122`), not recalled from training data. The
19-amendment count and the specific selection of Law 14/2022 as the
rate-setting amendment were confirmed by checking LLOC's own amendments
index for this law, following the same discipline that resolved the
Law 36/2012 contradiction in `BAHRAIN_EMPLOYMENT_LAW_SOURCES.md` §4. The
phase-in schedule inference in §1 is explicitly flagged as an inference,
not a verified figure — it must not be hardcoded without the follow-up
verification noted in §4.
