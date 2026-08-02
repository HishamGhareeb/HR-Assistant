"""EOSB pre/post-1-March-2024 liability split (HIS-63 research, HIS-71 wiring).

Per Decision No. (109) of 2023's own transition articles:

- Article 14: service *before* 1 March 2024 is governed by Law 36/2012
  Article 116 (a direct employer liability under the Labour Law), not the
  SIO-funded scheme -- these are two legally distinct liabilities for two
  date ranges of the same employee's tenure, not one continuous accrual.
- Article 13: an employee who already had more than
  ``EOSB_ARTICLE_13_PRE_TRANSITION_SERVICE_YEARS_THRESHOLD`` years of
  service before 1 March 2024 gets the subsequent-tier (8.4%) monthly
  contribution rate from day one of the scheme, rather than a fresh
  first-tier phase-in.

This module adds new functions on top of ``glue.bahrain_payroll.rules.eosb``
rather than changing that module's existing functions or their tested
behavior -- see docs/BAHRAIN_EOSB_PRE_POST_2024_SPLIT.md for the full
research and docs/BAHRAIN_RATE_VERSIONING.md for how the registry already
fails closed for any date before 2024-03-01.

**Interpretation flagged as an assumption, not confirmed by official text**
(docs/BAHRAIN_EOSB_PRE_POST_2024_SPLIT.md §3): the 3-year first tier for the
pre-2024 legacy portion is applied to that period's *own* duration,
independently from the post-2024 portion's own first tier -- not to the
employee's combined tenure. If a human/payroll reviewer determines
otherwise, only ``calculate_eosb_gratuity_with_pre_post_split`` needs to
change.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from glue.bahrain_payroll.rules.eosb import (
    eosb_effective_date,
    eosb_monthly_contribution_rate_percent,
)
from glue.bahrain_payroll.statutory_values import (
    EOSB_ARTICLE_13_PRE_TRANSITION_SERVICE_YEARS_THRESHOLD,
    EOSB_FIRST_TIER_YEARS,
    EOSB_HALF_MONTH_DIVISOR,
    EOSB_SUBSEQUENT_TIER_MONTHS_PER_YEAR,
    EOSB_SUBSEQUENT_YEARS_CONTRIBUTION_RATE_PERCENT,
    LEGACY_GRATUITY_FIRST_TIER_YEARS,
    LEGACY_GRATUITY_HALF_MONTH_DIVISOR,
    LEGACY_GRATUITY_SUBSEQUENT_TIER_MONTHS_PER_YEAR,
)

_DAYS_PER_YEAR = Decimal("365")  # NON_STATUTORY_NUMBER: calendar day-to-year conversion, not a legal figure.


@dataclass(frozen=True)
class EosbServicePeriodSplit:
    """Service duration split at the 2024-03-01 boundary, in years."""

    pre_march_2024_years: Decimal
    post_march_2024_years: Decimal


@dataclass(frozen=True)
class EosbSplitGratuityInput:
    monthly_basic_salary: Decimal
    monthly_social_allowance: Decimal
    hire_date: date
    termination_date: date

    @property
    def monthly_wage_base(self) -> Decimal:
        return self.monthly_basic_salary + self.monthly_social_allowance


@dataclass(frozen=True)
class EosbSplitGratuityResult:
    """Two legally distinct liabilities, reported separately -- never summed
    into a single figure without also exposing both components."""

    service_split: EosbServicePeriodSplit
    pre_march_2024_employer_direct_liability: Decimal
    post_march_2024_sio_funded_amount: Decimal
    total_amount: Decimal


def split_eosb_service_years(
    hire_date: date,
    termination_date: date,
) -> EosbServicePeriodSplit:
    """Splits [hire_date, termination_date] at the EOSB scheme's 2024-03-01
    effective-date boundary into pre- and post-period durations, in years."""

    if termination_date < hire_date:
        raise ValueError("termination_date cannot be before hire_date")

    boundary = eosb_effective_date()
    pre_period_end = min(termination_date, boundary)
    pre_days = max((pre_period_end - hire_date).days, 0)  # NON_STATUTORY_NUMBER: zero is the mathematical lower bound for a day count.
    post_period_start = max(hire_date, boundary)
    post_days = max((termination_date - post_period_start).days, 0)  # NON_STATUTORY_NUMBER: zero is the mathematical lower bound for a day count.

    return EosbServicePeriodSplit(
        pre_march_2024_years=Decimal(pre_days) / _DAYS_PER_YEAR,
        post_march_2024_years=Decimal(post_days) / _DAYS_PER_YEAR,
    )


def calculate_eosb_gratuity_with_pre_post_split(
    gratuity_input: EosbSplitGratuityInput,
) -> EosbSplitGratuityResult:
    """Calculates the pre-2024 (employer-direct) and post-2024 (SIO-funded)
    EOSB gratuity portions separately, per Decision 109/2023 Article 14."""

    if gratuity_input.monthly_wage_base < Decimal("0"):  # NON_STATUTORY_NUMBER: zero is the mathematical lower bound for wages.
        raise ValueError("monthly wage base cannot be negative")

    split = split_eosb_service_years(
        gratuity_input.hire_date,
        gratuity_input.termination_date,
    )

    pre_amount = _money(
        _tiered_amount(
            monthly_wage_base=gratuity_input.monthly_wage_base,
            service_years=split.pre_march_2024_years,
            first_tier_years=Decimal(str(LEGACY_GRATUITY_FIRST_TIER_YEARS.value)),
            half_month_divisor=Decimal(str(LEGACY_GRATUITY_HALF_MONTH_DIVISOR.value)),
            subsequent_months_per_year=Decimal(
                str(LEGACY_GRATUITY_SUBSEQUENT_TIER_MONTHS_PER_YEAR.value)
            ),
        )
    )
    post_amount = _money(
        _tiered_amount(
            monthly_wage_base=gratuity_input.monthly_wage_base,
            service_years=split.post_march_2024_years,
            first_tier_years=Decimal(str(EOSB_FIRST_TIER_YEARS.value)),
            half_month_divisor=Decimal(str(EOSB_HALF_MONTH_DIVISOR.value)),
            subsequent_months_per_year=Decimal(
                str(EOSB_SUBSEQUENT_TIER_MONTHS_PER_YEAR.value)
            ),
        )
    )

    return EosbSplitGratuityResult(
        service_split=split,
        pre_march_2024_employer_direct_liability=pre_amount,
        post_march_2024_sio_funded_amount=post_amount,
        total_amount=_money(pre_amount + post_amount),
    )


def eosb_monthly_contribution_rate_percent_with_article_13_transition(
    total_completed_service_years: Decimal,
    pre_march_2024_completed_service_years: Decimal,
    as_of: date | None = None,
) -> Decimal:
    """SIO-fund monthly contribution rate, applying Article 13's transition.

    Fails closed (``BahrainPayrollRateNotFoundError``) for any ``as_of``
    before the scheme's 2024-03-01 effective date, via the underlying
    registry lookup in ``eosb_monthly_contribution_rate_percent`` -- no
    special-case code needed for that; the registry already has no rows
    before that date.
    """

    threshold = Decimal(
        str(EOSB_ARTICLE_13_PRE_TRANSITION_SERVICE_YEARS_THRESHOLD.value)
    )
    if pre_march_2024_completed_service_years > threshold:
        return Decimal(str(EOSB_SUBSEQUENT_YEARS_CONTRIBUTION_RATE_PERCENT.value))
    return eosb_monthly_contribution_rate_percent(total_completed_service_years, as_of)


def eosb_monthly_employer_contribution_with_article_13_transition(
    monthly_wage: Decimal,
    total_completed_service_years: Decimal,
    pre_march_2024_completed_service_years: Decimal,
    as_of: date | None = None,
) -> Decimal:
    rate = eosb_monthly_contribution_rate_percent_with_article_13_transition(
        total_completed_service_years,
        pre_march_2024_completed_service_years,
        as_of,
    )
    return _money(monthly_wage * rate / Decimal("100"))


def _tiered_amount(
    monthly_wage_base: Decimal,
    service_years: Decimal,
    first_tier_years: Decimal,
    half_month_divisor: Decimal,
    subsequent_months_per_year: Decimal,
) -> Decimal:
    first_tier_years_used = min(service_years, first_tier_years)
    subsequent_tier_years_used = max(
        service_years - first_tier_years,
        Decimal("0"),  # NON_STATUTORY_NUMBER: zero is the mathematical lower bound.
    )
    first_tier_amount = monthly_wage_base / half_month_divisor * first_tier_years_used
    subsequent_tier_amount = (
        monthly_wage_base * subsequent_months_per_year * subsequent_tier_years_used
    )
    return first_tier_amount + subsequent_tier_amount


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
