"""Citation-backed statutory and official-operational Bahrain payroll values."""

from __future__ import annotations

from glue.bahrain_payroll.citation_guard import StatutoryCitation, StatutoryValue


WPS_MAX_WORKER_RECORDS_PER_FILE = StatutoryValue(
    name="wps_max_worker_records_per_file",
    value=1000,
    unit="worker records",
    citation=StatutoryCitation(
        section="§2a-ter",
        instrument="WPS User Manual",
        retrieved="2026-08-02",
        quote="Maximum **1,000 worker records per salary file**",
    ),
)

WPS_ADVANCE_SCHEDULING_WINDOW_DAYS = StatutoryValue(
    name="wps_advance_scheduling_window_days",
    value=14,
    unit="days",
    citation=StatutoryCitation(
        section="§2a-ter",
        instrument="WPS User Manual",
        retrieved="2026-08-02",
        quote="scheduled up to 14 days before the actual transfer",
    ),
)

WPS_DISCLOSURE_FIELDS_CITATION = StatutoryCitation(
    section="§2c",
    instrument="Resolution No. 68 of 2019",
    retrieved="2026-08-02",
)

SIO_SALARY_INCREASE_CAP_PERCENT = StatutoryValue(
    name="sio_salary_increase_cap_percent",
    value=40,
    unit="percent",
    citation=StatutoryCitation(
        section="§2a-ter",
        instrument="SIO employer wage-reporting guides",
        retrieved="2026-08-02",
        quote="40% salary-increase cap",
    ),
)

SIO_NO_SALARY_DECREASE_CITATION = StatutoryCitation(
    section="§2a-ter",
    instrument="SIO employer wage-reporting guides",
    retrieved="2026-08-02",
    quote="No salary decreases permitted",
)

SIO_TOTAL_ALLOWANCES_CITATION = StatutoryCitation(
    section="§2a-ter",
    instrument="SIO employer wage-reporting guides",
    retrieved="2026-08-02",
    quote="Total Allowances ≤ Basic Salary",
)

SIO_CONTRIBUTION_SCOPE_CITATION = StatutoryCitation(
    section="§2a-ter",
    instrument="SIO employer wage-reporting guides",
    retrieved="2026-08-02",
    quote="annual-vs-monthly contribution scope",
)

SIO_IMMUTABLE_FIELDS_CITATION = StatutoryCitation(
    section="§2a-ter",
    instrument="SIO employer wage-reporting guides",
    retrieved="2026-08-02",
    quote="Immutable fields",
)

EOSB_FIRST_THREE_YEARS_CONTRIBUTION_RATE_PERCENT = StatutoryValue(
    name="eosb_first_three_years_contribution_rate_percent",
    value=4.2,
    unit="percent",
    citation=StatutoryCitation(
        section="§2a",
        instrument="Decision No. (109) of 2023",
        retrieved="2026-08-02",
        quote="4.2% / 8.4% contribution rates",
    ),
)

EOSB_SUBSEQUENT_YEARS_CONTRIBUTION_RATE_PERCENT = StatutoryValue(
    name="eosb_subsequent_years_contribution_rate_percent",
    value=8.4,
    unit="percent",
    citation=StatutoryCitation(
        section="§2a",
        instrument="Decision No. (109) of 2023",
        retrieved="2026-08-02",
        quote="4.2% / 8.4% contribution rates",
    ),
)

EOSB_FIRST_TIER_YEARS = StatutoryValue(
    name="eosb_first_tier_years",
    value=3,
    unit="years",
    citation=StatutoryCitation(
        section="§2a",
        instrument="Decision No. (109) of 2023",
        retrieved="2026-08-02",
        quote="half a month's wages for each of the first three years of employment and one month's wages for each of the subsequent years",
    ),
)

EOSB_HALF_MONTH_DIVISOR = StatutoryValue(
    name="eosb_half_month_divisor",
    value=2,
    unit="monthly-wage divisor",
    citation=StatutoryCitation(
        section="§2a",
        instrument="Decision No. (109) of 2023",
        retrieved="2026-08-02",
        quote="half a month's wages for each of the first three years of employment and one month's wages for each of the subsequent years",
    ),
    note="Human payroll/legal interpretation logged on HIS-54: half month means monthly wage ÷ 2, not daily wage × 15.",
)

EOSB_SUBSEQUENT_TIER_MONTHS_PER_YEAR = StatutoryValue(
    name="eosb_subsequent_tier_months_per_year",
    value=1,
    unit="monthly wages per year",
    citation=StatutoryCitation(
        section="§2a",
        instrument="Decision No. (109) of 2023",
        retrieved="2026-08-02",
        quote="half a month's wages for each of the first three years of employment and one month's wages for each of the subsequent years",
    ),
)

EOSB_EFFECTIVE_DATE_CITATION = StatutoryCitation(
    section="§2a",
    instrument="Decision No. (109) of 2023",
    retrieved="2026-08-02",
    quote="1 March 2024",
)

EOSB_EFFECTIVE_DATE = StatutoryValue(
    name="eosb_effective_date",
    value="2024-03-01",
    unit="date",
    citation=StatutoryCitation(
        section="§2a",
        instrument="Decision No. (109) of 2023",
        retrieved="2026-08-02",
        quote="1 March 2024",
    ),
)

EOSB_SCOPE_CITATION = StatutoryCitation(
    section="§2a",
    instrument="Decision No. (109) of 2023",
    retrieved="2026-08-02",
    quote="GCC nationals under Law 68/2006; categories in Article 3 of the Law",
)

EOSB_FUND_STRUCTURE_CITATION = StatutoryCitation(
    section="§2a-ter",
    instrument="Legislative Decree No. (21) of 2020",
    retrieved="2026-08-02",
    quote="Retirement and Social Insurance Fund",
)

EOSB_EMPLOYER_PENALTY_MIN_MULTIPLIER = StatutoryValue(
    name="eosb_employer_penalty_min_multiplier",
    value=1,
    unit="times unpaid amount",
    citation=StatutoryCitation(
        section="§2a-ter",
        instrument="Legislative Decree No. (21) of 2020",
        retrieved="2026-08-02",
        quote="not less than the unpaid amount and not exceeding three times that amount",
    ),
)

EOSB_EMPLOYER_PENALTY_MAX_MULTIPLIER = StatutoryValue(
    name="eosb_employer_penalty_max_multiplier",
    value=3,
    unit="times unpaid amount",
    citation=StatutoryCitation(
        section="§2a-ter",
        instrument="Legislative Decree No. (21) of 2020",
        retrieved="2026-08-02",
        quote="not less than the unpaid amount and not exceeding three times that amount",
    ),
)

# --- Bahraini SIO: old-age/disability/death pension branch (Article 33, ---
# --- Decree-Law 24/1976 as replaced by Law No. (14) of 2022) --------------
#
# Only the EMPLOYEE share is registered as an executable rate. The employer
# share's target rate (17%) and starting rate (11%) are documented, but the
# amendment text only says the employer rate "increases annually by a rate
# of 1%" without stating the exact calendar trigger for each step -- unlike
# the employee share, which explicitly steps "at the beginning of the year
# following the entry into force of the law." Per HIS-68's scope decision,
# the employer pension share stays unregistered (fails closed) until a
# human/payroll reviewer confirms the annual step-up trigger date. See
# docs/BAHRAIN_RATE_VERSIONING.md for the standing record of this decision.

BAHRAINI_PENSION_EMPLOYEE_RATE_PERCENT_INITIAL = StatutoryValue(
    name="bahraini_pension_employee_rate_percent_initial",
    value=6,
    unit="percent",
    citation=StatutoryCitation(
        section="§1",
        instrument="Law No. (14) of 2022",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_SIO_CONTRIBUTION_RATES.md",
        quote="upon enforcement, increases to the full 7%",
    ),
    note=(
        "Effective 2022-04-19 (day after the LLOC-recorded Official Gazette "
        "publication date of 18 April 2022, Gazette No. 3599) until the "
        "2023-01-01 step-up to 7%."
    ),
)

BAHRAINI_PENSION_EMPLOYEE_RATE_PERCENT_TARGET = StatutoryValue(
    name="bahraini_pension_employee_rate_percent_target",
    value=7,
    unit="percent",
    citation=StatutoryCitation(
        section="§1",
        instrument="Law No. (14) of 2022",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_SIO_CONTRIBUTION_RATES.md",
        quote="the beginning of the year following the entry into force of the law",
    ),
    note="Effective 2023-01-01: the calendar year following Law 14/2022's 2022 entry into force.",
)

BAHRAINI_PENSION_EMPLOYEE_INITIAL_EFFECTIVE_DATE = StatutoryValue(
    name="bahraini_pension_employee_initial_effective_date",
    value="2022-04-19",
    unit="date",
    citation=StatutoryCitation(
        section="§1",
        instrument="Law No. (14) of 2022",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_SIO_CONTRIBUTION_RATES.md",
        quote="18 April 2022, in force the day after Official Gazette publication",
    ),
)

BAHRAINI_PENSION_EMPLOYEE_TARGET_EFFECTIVE_DATE = StatutoryValue(
    name="bahraini_pension_employee_target_effective_date",
    value="2023-01-01",
    unit="date",
    citation=StatutoryCitation(
        section="§1",
        instrument="Law No. (14) of 2022",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_SIO_CONTRIBUTION_RATES.md",
        quote="the beginning of the year following the entry into force of the law",
    ),
)

# --- Employment injury (Decree-Law 24/1976, Article 47) -------------------
#
# Deliberately NOT registered as an executable rate. The 3% figure and its
# original citation are documented for traceability only; per HIS-68/69's
# scope decision it stays out of the rate registry until the amendment
# currency question is resolved (LLOC's pagination for this law's older
# amendments -- pre-2009 -- could not be reached this research pass).

EMPLOYMENT_INJURY_RATE_CITATION_NOT_REGISTERED = StatutoryCitation(
    section="§1",
    instrument="Decree-Law No. (24) of 1976, Article 47",
    retrieved="2026-08-02",
    source_doc="docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md",
    quote="3% of monthly wages, employer-only",
)

# --- Unemployment insurance (Law 78/2006, Article 6) -----------------------
#
# Nationality-neutral: applies identically to Bahraini and non-Bahraini
# private-sector workers (see docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md §1).
# The employer's 1% share is paid by the Labour Fund (Tamkeen) for
# private-sector employers, not charged to the employer directly -- modeled
# via BahrainContributionPayer.LABOUR_FUND, not EMPLOYER.

BAHRAIN_UNEMPLOYMENT_EMPLOYEE_RATE_PERCENT = StatutoryValue(
    name="bahrain_unemployment_employee_rate_percent",
    value=1,
    unit="percent",
    citation=StatutoryCitation(
        section="§1",
        instrument="Law 78/2006",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md",
        quote="1% of wage from the insured employee, 1% from the employer, 1% from the Government",
    ),
)

BAHRAIN_UNEMPLOYMENT_LABOUR_FUND_RATE_PERCENT = StatutoryValue(
    name="bahrain_unemployment_labour_fund_rate_percent",
    value=1,
    unit="percent",
    citation=StatutoryCitation(
        section="§1",
        instrument="Law 78/2006",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md",
        quote="Tamkeen (the Labour Fund) covers the private-sector employer's 1% share",
    ),
    note="Paid by the Labour Fund on the private-sector employer's behalf, not deducted from the employer directly.",
)

BAHRAIN_UNEMPLOYMENT_GOVERNMENT_RATE_PERCENT = StatutoryValue(
    name="bahrain_unemployment_government_rate_percent",
    value=1,
    unit="percent",
    citation=StatutoryCitation(
        section="§1",
        instrument="Law 78/2006",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md",
        quote="1% of wage from the insured employee, 1% from the employer, 1% from the Government",
    ),
)

BAHRAIN_UNEMPLOYMENT_LAW_EFFECTIVE_DATE = StatutoryValue(
    name="bahrain_unemployment_law_effective_date",
    value="2006-11-23",
    unit="date",
    citation=StatutoryCitation(
        section="§2",
        instrument="Law No. (78) of 2006",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_PAYROLL_SOURCES.md",
        quote="Law No. (78) of 2006 with respect to Insurance Against Unemployment",
    ),
    note=(
        "This is the LLOC-recorded Official Gazette publication date, used as a "
        "conservative floor. The law's exact commencement date (which may be "
        "some days after publication per its own commencement article) was not "
        "independently re-confirmed -- immaterial for any payroll date in "
        "practice, since it is decades in the past."
    ),
)

# --- EOSB pre/post-1-March-2024 liability split (Decision 109/2023 -------
# --- Articles 13-14, HIS-63/HIS-71) ---------------------------------------
#
# Article 14 requires pre-2024-03-01 service to be governed by Law 36/2012
# Article 116 (a direct employer liability under the Labour Law) rather than
# the SIO-funded scheme. Article 116 uses the identical formula *shape* as
# Decision 109/2023 Article 9 ("half a month's wage for each of the first
# three years... one month's wage for each of the subsequent years"), so the
# following constants mirror EOSB_FIRST_TIER_YEARS / EOSB_HALF_MONTH_DIVISOR
# / EOSB_SUBSEQUENT_TIER_MONTHS_PER_YEAR numerically, but are kept as
# separate StatutoryValue entries citing their own legal basis (Article 116,
# not Article 9) for audit clarity -- the two provisions could diverge in a
# future amendment even though they agree today.

LEGACY_GRATUITY_FIRST_TIER_YEARS = StatutoryValue(
    name="legacy_gratuity_first_tier_years",
    value=3,
    unit="years",
    citation=StatutoryCitation(
        section="§5",
        instrument="Law No. 36 of 2012",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_EMPLOYMENT_LAW_SOURCES.md",
        quote="half a month's wage per year for the first 3 years, one month's wage per year thereafter",
    ),
)

LEGACY_GRATUITY_HALF_MONTH_DIVISOR = StatutoryValue(
    name="legacy_gratuity_half_month_divisor",
    value=2,
    unit="monthly-wage divisor",
    citation=StatutoryCitation(
        section="§5",
        instrument="Law No. 36 of 2012",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_EMPLOYMENT_LAW_SOURCES.md",
        quote="half a month's wage per year for the first 3 years, one month's wage per year thereafter",
    ),
    note=(
        "Reuses the same wage-division interpretation decided for Article 9 on "
        "HIS-54 (half a month means monthly wage ÷ 2, not daily wage × 15), "
        "applied here by analogy to Article 116's identical wording -- not "
        "independently re-confirmed for Article 116 specifically."
    ),
)

LEGACY_GRATUITY_SUBSEQUENT_TIER_MONTHS_PER_YEAR = StatutoryValue(
    name="legacy_gratuity_subsequent_tier_months_per_year",
    value=1,
    unit="monthly wages per year",
    citation=StatutoryCitation(
        section="§5",
        instrument="Law No. 36 of 2012",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_EMPLOYMENT_LAW_SOURCES.md",
        quote="half a month's wage per year for the first 3 years, one month's wage per year thereafter",
    ),
)

EOSB_ARTICLE_13_PRE_TRANSITION_SERVICE_YEARS_THRESHOLD = StatutoryValue(
    name="eosb_article_13_pre_transition_service_years_threshold",
    value=3,
    unit="years",
    citation=StatutoryCitation(
        section="§2",
        instrument="Decision No. (109) of 2023",
        retrieved="2026-08-02",
        source_doc="docs/BAHRAIN_EOSB_PRE_POST_2024_SPLIT.md",
        quote="exceeding three years before the entry into force of the provisions of this Regulation",
    ),
    note=(
        "Employees with more than this many years of pre-2024-03-01 service "
        "skip straight to the subsequent-tier (8.4%) monthly contribution rate "
        "from day one of the scheme, per Article 13. This is a distinct legal "
        "threshold from EOSB_FIRST_TIER_YEARS even though the number matches."
    ),
)
