# Bahrain employment-law official-source inventory

Research/verification deliverable for **HIS-65** (private-sector labor-law
entitlements), cross-referencing **HIS-66** (LMRA employment-operations) and
**HIS-67** (employee-category matrix). **No entitlement/payroll calculation
code is added by this document.**

**Relationship to `docs/BAHRAIN_PAYROLL_SOURCES.md`**: that document already
covers SIO (social insurance, EOSB, wage-reporting), LMRA fees, WPS, and the
domestic-worker work-permit regulation (Order 4/2014) in full-text detail —
this document does **not** duplicate that content. It focuses on the
**Labour Law for the Private Sector (Law 36/2012)** entitlement provisions
(leave, hours, termination, wages) that were the actual gap identified in the
scope audit. Where SIO/LMRA/WPS content is relevant, this doc links to the
specific section of `BAHRAIN_PAYROLL_SOURCES.md` rather than re-stating it.

**Source discipline** (per the standing rule across all Bahrain research in
this repo): official government sources only — LLOC, SIO, LMRA, BENEFIT.
Never law-firm blogs, HR blogs, accounting summaries, or LLM training data
for statutory facts. Arabic Official Gazette text is authoritative; English
is a reference translation unless stated otherwise by the issuing body.

**Pass status**: this is **Pass 1** of what will likely be a multi-pass
effort (following the pattern established on HIS-50, which took six passes
to reach practical completeness). Pass 1 covers the core individual-contract
entitlement provisions of Law 36/2012 in full — probation, hours/overtime,
weekly rest, annual/sick/maternity/other leave, public holidays, wage
payment/deduction rules, and termination/notice/unfair-dismissal/legacy
gratuity. **Not yet covered in this pass**: juveniles (Part Four),
apprenticeship (Part Two), disciplinary-penalty detail (Part Ten),
employment-injury compensation detail (Part Eleven, distinct from the SIO
work-injury branch already covered in the payroll doc), individual labour
disputes procedure (Part Thirteen), collective labour relations (Part
Fourteen), labour inspection (Part Sixteen), and criminal penalties (Part
Seventeen). These are flagged as open in §5 and §6 (readiness) rather than
silently omitted.

---

## 1. Primary source for this pass

| Field | Value |
|---|---|
| **Title** | Law No. 36 of 2012 Promulgating the Labour Law for the Private Sector |
| **Full text** | **Downloaded and parsed in full — 52 pages, ~117,000 characters**, structured as 17 Parts (Definitions, Apprenticeship, Individual Contract, Juveniles, Employment of Women, Wages, Hours of Work & Rest, Holidays, Regulation of Work, Workers' Duties & Penalties, Employment Injuries, Termination, Individual Labour Disputes, Collective Labour Relations, [Part Fifteen — Occupational Safety, not separately fetched], Labour Inspection, Penalties). |
| **Source** | https://www.lmra.gov.bh/files/cms/shared/file/labour%20law.pdf (same URL already recorded in `BAHRAIN_PAYROLL_SOURCES.md` §2c, but that pass only quoted the preamble; this pass reads the substantive articles) |
| **Language / authority statement** | English (LMRA's own translation). The PDF carries LMRA's own footnote: **"This is unofficial translation, in case of difference between the Arabic and the English text, the Arabic text shall prevail."** — same Arabic-primacy statement already recorded in the payroll doc. |
| **Retrieved** | 2026-08-02 |
| **⚠ Version-currency concern (see §4)** | This PDF's content for Articles 30, 31, and 39 does **not** reflect the amendments made by Legislative Decree No. (16) of 2021 (confirmed full-text in `BAHRAIN_PAYROLL_SOURCES.md` §2a-ter), even though the LMRA page shows a "Last Update: 14-10-2025" date. Flagged, not resolved — see §4. |

---

## 2. Verified citations — individual contract, hours, and rest (Parts Three, Seven)

| Rule area | Verified figure/rule (quoted/paraphrased) | Article |
|---|---|---|
| **Probation** | Max 3 months; extendable to max 6 months for Minister-designated occupations; must be expressly stated in the contract; either party may terminate with **1 day's notice**; a worker may not be put on probation more than once by the same employer. | Art. 21 |
| **Contract form** | Must be in writing, in Arabic (bilingual if drawn up in another language); worker may prove rights by any evidence if no written contract exists. | Art. 19 |
| **Contract type — indefinite by default** | A contract is deemed indefinite if: no duration specified; duration >5 years; original+renewed duration >5 years; parties continue performance past expiry without express renewal (same rule for "specific work" contracts). | Art. 98 |
| **Standard working week** | Max **48 hours/week** actual work. | Art. 51(a) |
| **Ramadan hours (Muslim workers)** | Max **6 hours/day or 36 hours/week**. | Art. 51(b) |
| **Daily hours cap** | Max **8 hours/day** standard, up to **10 hours/day** by agreement; total attendance span (start to end including breaks) capped at **11 hours/day** (12 hours for Minister-designated intermittent-work jobs). | Art. 53 |
| **Rest breaks** | At least 30 minutes total per period so no continuous work exceeds 6 hours; break time not counted as working hours (unless Minister designates otherwise for hard/exhausting jobs). | Art. 52 |
| **Overtime pay** | Minimum **+25%** of wage for daytime extra hours, minimum **+50%** for nighttime extra hours. | Art. 54 |
| **Weekly rest day** | At least **24 consecutive hours**; **Friday** is the default weekly rest day (employer may move it for some workers, subject to Friday prayer time); if worked, worker gets wage + **150% overtime pay** OR a substitute day off (worker's choice); may not be required to work >2 consecutive weekly rest days without written consent. | Art. 57 |
| **Exemptions from hours/rest provisions** | Employer's authorized agents; workers on preparatory/supplementary jobs bookending official hours; security guards and cleaners (Minister sets their max hours/overtime rate separately, not below Art. 54's rate). | Art. 56 |

---

## 3. Verified citations — leave entitlements (Parts Five, Eight)

| Leave type | Verified figure/rule (quoted/paraphrased) | Article |
|---|---|---|
| **Annual leave** | **30 days/year full pay** after 1 year of service, accruing at **2.5 days/month**; pro-rated for <1 year service; **not waivable** (only cash-in-lieu per Art. 59(b)); employer schedules dates by business need but worker must get ≥15 days including ≥6 consecutive days; employer must settle leave balance/wages **at least every 2 years**. | Art. 58–59 |
| **Contingency (personal) leave** | Up to **6 days/year**, max **2 days per instance**, deducted from annual leave balance. | Art. 59(b) |
| **Sick leave** (after 3 continuous months of service, medically certified) | **15 days full pay + 20 days half pay + 20 days unpaid**, per year; accumulation of full/half-pay portion capped at **240 days**. | Art. 65 |
| **Maternity leave** | **60 days full pay** (covering pre/post confinement) + optional **15 days unpaid** extension; work **prohibited for 40 days post-confinement**; dismissal/termination during maternity leave or due to marriage is **prohibited** (Art. 33) and is itself grounds for unfair-dismissal compensation (Art. 104(a)(1)). | Art. 32–33 |
| **Breastfeeding breaks** | Two ≥1-hour breaks/day until child is 6 months old, then two 30-minute breaks/day until child turns 1 — counted as working hours, no wage reduction. | Art. 35 |
| **Unpaid childcare leave** | Up to **6 months per instance**, max **3 times** during service, for a child ≤6 years old. | Art. 34 |
| **Marriage leave** | **3 days full pay**, once. | Art. 63(a)(1) |
| **Bereavement leave** | **3 days full pay** for spouse or relatives to 4th degree (own side) / 2nd degree (spouse's side). | Art. 63(a)(2–3) |
| **Paternity/birth leave** | **1 day full pay** on birth of a child. (No separate "paternity leave" article beyond this — this is the closest equivalent; do not assume a longer entitlement without further sourcing.) | Art. 63(b) |
| **Iddah leave (Muslim widow)** | **1 month full pay**, plus completion of the 3-month-10-day Iddah period from annual leave balance, or unpaid if no balance remains. | Art. 63(c) |
| **Hajj (pilgrimage) leave** | **14 working days full pay**, once per service lifetime (unless already taken with a prior employer), after **5 continuous years** of service with the same employer; employer allocates slots by business need, priority to longest-serving. | Art. 67 |
| **Public holidays** | Full pay on Eid/official occasions (set by Council of Ministers Edict — the specific list/dates are **not captured in this pass**, flagged as a gap); if worked, **150% pay** or substitute day off (worker's choice); if a holiday falls on Friday or another public holiday, worker gets a substitute day. | Art. 64 |
| **Examination leave** | Worker may schedule annual leave around exams with 30 days' prior notice to employer. | Art. 61 |
| **Juvenile annual leave** | Not divisible, reducible, or interruptible (juvenile-specific protection). | Art. 60 |

---

## 4. ⚠ Flagged contradiction — Articles 30–31 and Article 39 do not reflect Decree 16/2021

**Do not silently resolve this — flagging per explicit instruction.**

`BAHRAIN_PAYROLL_SOURCES.md` §2a-ter (sixth research pass, HIS-50) retrieved
the **full official text of Legislative Decree No. (16) of 2021** directly
from LLOC, which states:

> Article One: A second paragraph is added to Article (39) of the Labour
> Law... "discrimination in wages between male and female workers in work
> of equal value is prohibited."
> Article Two: Articles (30) and (31) of the Labour Law... shall be
> repealed.

This pass's read of the **current LMRA-hosted "consolidated" PDF**
(`labour law.pdf`, page metadata "Last Update: 14-10-2025") shows:

- **Article 39** with only its *original* single paragraph ("It shall be
  prohibited to discriminate in the payment of wages on the basis of sex,
  ethnic origin, language, religion or belief.") — **no second paragraph
  about "work of equal value" is present.**
- **Articles 30 and 31** present with substantive content (Ministerial
  resolutions on night-work restrictions and prohibited occupations for
  women respectively) — **not repealed/removed/blank as Decree 16/2021
  states they should be.**

**Possible explanations, none confirmed**:
1. The LMRA PDF is a stale consolidation that has not been updated to
   reflect the 2021 amendment, despite its displayed "Last Update" date
   (which may refer to page/metadata update, not legal-text currency).
2. The Articles 30/31 repealed in 2021 were later re-populated by a
   subsequent, not-yet-located amendment (legislatively unusual but not
   impossible — article numbers can be reused).
3. Some other reconciliation exists between the two texts that neither
   document explains.

**Recommendation**: do not treat the LMRA PDF as automatically
amendment-current. Before encoding **any** Article 39-adjacent
(wage-discrimination) or Article 30/31-adjacent (women's night-work /
occupation-restriction) rule, a human should cross-check the actual
Official Gazette Arabic text via LLOC directly (not LMRA's translation) for
the current, amendment-integrated wording. **Flagged for human legal
review — not resolved by this document.**

---

## 5. Verified citations — wages and termination (Parts Six, Twelve)

| Rule area | Verified figure/rule (quoted/paraphrased) | Article |
|---|---|---|
| **Wage payment timing** | Monthly-rate workers: paid **at least once a month**. All workers: paid **at least once a week** unless otherwise agreed (except production-basis work >2 weeks, which gets weekly payments on account). Final settlement: **immediate** if employer-initiated termination; **within 7 days** if the worker resigns. | Art. 40(b) |
| **Late-payment penalty** | **6% per annum** for delays up to 6 months, **+1%/month** thereafter, capped at **12% per annum**. | Art. 40(c) |
| **Wage-discrimination prohibition** | Original text: prohibited on basis of sex, ethnic origin, language, religion, belief. **Per §4 above, an equal-value-work amendment via Decree 16/2021 is not reflected in the current LMRA PDF — flagged, not resolved.** | Art. 39 |
| **Notice period** | **30 days minimum**, either party, in writing; may be extended by agreement if employer-initiated; payment in lieu of notice = wage for the notice period; if employer-initiated, notice period counts toward service; worker gets 1 day/week (or 8 hrs/week) paid job-search leave during employer-given notice. | Art. 99–100 |
| **Termination during leave** | Employer **may not terminate** during any worker leave; notice given during leave only takes effect the day after leave ends. | Art. 102 |
| **Unfair dismissal grounds** | Sex/color/religion/belief/social status/family responsibility/pregnancy/childbirth/breastfeeding; trade-union membership or activity; filing a (non-vexatious) complaint/case against employer; exercising a leave right; wage attachment placed on the worker. Court may order **reinstatement** for union-related dismissals specifically. | Art. 104 |
| **Worker-initiated termination without notice** | Permitted for employer assault/insult (words or deeds) against worker, or immoral conduct against worker/family — and this itself counts as *unjustified dismissal by the employer* for compensation purposes. | Art. 105 |
| **Employer-initiated termination without notice/compensation ("for cause")** | 11 enumerated grounds: false identity/certificates; fault causing material financial loss (must report within 2 working days); safety-instruction non-compliance after written warning; unauthorized absence >20 intermittent days or >10 consecutive days/year (with prior written warnings at 10 and 5 days respectively); failure of essential duties; unauthorized disclosure of work secrets; final conviction for a morals/dishonesty crime; on-duty intoxication or immoral act at work; assault on employer/supervisor; unlawful strike-participation; loss of qualification/permit needed for the job. | Art. 107 |
| **Termination compensation (indefinite contract, no cause)** | **First 3 months**: no compensation unless unfair dismissal (then 1 month's wage). **After 3 months**: **2 days' wages per month of service**, minimum **1 month's wages**, maximum **12 months' wages**. | Art. 111(a)–(b) |
| **Termination compensation (definite/specific-work contract, no cause)** | Wages for the remaining contract/work period, unless a lesser amount is agreed — but never less than **3 months' wages** or the remaining period, whichever is less. | Art. 111(c)–(d) |
| **Unfair-dismissal uplift** | **+50%** of the base compensation above (Art. 104/105 cases), unless the contract specifies a higher amount. | Art. 111(e) |
| **Redundancy/closure termination** | Requires 30 days' notice to the Ministry before notifying the worker; Bahraini workers with equal competence/experience to a foreign worker in the same role should not be the one let go (2015-amended provision, per the PDF's own footnote); worker gets a bonus = **half of the Art. 111 compensation**. | Art. 110 |
| **Death in service** | Contract terminates; if worker had ≥1 year of service, employer pays family **2 months' wages**. | Art. 113(a) |
| **Retirement age termination** | Employer may terminate without compensation at age **60**, unless otherwise agreed. | Art. 115 |
| **Illness-based termination restriction** | Employer may not terminate for illness until the worker exhausts annual + sick leave; must give **15 days' notice** before that exhaustion date; barred from terminating if the worker recovers first. | Art. 117 |
| **⚠ Legacy (non-SIO) leaving indemnity — important distinction** | **Article 116**: workers **NOT subject to the Social Insurance Law** are entitled to a Labour-Law-based leaving indemnity of **half a month's wage per year for the first 3 years, one month's wage per year thereafter** — this is the **same formula wording** ("half a month's wage") already confirmed for the SIO-administered non-Bahraini EOSB scheme in Decision 109/2023 (`BAHRAIN_PAYROLL_SOURCES.md` §2a). **This is a second, independent statutory source using the identical "half a month's wage" phrasing** — relevant corroborating evidence for the wage÷2 interpretation already decided on HIS-54, though this Article 116 scheme applies to a different population (workers outside the Social Insurance Law) and should not be conflated with the SIO/EOSB scheme without confirming which workers this actually covers today. |

---

## 6. Open items / not yet covered in this pass

- **Public holiday calendar itself** (the actual Council of Ministers Edict listing Eid/official dates) — Article 64 references it but the instrument itself was not located this pass.
- **Part Two (Apprenticeship)**, **Part Four (Juveniles)** beyond the one leave-related cross-reference in §3, **Part Nine (Regulation of Work)**, **Part Ten (Workers' Duties and Penalties — disciplinary detail)**, **Part Eleven (Employment Injury compensation under the Labour Law itself, as distinct from the SIO work-injury branch)**, **Part Thirteen (Individual Labour Disputes procedure)**, **Part Fourteen (Collective Labour Relations)**, **Part Sixteen (Labour Inspection)**, **Part Seventeen (Penalties)** — none opened in this pass.
- **Whether Article 116's "leaving indemnity" population (workers not subject to the Social Insurance Law) is a live, non-empty category today** — needs cross-referencing against the Social Insurance Law's actual coverage scope (Decree-Law 24/1976, already fully retrieved in `BAHRAIN_PAYROLL_SOURCES.md` §2a) to determine who, if anyone, this Article 116 provision still applies to in practice.
- **Domestic workers' relationship to Law 36/2012** — this pass did not confirm whether/how domestic workers are covered or excluded from the Labour Law itself (separate from the LMRA work-permit regulation already covered in the payroll doc). Flagged for HIS-66/§5 domestic-worker research.
- **GCC nationals** — Law 36/2012 itself does not appear (in the parts read) to carve out GCC nationals specially; their distinct treatment is expected to come from the SIO/social-insurance side (Law 68/2006, still blocked per `BAHRAIN_PAYROLL_SOURCES.md` §5) rather than the Labour Law. Not independently confirmed this pass.

---

## 7. Explicit rejection of AI-generated statutory numbers

Every figure in §2, §3, and §5 above is a direct quote or close paraphrase
of text read from the official LMRA-hosted PDF of Law 36/2012 in this
session — not a number recalled from training data. The §4 contradiction is
flagged precisely because it was caught by comparing two independently
retrieved official sources, not by trusting either one uncritically. Any
statutory number needed for a future rule pack that is not backed by a row
in this document (or in `BAHRAIN_PAYROLL_SOURCES.md`) must be treated as
unverified and blocked.
