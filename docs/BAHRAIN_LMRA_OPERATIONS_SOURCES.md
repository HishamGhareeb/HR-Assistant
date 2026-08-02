# Bahrain LMRA employment-operations source inventory

Research deliverable for **HIS-66**. **No implementation code is added by
this document.**

**Relationship to existing docs**: `docs/BAHRAIN_PAYROLL_SOURCES.md` §2c
already covers the domestic-worker permit (Order 4/2014), LMRA's fee
schedule (Resolution 1/2017), and the Flexi Permit "Unresolved" closure.
This document adds the **general (non-domestic) expatriate work-permit
regime** — issuance, renewal, cancellation, worker mobility/transfer, and
medical-fitness requirements — which were the concrete open items left
after HIS-50 and the earlier passes on this ticket.

---

## 1. General work permit regulation — fully sourced

| Field | Value |
|---|---|
| **Title** | Decision No. (76) of 2008 Regarding Regulating Work Permits for Expatriate Employees Other than the category of Domestic Employees and its Amendments |
| **Full text** | **Downloaded and parsed in full — 21 articles.** |
| **Source** | https://www.lmra.gov.bh/en/legal/show/14 |
| **Retrieved** | 2026-08-02 |
| **Issued** | 18 May 2008, in force 1 July 2008 |

**Key provisions (quoted/paraphrased)**:

- **Employer eligibility (Article 2)**: registered commercial entity; all
  LMRA fees settled; demonstrated genuine need for a foreign worker
  (assessed against org size/nature of business); no unresolved LMRA
  violations; no history of unlawfully discontinuing/relocating a
  business; all final-judgment penalties settled; must commit to SIO
  insurance; no history of unpaid worker rights; worker must be medically
  fit and free of contagious disease; role must not be Bahraini-reserved;
  employer must hold any profession-specific license required; worker
  must not have a prior deportation/ban record.
- **Application process (Articles 3–4)**: employer applies (paper or
  online); LMRA verifies and issues an accept/decline order within
  **3 business days** of complete information; approval **voids if fees
  aren't settled within 30 days**.
- **Permit validity and renewal (Article 10)**: valid **2 years** from the
  worker's arrival, renewable for further 2-year periods; renewal
  application may be submitted **up to 90 days before expiry**.
- **Post-expiry grace (Article 12)**: worker must leave Bahrain after
  permit expiry **unless** the employer applies for a new permit for the
  same employee within **30 days** of the prior permit's termination.
- **Cancellation process (Article 13)**: LMRA must notify the employer of
  intent to cancel and reasons, with **at least 10 days** to respond,
  before issuing a cancellation order (except when cancellation is
  employer-requested or the worker has already abandoned work in
  violation of permit conditions). Appeal route to the CEO exists (via
  Article 33 of the Labour Market Regulation Law).
- **Temporary work permits (Articles 15–19)**: valid **6 months**,
  renewable **once only** (application up to 90 days before expiry);
  requires demonstrated temporary-nature need; **exempt from the
  Bahrainisation-percentage requirement** (Article 18) — a materially
  different rule from standard permits.
- **Worker obligations (Article 8)**: must not work outside the permitted
  role/premises; must register fingerprints/photo/signature within 1
  month of first arrival; may not be absent without leave/employer
  permission for **more than 15 continuous days**; must notify LMRA and
  employer of intent to transfer per the transfer-procedure order (§2
  below).
- **Employer obligations (Article 7)**: keep worker in the permitted role
  and premises (or same-activity branches); collect and submit biometric
  data; pay monthly permit fees; notify LMRA immediately of unauthorized
  departure, forfeited eligibility conditions, contagious illness
  discovery, or business liquidation/bankruptcy/license cancellation.
- **Profession change (Article 9)**: requires LMRA written consent;
  conditions largely mirror initial-eligibility conditions (genuine need,
  not a Bahraini-reserved role, medical fitness, required license).

---

## 2. Worker mobility / transfer between employers — fully sourced

| Field | Value |
|---|---|
| **Title** | Order No. (79) for 2009 Regarding the Procedures for Transferring a Foreign Worker to Another Employer |
| **Full text** | **Downloaded and parsed in full — 9 articles.** |
| **Source** | https://www.lmra.gov.bh/en/legal/show/17 |
| **Retrieved** | 2026-08-02 |
| **Issued** | 16 April 2009, in force 30 days after Official Gazette publication |

**Key provisions**:

- **Article 2 — the headline right**: a foreign worker may transfer to
  another employer **without the original employer's consent**,
  notwithstanding Article 25(b) of the Labour Market Regulation Law
  (Law 19/2006) — subject to the worker's contractual/legal obligations
  to the first employer remaining intact (i.e. this is a right to seek a
  new sponsor, not a release from contractual liability).
- **Article 3 — notice to the first employer**: required before transfer,
  by registered mail with delivery confirmation, during the
  contract/statutory notice period, **capped at 3 months** before the
  intended transfer date.
- **Articles 4–5 — new employer's application**: the receiving employer
  applies for a new work permit under the standard Decision 76/2008
  process (§1), attaching proof of the notice to the first employer; LMRA
  processes within the same 3-business-day framework.
- **Article 6**: the new permit becomes valid once fees are settled.
- **Article 7 — grace period after permit expiry/cancellation**: the
  worker must notify LMRA of transfer intent **at least 30 days before**
  permit expiry, or **within 5 business days** of a cancellation notice;
  a **30-day grace period** follows to arrange the transfer, during which
  the worker **may not perform any contractual work**.
- **Article 8**: this transfer right and its grace periods **do not
  apply** in the disqualifying circumstances listed in Article 25(b) of
  Law 19/2006. **Resolved in §3a below**: those 3 circumstances are (1)
  the worker ceases to meet permit-issuance conditions, (2) a final
  criminal judgment for a felony or an honor/honesty crime, (3) the
  worker violates the work permit's terms.
- **⚠ Correction (see §3a)**: Article 25(a) itself was amended in 2011 to
  add a **minimum-tenure condition — at least 1 Gregorian year in the
  worker's current job** — before the transfer-without-consent right
  applies. Neither the LMRA PDF nor this section's original wording
  captured that condition; it must be included in any implementation.

---

## 3. Medical fitness requirement — fully sourced

| Field | Value |
|---|---|
| **Title** | Order No. (9) of 2007 With Regard to Proving Medical Fitness of Foreign Workers |
| **Full text** | **Downloaded and parsed in full — 7 articles.** |
| **Issuing body** | Ministry of Health (not LMRA itself, though it's part of LMRA's legal library — cross-agency instrument, coordinated with LMRA's Board per the preamble). |
| **Source** | https://www.lmra.gov.bh/en/legal/show/91 |
| **Retrieved** | 2026-08-02 |
| **Issued** | 2 September 2007, in force the day after Gazette publication |

**Key provisions**: employer must send the foreign worker to a General
Medical Committee for examination **within 30 days of arrival** in
Bahrain (Article 2); the Committee certifies fitness and notifies LMRA of
the outcome (Article 3); if a worker is found unfit or has a contagious
disease, the Committee must notify LMRA **within 24 hours** (Article 4).

---

## 3a. Follow-up pass — Law 19/2006's own amendment history checked (closes a real gap)

Per the standing discipline established in `BAHRAIN_EMPLOYMENT_LAW_SOURCES.md`
§4 (never trust a "full text" document as self-consolidating without
checking its amendment list): **Law No. 19 of 2006 has 6 official
amendments on LLOC**
(https://www.lloc.gov.bh/En/Legislation/Amendments/K1906). Two are directly
relevant to what's sourced above.

### Article 25 was itself amended in 2011 — the LMRA PDF is missing this

| Field | Value |
|---|---|
| **Title** | Decision No. (15) of 2011 amending Paragraph (a) of Article (25) of Law No. (19) of 2006 |
| **Full text** | **Downloaded and parsed in full — a single, short amendment.** Adds the phrase **"provided that the foreign worker has spent at least one Gregorian year in his current work"** to Article 25(a) — a minimum-tenure condition on the worker's right to transfer without employer consent. |
| **Source** | https://www.lloc.gov.bh/FullEn/K1511.docx |
| **Retrieved** | 2026-08-02 |
| **⚠ Correction to §2 above**: the LMRA-hosted PDF text of Law 19/2006 quoted in §2 (Article 25) does **not** include this 1-year minimum-tenure condition — same "unconsolidated translation" pattern already found and explained for Law 36/2012 (`BAHRAIN_EMPLOYMENT_LAW_SOURCES.md` §4). **The correct, current reading of Article 25(a) is**: a foreign worker may transfer employers without the original employer's consent, *provided he has spent at least one Gregorian year in his current work* — this condition must be added to any implementation of the transfer right in §2. |

### The legal basis for work-permit quotas/ceilings — found

| Field | Value |
|---|---|
| **Title** | Legislative Decree No. (21) of 2021 amending Some Provisions of Law No. (19) of 2006 |
| **Full text** | **Downloaded and parsed in full — 3 articles.** Replaces Article 4(a)(1) to explicitly authorize the national labour market plan to **"include setting a maximum limit for the total number of work permits issued by the authority within a specific time frame, either across all work sectors or based on each profession or economic activity."** Also repeals Article 7(a)(1) and Article 12(a)(8) (content not independently re-extracted from the base law in this pass). |
| **Source** | https://www.lloc.gov.bh/FullEn/L2121.docx |
| **Retrieved** | 2026-08-02 |
| **Significance** | This is the **legal basis** for the quota/ceiling concept that LMRA's "Bahrainization Target Rate Lookup Values" e-service and "Parallel Bahrainization System" FAQ category (both found this pass, see §3b) implement operationally. It confirms quotas are legally authorized to be set per-sector or per-profession via the periodically-published national labour plan, **not** as a single fixed percentage in the primary legislation itself — which is why no flat quota number was found anywhere in the base law text. |

**Remaining 3 amendments not opened this pass** (lower apparent relevance
by title): Decision 18/2015 (amends Article 6 — LMRA's founding/governance
provisions, not the transfer/cancellation articles used above), Law
40/2014 ("some provisions," title too vague to skip safely — flagged as a
residual gap), Legislative Decree 32/2011 (Article 42(e), fee-related).

### Article 26 and the other cancellation grounds — not independently re-checked

Article 26 (permit cancellation grounds, §2 above) was **not** individually
confirmed against this amendment list the same way Article 25 was — it
happened to be captured incidentally while reading Article 25's
surrounding text in the base LMRA PDF, not independently cross-checked.
Flagged as a residual gap, not asserted as confirmed-current.

## 3b. Bahrainisation / Parallel Bahrainization System — partially confirmed

LMRA has a dedicated FAQ category, **"General Inquiries about Parallel
Bahrainization System"** (https://www.lmra.gov.bh/en/faq/category/5),
confirming the concept is real and administered as a **"commitment
level"**-based system (question 3: "How can I find out my Bahranization
commitment level?"), with its own fee structure (question 4/7) and
occupation-specific restrictions (question 10) — **but the answer content
itself could not be retrieved**: the page's accordion-style FAQ answers
did not load via a real click, a synthetic click, or by inspecting the DOM
for pre-rendered content (same broken-interaction pattern already seen on
SIO's FAQ tabs and LLOC's pagination controls this session — this appears
to be a systemic issue with Bahraini government sites' JS frameworks, not
a tooling gap specific to any one site).

**What is confirmed**: quotas/ceilings are legally authorized per §3a
above and administered via a tiered "commitment level" system, not a flat
percentage. **What is not confirmed**: the actual commitment-level tiers,
their percentage thresholds, or the fee schedule tied to them.

---

## 4. Still open

- **Employer quota/Bahrainisation ceiling rules — legal basis found, exact
  numbers still open**: Legislative Decree 21/2021 (§3a) confirms quotas
  are legally set per-sector/per-profession via the periodically-published
  national labour plan, administered via a "commitment level" tiered
  system (§3b) — but the actual tier thresholds, percentages, and fee
  schedule were not retrieved (LMRA's FAQ answers for this specific topic
  did not load despite three different interaction attempts).
- **Article 25(b) of Law 19/2006 — resolved** (§2, §3a): 3 disqualifying
  circumstances (forfeited permit conditions, felony/honor-honesty
  conviction, permit-terms violation) plus a 2011-added minimum-tenure
  condition (≥1 Gregorian year) on the underlying transfer right itself.
- **Residency/NOC (No-Objection Certificate) process** — not researched
  this pass; likely lives with the Nationality, Passports & Residence
  Affairs authority rather than LMRA directly (seen as a separate
  "stakeholder" link on LMRA's own site), which would put it outside this
  ticket's LMRA-specific scope — worth a scope clarification rather than
  further searching under HIS-66.
- **Dependents/family visa handling** — not researched; same
  cross-agency-boundary concern as residency/NOC above.
- **Whether domestic workers (Order 4/2014, already sourced) follow the
  same general transfer/medical-fitness procedures documented here, or
  have their own parallel process** — not cross-checked in this pass.

---

## 5. Explicit rejection of AI-generated statutory numbers

All figures and procedural details in §1–§3 are direct quotes or close
paraphrases of official LMRA-hosted legal-library text, retrieved and
parsed in this session — not recalled from training data.

---

## 6. Amendment-currency audit — cross-repo status (closes a standing open item)

Per the "check every cited law's amendment history before trusting a
full-text document" discipline established in `BAHRAIN_EMPLOYMENT_LAW_SOURCES.md`
§4, here is the current audit status across every Bahraini law with a
full-text citation anywhere in this repo:

| Law | LLOC amendment count | Fully checked? | Result |
|---|---|---|---|
| Law 36/2012 (Labour Law) | 4 | ✅ Yes | Confirmed unconsolidated — Articles 30/31/39 corrections documented in `BAHRAIN_EMPLOYMENT_LAW_SOURCES.md` §4 |
| Decree-Law 24/1976 (Social Insurance Law) | 19 | ⚠️ Partial | Article 33 confirmed current via Law 14/2022 (`BAHRAIN_SIO_CONTRIBUTION_RATES.md`); Article 47 (employment injury) unconfirmed — LLOC pagination broken, 9 older (pre-2009) amendments unreachable |
| Law 78/2006 (Unemployment Insurance) | 9 | ✅ Yes | **Confirmed current** — none of the 9 amendments touch Article 6 (subscription rates); the one vague-titled amendment (Law 4/2019) was individually checked and confirmed to touch Articles 1/8/11/12/14/18/19 only |
| **Law 19/2006 (LMRA founding law)** | 6 | ⚠️ Partial (this pass) | **Confirmed unconsolidated** — Article 25(a) missing a 2011-added minimum-tenure condition in the LMRA PDF (§3a above); 3 of 6 amendments not yet opened (Decision 18/2015 on Article 6, Law 40/2014 "some provisions," Legislative Decree 32/2011 on Article 42(e)) |

**Net finding**: this is now confirmed as a **repeatable pattern across at
least 2 of 4 checked laws** (Law 36/2012 and Law 19/2006), not a one-off.
Any future full-text citation from LLOC or LMRA should have its amendment
list checked before being treated as current — this is now a standing
operational discipline for this repo's Bahrain research, not just a
one-time finding.
