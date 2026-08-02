# Tamkeen (Bahrain Labour Fund) — statutory role and employer-facing programs

Research addendum, triggered by the HIS-61 finding that Tamkeen pays the
private-sector employer's unemployment-insurance contribution share
(Law 78/2006 Article 6). **No calculation code is added by this
document.** This covers two distinct things that both matter for a
Bahrain-first HRMS: Tamkeen's **statutory funding role** (a legal
obligation already sourced) and its **employer-facing support programs**
(voluntary applications that affect effective payroll cost, not statutory
obligations).

---

## 1. Statutory role — confirmed, not new research

Tamkeen ("Labour Fund") is the entity Law No. (78) of 2006 (Insurance
Against Unemployment) designates to pay the **private-sector employer's
1% unemployment-insurance share** on the employer's behalf — see
`docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md` §1, sourced from the law's
Article 6: *"The Labour Fund shall pay the employers' share for the
insureds employed in the private sector."* This applies to Bahraini and
non-Bahraini private-sector employees identically (the branch's scope is
nationality-neutral).

**Product implication**: if a payroll rule pack ever models total
employer cost, the unemployment-insurance employer share must **not** be
charged to the employer directly for private-sector employees — it's
funded by Tamkeen. Getting this wrong would overstate employer payroll
cost by 1% of wages across the entire private-sector workforce.

Tamkeen's own website (tamkeen.bh, checked this session) does not restate
this specific statutory funding mechanism in its general marketing/about
pages — expected, since it's a narrow legal funding arrangement rather
than an employer-facing "program" Tamkeen promotes. **The Law 78/2006
Article 6 text remains the authoritative citation for this**, not a
Tamkeen page.

---

## 2. Employer-facing support programs (voluntary, not statutory obligations)

These are **not** legal requirements — employers/employees apply and are
approved case-by-case. They matter for a Bahrain HRMS because they affect
**effective payroll cost** for enterprises that participate, and a
product serving Bahraini employers should plausibly be aware of them even
though they're not deterministic statutory rules the way SIO/WPS/EOSB
figures are.

### National Employment Program (NEP 3.0)

| Field | Value |
|---|---|
| **Purpose** | Wage-cost subsidy to incentivize private-sector enterprises to hire Bahraini nationals. |
| **Duration** | Up to 5 years, employer chooses one of three support-tier options. |
| **Support tiers** | (a) 3 years: 70% wage support year 1, 50% year 2, 30% year 3; (b) 3 years: flat 50% all years; (c) 5 years: flat 30% all years. **Engineers track**: flat 40% for 5 years. **People with Determination (disability) track**: +10% additional support annually. |
| **Minimum wage thresholds (by education)** | High school: BHD 350+; Diploma: BHD 430+; Bachelor's+: BHD 500+ (Actuaries track: BHD 500+; Doctors track: BHD 800+; Engineers track: BHD 500+). |
| **Employee eligibility** | Bahraini national; registered in SIO under the hiring company; not a business owner/CR holder; not a 1st/2nd-degree relative of the enterprise owner; open-ended contract; fresh graduate (≤24 months experience) or Ministry-nominated jobseeker/Jobs+ participant. |
| **Enterprise eligibility** | Active CR from MOIC or relevant regulator; no outstanding violations with Tamkeen/LMRA/other government entities; not an outsourcing enterprise applying for seconded employees. |
| **Application window** | Within 6 months of the employee's joining date. |
| **Re-enrollment** | An individual can be enrolled twice, only with a different enterprise (different CR, different owner). |
| **Source** | https://www.tamkeen.bh/en/programs/national-employment-program-3-0/ |
| **Retrieved** | 2026-08-02 |

### Wage Increment Program (Updated)

| Field | Value |
|---|---|
| **Purpose** | Subsidizes basic-wage increases for existing Bahraini employees to support retention/career progression. |
| **Duration** | 12 months. |
| **Support level** | Tamkeen funds **100%** of the wage increment (up to approved/supported amounts) for 12 months. |
| **Increment bounds** | Minimum 5%, maximum 20% of basic salary; the increment amount itself must be between **BHD 30 and BHD 300**. Allowances/bonuses are explicitly excluded — must be reflected in basic salary only. |
| **Enterprise eligibility** | Must be classified Small/Medium/Micro per MOIC's definition; active CR/license; no outstanding violations with Tamkeen/LMRA/SIO/other government entities. |
| **Employee eligibility** | Bahraini national; age 18–45 at application; ≥3 months' tenure with the same enterprise; not a 1st/2nd-degree relative of the owner; registered in SIO under the same company in a matching role. |
| **Minimum wage thresholds (by education)** | High school: BHD 300+; Diploma: BHD 380+; Bachelor's+: BHD 450+. Basic wage must be BHD 200–1,500 at application regardless of education tier — wages between BHD 200 and the education-tier minimum are not auto-rejected, they get individual assessment. Part-time employees eligible at BHD 200 minimum. Doctors/dentists are exempt from the 20%/BHD 300 caps if a higher increase is warranted (detail truncated in this pass — not fully captured). |
| **Source** | https://www.tamkeen.bh/en/programs/wage-inc/ |
| **Retrieved** | 2026-08-02 |

### Other programs identified but not researched this pass

Found via Tamkeen's site navigation, not opened: Apprenticeship Program,
Freelance support, Furas (employment-matching?), Qiyada, Tamakkan, AI
Training, Medical Fellowship, Hospital Residency, Nursing Specializations/
Bachelor's, Digital Enablement, Riyada (business accelerator), Business
Franchising, SME Fund, Tamweel, Musanada. Most of these appear to be
**enterprise growth/training programs, not payroll-cost-affecting wage
subsidies** — lower priority for an HRMS payroll module, but flagged for
completeness in case any of them turn out to be wage-relevant on closer
inspection.

---

## 3. Product implications for a Bahrain HRMS

- **The statutory unemployment-insurance funding role (§1) should be
  encoded as a rule** if/when an employer-total-cost calculation is built
  — this is a real correction to what a naive reading of Law 78/2006 alone
  would suggest (naive reading: employer pays 1%; actual: Tamkeen pays it
  for private-sector employers).
- **The two support programs (§2) are optional/voluntary and
  employer-initiated** — they should not be modeled as automatic payroll
  deductions or additions the way SIO/WPS/EOSB rules are. If the product
  ever surfaces "potential savings" or "eligible programs" to an employer,
  these would be the two most payroll-relevant ones found so far, but that
  is a distinct product feature from deterministic statutory payroll
  calculation, and should not be conflated with the citation-integrity
  discipline (HIS-57) that governs actual statutory numbers.
- **Minimum wage figures in both programs (BHD 200–800 depending on
  program/education tier) are Tamkeen program eligibility thresholds, not
  a general Bahrain statutory minimum wage** — Bahrain does not have a
  general statutory minimum wage in the private sector as far as sourced
  in this repo so far (not independently confirmed one way or the other
  in this pass; flagged as a distinct open question, do not assume these
  figures answer it).

---

## 4. Explicit rejection of AI-generated statutory numbers

The statutory funding role in §1 is a re-citation of Law 78/2006 Article 6
(already sourced in `BAHRAIN_NON_BAHRAINI_SIO_RATES.md`), not new
figures. The program details in §2 are direct quotes/close paraphrases
from Tamkeen's own official program pages, retrieved this session — not
recalled from training data. These program terms are worth periodically
re-checking since Tamkeen programs are known to change more frequently
than primary legislation (this is "Wage Increment Program **(Updated)**"
per its own page title, implying at least one prior version existed).
