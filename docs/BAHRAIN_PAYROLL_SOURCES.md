# Bahrain payroll & labor-law official-source inventory

Research/verification deliverable for HIS-50. **No payroll calculation code is
added by this document or this ticket** — per the non-negotiable invariant in
`HR_ASSISTANT_DEFINITIVE_ARCHITECTURE_HANDOFF.md` §6.7, statutory
calculations must be deterministic code with official citations, never
LLM-derived, and this inventory exists to make that citation possible later.
Nothing in this file should be treated as a finished rule pack — it is the
sourcing layer a rule pack would be built and tested against.

## How to read this document

- **Verified this session**: a human-legible primary-source page was loaded
  in a real browser (not just an automated fetch — several of these portals
  block simple HTTP fetches with a 403/WAF response but are reachable through
  an interactive browser) and the cited text/figure was read directly off
  the page, quoted or closely paraphrased below.
- **Listed, not yet individually verified**: the requesting ticket named
  this law/decree as relevant. It has **not** been individually located and
  confirmed against LLOC or SIO's search tools in this session. Do not treat
  these as confirmed — they are a research backlog, not a citation.
- Every "Verified" row includes the retrieval date and the exact page URL so
  the citation can be re-checked as sources change.

---

## 1. Primary portals

| # | Portal | URL | Status | Language | Notes |
|---|---|---|---|---|---|
| 1 | Legislation & Legal Opinion Commission (LLOC) — legislation search | https://www.lloc.gov.bh/en/Legislation/Search | **Verified reachable** (browser; blocked via plain HTTP fetch) | EN/AR toggle | Advanced search UI confirmed: filters by legislation number, year, official gazette number, legislation type, issuing ministry/organization, and classification. This is the authoritative gazette-of-record search tool and should be the first stop for pinning exact legislation text. Keyword search execution (via on-page search box) did not return results within this session — likely requires using the structured number/year filters rather than the free-text box; flagged as follow-up. |
| 2 | SIO — advanced legislation search | https://www.sio.gov.bh/en/advanced-legislations-search | **Verified reachable and functional** | EN/AR toggle | Returned a live, paginated (46 pages) result set of SIO decisions/regulations when loaded. Confirms `Law No. 13 of 1975` is an actively cross-referenced SIO legislation number (see §2). |
| 3 | SIO official portal | https://www.sio.gov.bh | **Verified reachable** (browser; blocked via plain HTTP fetch) | EN/AR toggle | Homepage exposes Legislations, Reports & Statistics, Knowledge Center (FAQs), E-Services navigation. |
| 4 | LMRA official portal / legal library | https://lmra.gov.bh | **Verified reachable** | EN/AR toggle | |
| 5 | LMRA — WPS employer obligations | https://www.lmra.gov.bh/en/page/show/638 | **Verified reachable and read** (browser; blocked via plain HTTP fetch) | EN | See §3. |
| 6 | LMRA blog — Enhanced WPS announcement | https://blog.lmra.gov.bh/en/2025/10/21/lmra-launches-the-enhanced-wages-protection-system/ | **Verified reachable and read** (plain fetch succeeded) | EN | See §3. |
| 7 | BENEFIT — WPS 2.0 overview | https://benefit.bh/others/wps/Default | **Verified reachable and read** (browser; blocked via plain HTTP fetch) | EN | See §3. |

**Operational note for future automation against these portals**: LLOC, SIO,
and most LMRA pages return HTTP 403 to simple/automated HTTP clients (bot
protection), but render normally in a real browser session. Any future
scraping/ingestion pipeline for these sources needs a browser-rendering
fetch path, not a bare HTTP client.

---

## 2. Verified citations — SIO / end-of-service and social insurance

| Field | Value |
|---|---|
| **Rule family** | End-of-service gratuity — non-Bahraini private-sector employees |
| **Title** | Decision No. (109) of 2023 Promulgating the Regulation of End of Service Remuneration for Non-Bahrainis Working in the Private Sector |
| **Document number** | Decision No. (109) of 2023 |
| **Issuing body** | Social Insurance Organization (SIO), Bahrain |
| **Source URL (EN)** | https://www.sio.gov.bh/en/end-of-service-benefits |
| **Source URL (AR)** | https://www.sio.gov.bh/ar/end-of-service-benefits |
| **Language priority** | Arabic original is authoritative; the English page is a reference/translation. Full Arabic gazette text of Decision 109/2023 itself was **not** located within this session (the SIO page names the decision but does not link its full text/PDF inline) — flagged as follow-up. |
| **Page last updated (per site)** | 23 Jul 2026 |
| **Retrieved** | 2026-08-01 |
| **Legal priority** | High — this is the specific instrument the EN summary page cites as its basis. |
| **Status** | Decision identified and named from an official source; full legal text not yet retrieved. **Partially verified.** |

| Field | Value |
|---|---|
| **Rule family** | End-of-service gratuity — employer monthly contribution rate (non-Bahraini) |
| **Verified figure** | "The employer is obligated to pay a monthly subscription equal to **4.2%** of the employee's monthly wages for each of the first three years of service, and **8.4%** of the employee's monthly wages for subsequent years until the end of employment." |
| **Source** | SIO FAQ — "End Of Service Gratuity for non-Bahrainis" |
| **Source URL** | https://www.sio.gov.bh/en/end-of-service-gratuity-for-non-bahrainis |
| **Issuing body** | Social Insurance Organization (SIO), Bahrain |
| **Language** | English (FAQ page); Arabic original at `https://www.sio.gov.bh/ar/end-of-service-gratuity-for-non-bahrainis` not independently re-read in this session |
| **Retrieved** | 2026-08-01 |
| **Legal priority** | Medium-high — official FAQ, not the gazette text itself. Should be cross-checked against Decision 109/2023's actual text before being used as a rule-pack parameter. |
| **Status** | **Verified against official FAQ page**, quoted verbatim above. Not yet cross-checked against the underlying gazette decision text. |

| Field | Value |
|---|---|
| **Rule family** | End-of-service gratuity — calculation formula (non-Bahraini) |
| **Verified figure** | "End of service gratuity is calculated on the basis of the basic salary in addition to social allowance, if any, as **15 days' salary for each year** of the first three years of service, and **one month salary for each year of service thereafter**." |
| **Source** | Same SIO FAQ as above |
| **Source URL** | https://www.sio.gov.bh/en/end-of-service-gratuity-for-non-bahrainis |
| **Retrieved** | 2026-08-01 |
| **Legal priority** | Medium-high — same caveat as above (FAQ paraphrase, not gazette text). |
| **Status** | **Verified against official FAQ page**, quoted verbatim above. |

| Field | Value |
|---|---|
| **Rule family** | End-of-service gratuity — scope of coverage |
| **Verified statement** | "This system applies to all expatriate employees in the private sector covered by the provisions of the insurance against employment injuries branch of the Social Insurance Law." |
| **Source URL** | https://www.sio.gov.bh/en/end-of-service-gratuity-for-non-bahrainis |
| **Retrieved** | 2026-08-01 |
| **Status** | **Verified**, quoted verbatim. Note: this FAQ answer itself references "the Social Insurance Law" by name without a decree number on this page — ties back to Decree-Law No. (24) of 1976 per the ticket's brief, but that linkage was **not independently confirmed** in this session (see §4). |

| Field | Value |
|---|---|
| **Rule family** | Social insurance legislation cross-reference |
| **Verified statement** | SIO's own advanced legislation search returned a live result directly citing **"Law No. 13 of 1975"** (in the context of a 1986 decision on transferring reserves of government employees) — confirming this law number is real and actively cross-referenced by SIO, consistent with the ticket's identification of it as the pensions/retirement-benefits law for civil servants. |
| **Source URL** | https://www.sio.gov.bh/en/advanced-legislations-search |
| **Retrieved** | 2026-08-01 |
| **Status** | **Existence and active use confirmed**; full text of Law No. (13) of 1975 itself not retrieved in this session. |

---

## 3. Verified citations — LMRA / Wages Protection System (WPS)

| Field | Value |
|---|---|
| **Rule family** | WPS — employer obligations (base system) |
| **Title** | Employer Responsibilities and Obligations in the Wages Protection System (WPS) |
| **Issuing body** | Labour Market Regulatory Authority (LMRA), Bahrain |
| **Source URL** | https://www.lmra.gov.bh/en/page/show/638 |
| **Page last updated (per site)** | 21-01-2026 |
| **Retrieved** | 2026-08-01 |
| **Key verified obligations (quoted/paraphrased)** | Employer must assign a "Wage Responsible Person" (WRP) who processes/reviews payroll files; must create/update worker profiles in WPS; register company bank account or digital wallet; maintain employee salary/bank details; upload and confirm the Salary File (XLS format); "Ensure wages are paid on time, in accordance with the **Labour Law in the Private Sector (Law No. 36 of 2012)**, using payment methods licensed by the Central Bank of Bahrain (CBB)." |
| **Legal cross-reference confirmed** | **Law No. (36) of 2012** — explicitly named by LMRA itself as the legal basis for on-time wage payment, confirming the ticket's identification of this as the Private Sector Labour Law. |
| **Status** | **Verified**, primary source read directly. |

| Field | Value |
|---|---|
| **Rule family** | WPS 2.0 — enhanced system rollout |
| **Title** | LMRA Launches the Enhanced Wages Protection System |
| **Issuing body** | LMRA |
| **Source URL** | https://blog.lmra.gov.bh/en/2025/10/21/lmra-launches-the-enhanced-wages-protection-system/ |
| **Publish date** | 2025-10-21 |
| **Retrieved** | 2026-08-01 |
| **Key verified points** | Electronic wage payment through approved bank/financial-institution accounts; integration with Bahrain's Electronic Network for Financial Transactions (BENEFIT); pilot phase completed with select banks; **full-scale implementation targeted for Q1 2026**. No specific law/decree number is cited in this announcement itself. |
| **Status** | **Verified**, primary source read directly. |

| Field | Value |
|---|---|
| **Rule family** | WPS 2.0 — technical operator / rollout confirmation |
| **Title** | Wage Protection System (WPS) 2.0 |
| **Issuing/operating body** | BENEFIT (Bahrain's national electronic financial transactions network), in collaboration with LMRA and the Central Bank of Bahrain (CBB) |
| **Source URL** | https://benefit.bh/others/wps/Default |
| **Retrieved** | 2026-08-01 |
| **Key verified points** | "Effective **January 2026**, WPS 2.0 introduces a series of mandatory enhancements for all private sector employers in Bahrain": mandatory participation, monthly payroll file submission, Wage Responsible Person (WRP), centralized salary processing, bank/PSP integration, compliance monitoring. Salary transfers operate via "Fawri Salary Transfers." This **corroborates** the LMRA blog's "Q1 2026" full-scale-implementation date with a specific month (January 2026). |
| **Status** | **Verified**, primary source read directly. Corroborates LMRA blog date. |

---

## 4. Listed by the ticket, **not yet individually verified** this session

These are named in HIS-50's brief as core legislation to collect. None of
them were individually located and confirmed against LLOC or SIO's search
tools in this session — they are recorded here as the research backlog, not
as confirmed citations. **Do not use any of these as a rule-pack parameter
source until independently verified.**

### SIO / social insurance

| Legislation | Ticket's description | Verification status |
|---|---|---|
| Decree-Law No. (24) of 1976 | Social Insurance Law / private sector | Not yet located via LLOC/SIO search this session. The SIO EOSB FAQ references "the Social Insurance Law" by name without a decree number on that page (§2), consistent with but not confirming this specific decree number. |
| Law No. (13) of 1975 | Pensions and retirement benefits, civil servants / public sector | **Existence confirmed** via SIO search result (§2); full text not retrieved. |
| Law No. (78) of 2006 | Insurance Against Unemployment | Not yet located this session. |
| Decree-Law No. (21) of 2020 and amendments | Pension/social insurance unification | Not yet located this session. |
| 2023–2024 expatriate EOSB decrees/decisions | SIO-managed non-Bahraini EOSB | Decision No. (109) of 2023 identified (§2) as the specific instrument named on SIO's own EOSB page; other 2023-2024 decrees/decisions not enumerated this session. |
| SIO employer directives — monthly wage reporting/contribution shares | — | Not yet located this session; likely reachable via SIO E-Services/employer guides, not yet browsed. |

### LMRA / labour legislation

| Legislation | Ticket's description | Verification status |
|---|---|---|
| Law No. (19) of 2006 | Labour Market Regulation / LMRA founding law | Not yet located this session. |
| Law No. (36) of 2012 | Labour Law for the Private Sector | **Confirmed** — directly cited by LMRA's own WPS obligations page (§3). |
| Legislative Decree No. (16) of 2021 | Amendment | Not yet located this session. |
| LMRA Board Resolution No. (1) of 2022 | Work permits | Not yet located this session. |
| LMRA Board Resolution No. (2) of 2014 | Domestic workers | Not yet located this session. |
| Flexible work permits / worker mobility / quota-ceiling regulations | — | Not yet located this session. |

### Supplementary operational guidance (not legal text)

Not yet retrieved this session: LMRA employer/employee manuals and FAQs,
visa/work-permit issuance guidance, medical check guidance, employer
ceiling/quota guidance, the WPS User Manual PDF (referenced by name — "Wage
Protection System (WPS) User Manual PDF (4 MB)" — on the LMRA obligations
page in §3, but not opened), and SIO employer contribution-calculation
guides.

---

## 5. Explicit non-findings and blockers

- **LLOC keyword search**: the free-text search box on
  `lloc.gov.bh/en/Legislation/Search` did not return visible results within
  this session when a keyword ("Social Insurance Law") was entered and
  submitted via Enter. The page's structured filters (legislation
  number/year, gazette number, type, ministry) are present and are the more
  likely reliable path — e.g. searching number=`24`, year=`1976` directly —
  but that path was not completed this session. **Follow-up required**
  before Decree-Law No. (24) of 1976 can be marked verified.
- **Decision No. (109) of 2023 full text**: named and its title quoted
  exactly from SIO's official EOSB page, but the actual gazette/decision PDF
  or full text was not located/opened this session.
- **Automated (non-browser) fetch is blocked** on `sio.gov.bh`,
  `lmra.gov.bh`, `lloc.gov.bh`, and `benefit.bh` (HTTP 403 from bot
  protection). All content in this document was retrieved via an
  interactive browser session, not a bare HTTP client. Any future automated
  ingestion pipeline for these sources must render via a real browser.

---

## 6. Explicit rejection of AI-generated statutory numbers

Per HIS-50's acceptance criteria and the architecture handoff's invariant
that payroll/compliance calculations must be deterministic and
citation-backed, not LLM-derived: **every numeric figure in §2 and §3 above
is a direct quote or close paraphrase of text read from the cited official
page in this session**, not a figure recalled from training data. Any
statutory number needed for a future rule pack that is *not* backed by a row
in §2 or §3 must be treated as unverified and blocked — see §4 — until
independently sourced the same way.

## 7. Suitability for downstream use

Per the ticket's acceptance criteria ("output is suitable for later
ingestion into the AI knowledge base and deterministic rule-pack tests"):
this document's §2 and §3 tables are structured with a stable field set
(rule family, title/document number, issuing body, source URL, language,
retrieved date, status) suitable for direct ingestion as retrieval-indexed
policy documents or as fixture data for future rule-pack unit tests. No
payroll calculation logic, parameter defaults, or code changes are
introduced by this document.
