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
