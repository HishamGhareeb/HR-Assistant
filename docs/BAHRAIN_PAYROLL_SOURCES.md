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
  this law/decree as relevant, and as of this document's second research
  pass it has still **not** been individually located and confirmed against
  a primary source. Do not treat these as confirmed — they are a research
  backlog, not a citation. (Most items originally in this category were
  resolved during the second pass — see §4 for current status per item.)
- **Correction**: two items were actively wrong, not just unverified — the
  ticket's own description of two named LMRA Board Resolutions did not
  match what the primary source (LMRA's own legal library) actually shows.
  These are called out explicitly in §2c rather than silently fixed, since
  a wrong citation is more dangerous than a missing one.
- Every "Verified" row includes the retrieval date and the exact page URL so
  the citation can be re-checked as sources change.

---

## 1. Primary portals

| # | Portal | URL | Status | Language | Notes |
|---|---|---|---|---|---|
| 1 | Legislation & Legal Opinion Commission (LLOC) — legislation search | https://www.lloc.gov.bh/en/Legislation/Search | **Verified reachable and functional** (browser; blocked via plain HTTP fetch) | EN/AR toggle | Advanced search UI confirmed: filters by legislation number, year, official gazette number, legislation type, issuing ministry/organization, and classification. This is the authoritative gazette-of-record search tool. **The structured legislation-number + year filters work reliably and were used to confirm five citations in §2b** (free-text keyword search still did not return results — use the structured filters, not the search box). |
| 2 | SIO — advanced legislation search | https://www.sio.gov.bh/en/advanced-legislations-search | **Verified reachable and functional** | EN/AR toggle | Returned a live, paginated (46 pages) result set of SIO decisions/regulations when loaded. Confirms `Law No. 13 of 1975` is an actively cross-referenced SIO legislation number (see §2). |
| 3 | SIO official portal | https://www.sio.gov.bh | **Verified reachable** (browser; blocked via plain HTTP fetch) | EN/AR toggle | Homepage exposes Legislations, Reports & Statistics, Knowledge Center (FAQs), E-Services navigation. |
| 4 | LMRA official portal / legal library | https://lmra.gov.bh | **Verified reachable and functional** | EN/AR toggle | The "Legislations" nav item (`/en/page/show/221`) is a genuine legal library — see §2c. This is the single most valuable portal found this session for LMRA-specific instruments: it hosts full official PDF texts directly, not just metadata. |
| 5 | LMRA — WPS employer obligations | https://www.lmra.gov.bh/en/page/show/638 | **Verified reachable and read** (browser; blocked via plain HTTP fetch) | EN | See §3. |
| 6 | LMRA blog — Enhanced WPS announcement | https://blog.lmra.gov.bh/en/2025/10/21/lmra-launches-the-enhanced-wages-protection-system/ | **Verified reachable and read** (plain fetch succeeded) | EN | See §3. |
| 7 | BENEFIT — WPS 2.0 overview | https://benefit.bh/others/wps/Default | **Verified reachable and read** (browser; blocked via plain HTTP fetch) | EN | See §3. |
| 8 *(discovered this session, not in the original ticket list)* | LMRA Legislations hub | https://www.lmra.gov.bh/en/page/show/221 | **Verified reachable and functional** | EN (Arabic-only items also present) | Links to six sub-categories: The Law and Amendments, Decrees, Board of Directors Resolutions, Cabinet Resolutions Regarding LMRA Fees, Resolutions of Other Entities Related to LMRA Duties, Legislations on Cybersecurity — plus standalone "Labour Law" and "Personal Data Protection Law" pages. See §2c for what was found here. |

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

## 2a. Verified citations — SIO's own full-text law library (third research pass)

**Major discovery this pass**: SIO's `Legislations` nav menu is not just the
"Advanced Legislations Search" tool used in §1/§2 — it also has dedicated
**topic pages** (`Private Sectors`, `Public Sectors`, `Insurance Against
Unemployment`, `Insurance Protection Extension Law`, `End Of Service
Benefit`, `Women's rights...`), each of which links to a **"READ MORE"**
sub-page containing the **actual full consolidated legal text**, rendered
inline as HTML inside a modal (`<div class="modal" id="...">`), or in one
case a direct official PDF. This is one level more authoritative than
§2b's LLOC metadata (title/date/gazette number only) and closes several of
the "full text not retrieved" gaps flagged in the previous two passes.

**Access note**: the full text is not visible in the normal page render —
it lives inside a Bootstrap modal that only opens on click. The reliable
way to retrieve it is to load the sub-page in the browser, then read the
modal `<div>`'s `innerText` directly (e.g. via `document.querySelector('#modal-id').innerText`) — the modal HTML is already present in the page source, just hidden until the "READ MORE" link is clicked. This is a
useful operational note for a future ingestion pipeline.

| Field | Value |
|---|---|
| **Title** | Decree Law No. (24) of 1976 Promulgating the Social Insurance Law, consolidated with its amendments |
| **Full text** | **Complete inline text retrieved — 151 articles, ~126,400 characters**, from Article 1 ("This Law shall be cited as 'The Social Insurance Law'...") through Article 151 (penalties clause). Preamble confirms issuance: "Isa bin Salman Al Khalifa, Amir of the State of Bahrain... Issued at Al-Riffa Palace, on 2nd Rajab 1396 AH, corresponding to 29th June 1976." |
| **Source page** | https://www.sio.gov.bh/en/private-sectors → https://www.sio.gov.bh/en/law-no-24-of-1976 (modal `#article-6-924083`) |
| **Language** | English (site-provided translation; no Arabic-primacy statement shown on this specific modal, unlike §2c's LMRA PDF — treat Arabic Official Gazette text as authoritative per general principle in §6). |
| **Retrieved** | 2026-08-02 |
| **Legal priority** | High — this is the actual consolidated statutory text, not a summary or metadata record. **This closes the "full original text not retrieved" gap noted in §5 of the previous pass.** |
| **Status** | **Verified — full text retrieved and read.** This supersedes the LLOC-only metadata citation in §2b for this instrument. |

| Field | Value |
|---|---|
| **Title** | Law No. (78) of 2006 with respect to Insurance Against Unemployment and its amendments |
| **Full text** | **Complete inline text retrieved — ~30,400 characters**, from the preamble ("We, Hamad bin Isa Al Khalifa, King of the Kingdom of Bahrain, Having perused the Constitution, especially Article (38) thereof, And Law No. (13) of 1975...") through to the closing/signature block ("Issued at Rifaa Palace On 1st Thilqie'eda, 1427 Hijra, Corresponding to 22nd November, 2006"). |
| **Source page** | https://www.sio.gov.bh/en/insurance-against-unemployment → https://www.sio.gov.bh/en/law-no-13-of-1975-818549 (modal `#law-no-78-of-2006-with-respect-to-insurance-against-unemployment2`; note the URL slug is mismatched/reused from another page — a site quirk, not a data error) |
| **Language** | English (site-provided translation) |
| **Retrieved** | 2026-08-02 |
| **Legal priority** | High — full consolidated statutory text. |
| **Status** | **Verified — full text retrieved and read.** Supersedes the LLOC-only metadata citation in §2b for this instrument. |

| Field | Value |
|---|---|
| **Title** | Decision No. (109) of 2023 Promulgating the Regulation of End of Service Remuneration for Non-Bahrainis Working in the Private Sector |
| **Full text** | **Complete text retrieved — ~9,470 characters, all 15 articles** of the attached Regulation, plus the enacting Decision (4 articles) and signature block ("Prime Minister Salman bin Hamad Al Khalifa, Issued on: 28 Jumada al-Awwal 1445 AH, Corresponding: 12 December 2023"). Confirms Article Four: comes into force **1 March 2024**. |
| **Source page** | https://www.sio.gov.bh/en/end-of-service-benefits → https://www.sio.gov.bh/en/end-of-service-benefits (modal `#law-no21`) |
| **Language** | English (site-provided translation) |
| **Retrieved** | 2026-08-02 |
| **Legal priority** | High — this is the actual gazette-derived regulation text, not the FAQ paraphrase used in §2. **This closes the "Decision No. (109) of 2023 full text not located" gap flagged in §5 of the previous pass.** |
| **⚠ Correction to §2's FAQ-derived figure** | Article (9) of the Regulation states the remuneration is **"half a month's wages for each of the first three years of employment and one month's wages for each of the subsequent years"** — this is the authoritative wording. §2's SIO FAQ page paraphrased this as "**15 days' salary** for each year of the first three years," which is a common colloquial rendering of "half a month" but is **not the literal statutory wording** (a calendar half-month is not always exactly 15 days, and Bahraini payroll practice should confirm whether "half a month's wages" is computed as wage÷2 or as a fixed 15-day daily rate before this becomes a rule-pack parameter — flagged as an open implementation question, not resolved by source-gathering alone). The **4.2% / 8.4% contribution rates in §2 are confirmed verbatim** in Article (5) of this same text — no discrepancy there. |
| **Also confirms** | Article (1) definitions (Law = Decree-Law 24/1976; Organization = SIO; Fund = the pension/social-insurance fund established by Legislative Decree 21/2020); Article (3) exceptions (GCC nationals under Law 68/2006; categories in Article 3 of the Law); Article (13)–(14) transition rules for employees hired before the Regulation's entry into force. |
| **Status** | **Verified — full text retrieved and read. Supersedes §2's FAQ paraphrase as the primary citation; §2 should be read together with this correction, not relied on alone.** |

| Field | Value |
|---|---|
| **Title** | Law No. (13) of 1975 regarding the Organization of Pensions and Retirement Benefits for Government Employees (Bahraini workers, public sector) |
| **Full text** | **Direct official PDF located**: Arabic original, 2.7 MB, 58 pages. URL (Arabic filename, URL-encoded): `https://eservice-webprod-ir.s3.eu-west-1.amazonaws.com/uploads/القانون رقم 13 لسنة 1975 بشأن تنظيم معاشات ومكافآت التقاعد لموظفي الحكومة.pdf`. No English inline text is provided on this page ("This content will be published soon" placeholder shown instead). |
| **Source page** | https://www.sio.gov.bh/en/public-sectors → https://www.sio.gov.bh/en/law-no-13-of-1975 (modal `#article-1-542701`) |
| **Language** | Arabic only (official). No English translation currently published by SIO for this specific law. |
| **Retrieved** | 2026-08-02 |
| **Legal priority** | High — direct official PDF, Arabic original (the authoritative text per the language-priority principle in this document). |
| **Status** | **Verified — full official PDF located and link confirmed** (PDF not downloaded/OCR'd in this session — flagged as a follow-up if the full text needs to be machine-readable). **This closes the "Law No. 13 of 1975 full text not retrieved" gap** flagged in the previous pass's §5, though only in PDF/Arabic form, not English/inline HTML like the three laws above. |

---

## 2b. Verified citations — LLOC gazette-of-record legislation search

All five rows below were confirmed using LLOC's **structured** search
(`Legislation number` + `Year` fields, not the free-text keyword box) at
https://www.lloc.gov.bh/en/Legislation/Search, retrieved 2026-08-01. Each
result is the exact title/date/gazette-number LLOC's own database returns
for that legislation number and year — this is the closest this session got
to the actual gazette-of-record, one level more authoritative than SIO's or
LMRA's own paraphrased summary pages in §2/§3.

| Legislation number searched | Exact LLOC title returned | Date | Official Gazette No. | Confirms |
|---|---|---|---|---|
| 24 / 1976 | *(found via an amending law's title, not a direct hit — see note)* Law No. (44) of 2014 amending article (39) from Social Insurance Law promulgated by **Legislative Decree No. (24) of 1976** | 22-July-1976 (gazette date shown for the underlying 1976 instrument) | 1184 | **Decree-Law No. (24) of 1976 = "Social Insurance Law"** — the ticket's identification is correct. The original 1976 decree's own standalone LLOC record was not opened directly; this citation comes from a 2014 amending law's title that names it. Full original text still not retrieved — see §5. |
| 78 / 2006 | LAW NO. (78) OF 2006 WITH RESPECT TO INSURANCE AGAINST UNEMPLOYMENT | 23-November-2006 | 2766 | **Exact match** to the ticket's description. |
| 21 / 2020 | Legislative Decree No. (21) of 2020 regarding Retirement Funds and Pensions in Retirement and Insurance Laws and Regulations | 16-July-2020 | 3480 | Matches the ticket's "pension/social insurance unification" description. (Three unrelated "Decision No. (21) of 2020" items — judicial council, financial services, CBB supervision — also matched this number/year and are *not* this legislation; recorded here only to note the search returns same-numbered instruments from different issuing bodies in the same year.) |
| 19 / 2006 | LAW NO. (19) OF 2006 WITH RESPECT TO REGULATING THE LABOUR MARKET | 31-May-2006 | 2741 | **Exact match** — confirms this as the LMRA founding law. |
| 16 / 2021 | Legislative Decree No. (16) of 2021 amending certain provisions of the Labour Law for the Private Sector promulgated by **Law No. (36) of 2012** | 5-August-2021 | 3544 | **Exact match**, and independently *re-confirms* Law No. (36) of 2012 as "the Labour Law for the Private Sector" (second, independent source for that fact — see §3). |

**Status of all five**: legislation number, year, exact title, gazette date,
and gazette number confirmed via LLOC's own database. **Not yet
retrieved**: the actual PDF/full text of any of these five instruments —
LLOC's search results list metadata (title/date/gazette number) but this
session did not open an individual result to reach the full legislative
text. That remains a follow-up before any of these could back an actual
rule-pack parameter.

---

## 2c. Verified citations — LMRA's own legal library (full official texts)

LMRA hosts its own legal library directly on its site: **The Authority →
Legislations** (`https://www.lmra.gov.bh/en/page/show/221`), broken into
"The Law and Amendments," "Decrees," "Board of Directors Resolutions,"
"Cabinet Resolutions Regarding LMRA Fees," "Resolutions of Other Entities
Related to LMRA Duties," and "Legislations on Cybersecurity" /
"Labour Law" / "Personal Data Protection Law." This is a **more
authoritative source than LLOC's metadata-only search results in §2b** for
LMRA-specific instruments — it hosts full official PDF texts directly,
not just title/date/gazette-number metadata.

| Field | Value |
|---|---|
| **Title** | Act No. (19) of 2006 with regard to the Regulation of the Labour Market |
| **Full text** | **Direct PDF**: https://www.lmra.gov.bh/files/cms/shared/file/law-no19-year2006-english%20(1).pdf (273 KB) |
| **Landing page** | https://www.lmra.gov.bh/en/page/show/5 |
| **Retrieved** | 2026-08-01 |
| **Status** | **Verified — full official text located and directly downloadable** (PDF not opened/read in this session; link confirmed live). This is a stronger source than the LLOC metadata record in §2b for the same law. |

| Field | Value |
|---|---|
| **Title** | Labour Law (Law No. 36 of 2012, Private Sector) |
| **Full text** | **Direct PDF**: https://www.lmra.gov.bh/files/cms/shared/file/labour%20law.pdf (450 KB) |
| **Landing page** | https://www.lmra.gov.bh/en/page/show/199 |
| **Retrieved** | 2026-08-01 |
| **Key verified facts (quoted)** | "On July 26, 2012, the King of the Kingdom of Bahrain issued a new labour law No. 36 of 2012 **replacing the old labour law (No. 23 of 1976)**." — a new fact not seen elsewhere in this session: the predecessor law was Law No. 23 of 1976, not yet independently verified beyond this one mention. |
| **Arabic-primacy statement (verbatim, official)** | "This is unofficial translation, in case of difference between the Arabic and the English text, **the Arabic text shall prevail**." This is LMRA's own explicit statement — the strongest, most direct confirmation found this session of the ticket's "mark Arabic gazette/legal text as authoritative where English is only a translation/reference" requirement. |
| **Status** | **Verified — full official text located, with an explicit official Arabic-primacy statement.** Third independent confirmation of Law No. 36 of 2012 as the Private Sector Labour Law (after §2b and §3). |

### LMRA Board of Directors Resolutions — full list, with a correction to the ticket's descriptions

The full "Board of Directors Resolutions" list
(`https://www.lmra.gov.bh/en/legal/category/1`, retrieved 2026-08-01, "Last
Update" dates per-item as shown) contains 19 items. The two specifically
named in the ticket **do not match the ticket's stated subject matter** —
this is an important correction, not a confirmation:

| What the ticket said | What LMRA's own list actually shows for that number/year | Assessment |
|---|---|---|
| "LMRA Board Resolution No. (1) of 2022 on work permits" | قرار رقم (1) لسنة 2022 بشأن إسناد بعض مهام هيئة تنظيم سوق العمل إلى مراكز تسجيل العمالة وتعديلاته (Arabic only) — **"Resolution No. (1) of 2022 regarding the assignment of some tasks of the Labour Market Regulatory Authority to labour registration centres and its amendments"** | **Does not match** — this resolution is about delegating LMRA administrative tasks to registration centres, not work permits. Matches the unrelated LLOC hit found in §4 (same number/year, same subject). |
| "LMRA Board Resolution No. (2) of 2014 regarding domestic workers" | قرار رقم (2) لسنة 2014 بشأن تنظيم تصاريح مزاولة صاحب العمل الأجنبي للأنشطة المهنية وتعديلاته (Arabic only) — **"Resolution No. (2) of 2014 regarding the regulation of permits for the foreign employer's practice of professional activities and its amendments"** | **Does not match** — this is about foreign-employer professional-activity permits, not domestic workers. Confirms the LLOC finding in §4. |

**The actual domestic-workers instrument appears to exist under a
different number**: the same list includes **"Order No. (4) of 2014 With
regard to Regulation of Work Permits for Domestic Servants and
Equivalent"** — this, not "Resolution No. (2) of 2014," is the likely
correct citation for domestic-worker work permits. Not yet opened/read in
this session; recorded here as the corrected lead for follow-up.

**The general (non-domestic) work-permit regulation** also appears on this
list: "Decision No. (76) (2008) Regarding Regulating Work Permits for
Expatriate Employees Other than the category of Domestic Employees and its
Amendments."

**Recommendation**: treat the ticket's "LMRA Board Resolution No. (1) of
2022" and "No. (2) of 2014" descriptions as unreliable and supersede them
with this section. Do not carry the ticket's original descriptions into any
future rule-pack citation.

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

## 4. Legislation named in the ticket — verification status per item

These are named in HIS-50's brief as core legislation to collect. Most were
subsequently confirmed via LLOC (§2b) or LMRA's own legal library (§2c) in
a second research pass — this table is the up-to-date status per item, not
a stale "not yet found" list. Rows still marked unconfirmed, and the two
rows where **the ticket's own description turned out to be wrong**, are
called out explicitly. **Do not use any "not yet confirmed" row as a
rule-pack parameter source.**

### SIO / social insurance

| Legislation | Ticket's description | Verification status |
|---|---|---|
| Decree-Law No. (24) of 1976 | Social Insurance Law / private sector | **Fully confirmed** — full 151-article consolidated text retrieved directly from SIO (§2a), not just LLOC metadata (§2b). |
| Law No. (13) of 1975 | Pensions and retirement benefits, civil servants / public sector | **Confirmed** — direct official Arabic PDF (58 pages) located via SIO's Public Sectors page (§2a). No English translation currently published by SIO. |
| Law No. (78) of 2006 | Insurance Against Unemployment | **Fully confirmed** — full ~30,400-character consolidated text retrieved directly from SIO (§2a), not just LLOC metadata (§2b). |
| Decree-Law No. (21) of 2020 and amendments | Pension/social insurance unification | **Confirmed** via LLOC (§2b) — "Retirement Funds and Pensions in Retirement and Insurance Laws and Regulations" matches this description. Full text still not retrieved; amendments not individually enumerated. |
| 2023–2024 expatriate EOSB decrees/decisions | SIO-managed non-Bahraini EOSB | **Fully confirmed** — Decision No. (109) of 2023 full text (all 15 articles) retrieved directly from SIO (§2a), including a correction to §2's FAQ-paraphrased calculation formula. Other 2023-2024 decrees/decisions not enumerated this session. |
| SIO employer directives — monthly wage reporting/contribution shares | — | Not yet located this session; likely reachable via SIO E-Services/employer guides, not yet browsed. |

### LMRA / labour legislation

| Legislation | Ticket's description | Verification status |
|---|---|---|
| Law No. (19) of 2006 | Labour Market Regulation / LMRA founding law | **Confirmed** via LLOC (§2b) — exact title match. |
| Law No. (36) of 2012 | Labour Law for the Private Sector | **Confirmed twice, independently** — LMRA's own WPS obligations page (§3) and LLOC's record for Legislative Decree 16/2021 (§2b) both name it as "the Labour Law for the Private Sector." |
| Legislative Decree No. (16) of 2021 | Amendment | **Confirmed** via LLOC (§2b) — exact title match ("amending certain provisions of the Labour Law for the Private Sector"). |
| LMRA Board Resolution No. (1) of 2022 | Work permits | **Ticket's description is incorrect** — see §2c. LMRA's own legal library confirms this resolution is about assigning LMRA administrative tasks to labour registration centres, not work permits. |
| LMRA Board Resolution No. (2) of 2014 | Domestic workers | **Ticket's description is incorrect** — see §2c. LMRA's own legal library confirms this resolution is about foreign-employer professional-activity permits, not domestic workers. The likely correct instrument is **Order No. (4) of 2014 "Regulation of Work Permits for Domestic Servants and Equivalent"** (title read from LMRA's own list; full text not yet opened). |
| Flexible work permits / worker mobility / quota-ceiling regulations | — | Not yet located by name this session. LMRA's Board of Directors Resolutions list (§2c) is now known and enumerable — a full pass through all 19 entries (several "Arabic Only") for flexible-permit/mobility/quota content is a concrete, bounded follow-up rather than open-ended search. |

### Supplementary operational guidance (not legal text)

Not yet retrieved this session: LMRA employer/employee manuals and FAQs,
visa/work-permit issuance guidance, medical check guidance, employer
ceiling/quota guidance, the WPS User Manual PDF (referenced by name — "Wage
Protection System (WPS) User Manual PDF (4 MB)" — on the LMRA obligations
page in §3, but not opened), and SIO employer contribution-calculation
guides.

---

## 5. Explicit non-findings and blockers

- **LLOC keyword search still does not work**: the free-text search box on
  `lloc.gov.bh/en/Legislation/Search` never returned visible results in this
  session. **This is now resolved as a non-issue**: the structured filters
  (`Legislation number` + `Year`) work reliably and were used to confirm
  five citations in §2b — use those fields, not the search box.
- **Full text of LLOC-confirmed instruments — now resolved for 3 of 5**:
  §2b's five rows (Decree-Law 24/1976, Law 78/2006, Legislative Decree
  21/2020, Law 19/2006, Legislative Decree 16/2021) were confirmed at the
  title/date/gazette-number level from LLOC in the second pass. This third
  pass closed the full-text gap for **Decree-Law 24/1976 and Law 78/2006**
  directly via SIO (§2a), and **Law 19/2006** already had a full-text PDF
  via LMRA (§2c). **Still not retrieved in full**: Legislative Decree
  21/2020 (pension-fund unification) and Legislative Decree 16/2021 (a
  short amending instrument to Law 36/2012, which itself has full text via
  §2c).
- **Decision No. (109) of 2023 full text — resolved**: the complete
  15-article Regulation text was retrieved directly from SIO (§2a),
  including its coming-into-force date (1 March 2024) and a correction to
  the §2 FAQ's "15 days" paraphrase (statutory wording is "half a month's
  wages" — see §2a for the distinction and why it matters for a future
  rule pack).
- **Law No. (13) of 1975 — resolved, Arabic-only**: a direct official PDF
  (58 pages) was located via SIO's Public Sectors page (§2a). SIO has not
  published an English translation of this specific law; downstream use
  will need Arabic-text handling (OCR/translation) or a bilingual legal
  reviewer, not just an English paraphrase.
- **Legislative Decree No. (21) of 2020 and Legislative Decree No. (16) of
  2021 full text**: still only confirmed at the LLOC title/date/gazette-
  number level (§2b); neither has been opened at SIO, LMRA, or LLOC itself
  in any pass so far. This is the most concrete remaining full-text gap for
  a future pass.
- **The ticket's descriptions for two LMRA Board Resolutions were wrong**,
  not just unverified — see §2c. This is worth flagging distinctly from a
  simple "not found": a wrong citation is more dangerous than a missing one
  if it had been carried forward into a rule pack unchecked.
- **"Order No. (4) of 2014" (domestic-worker work permits) full text**: title
  read from LMRA's Board Resolutions list; the instrument itself has not
  been opened/read this session — flagged as the corrected follow-up lead
  (§2c, §4).
- **Automated (non-browser) fetch is blocked** on `sio.gov.bh`,
  `lmra.gov.bh`, `lloc.gov.bh`, and `benefit.bh` (HTTP 403 from bot
  protection). All content in this document was retrieved via an
  interactive browser session, not a bare HTTP client. Any future automated
  ingestion pipeline for these sources must render via a real browser.

---

## 6. Explicit rejection of AI-generated statutory numbers

Per HIS-50's acceptance criteria and the architecture handoff's invariant
that payroll/compliance calculations must be deterministic and
citation-backed, not LLM-derived: **every numeric figure and quoted legal
title in §2, §2b, §2c, and §3 above is a direct quote or close paraphrase
of text read from the cited official page in this session**, not a figure
recalled from training data. Any statutory number needed for a future rule
pack that is *not* backed by a row in one of those sections must be treated
as unverified and blocked — see §4 — until independently sourced the same
way. This discipline is also what caught the two wrong LMRA Board
Resolution descriptions in §2c: verifying against the primary source, not
trusting the ticket's own summary, is what surfaced the error.

## 7. Suitability for downstream use

Per the ticket's acceptance criteria ("output is suitable for later
ingestion into the AI knowledge base and deterministic rule-pack tests"):
this document's §2, §2a, §2b, §2c, and §3 tables are structured with a
stable field set (rule family, title/document number, issuing body, source
URL, language, retrieved date, status) suitable for direct ingestion as
retrieval-indexed policy documents or as fixture data for future rule-pack
unit tests. §2a provides the **full consolidated statutory text** (not
just metadata) for three core instruments (Decree-Law 24/1976, Law
78/2006, Decision 109/2023) plus a direct official PDF for a fourth (Law
13/1975); §2c additionally provides direct, official, full-text PDF URLs
for two core laws (No. 19/2006, No. 36/2012). Between §2a and §2c, six of
the ticket's named legislative instruments now have full-text (not just
metadata) citations — a materially stronger sourcing base than the first
two research passes. No payroll calculation logic, parameter defaults, or
code changes are introduced by this document.
