"""Bahrain EOSB rule pack for non-Bahraini private-sector employees.

Sources:
- ``docs/BAHRAIN_PAYROLL_SOURCES.md`` §2a: Decision No. (109) of 2023
- ``docs/BAHRAIN_PAYROLL_SOURCES.md`` §2a-ter: Legislative Decree 21/2020 and
  SIO wage-reporting guides
- ``docs/BAHRAIN_RULE_PACK_SCOPE.md``: human interpretation that Article 9's
  "half a month's wages" means monthly wage divided by two, not daily wage
  multiplied by fifteen.

This module implements deterministic EOSB eligibility, contribution-rate,
gratuity-amount, and employer-penalty helpers. It deliberately does not model
Flexi Permit or Law 68/2006 GCC social-insurance-protection logic because those
remain excluded from the current Bahrain rule-pack scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

from glue.bahrain_payroll.statutory_values import (
    EOSB_EMPLOYER_PENALTY_MAX_MULTIPLIER,
    EOSB_EMPLOYER_PENALTY_MIN_MULTIPLIER,
    EOSB_EFFECTIVE_DATE,
    EOSB_FIRST_THREE_YEARS_CONTRIBUTION_RATE_PERCENT,
    EOSB_FIRST_TIER_YEARS,
    EOSB_HALF_MONTH_DIVISOR,
    EOSB_SUBSEQUENT_TIER_MONTHS_PER_YEAR,
    EOSB_SUBSEQUENT_YEARS_CONTRIBUTION_RATE_PERCENT,
)
from glue.bahrain_payroll.rate_registry import (
    BAHRAIN_PAYROLL_RATE_REGISTRY,
    BahrainContributionBranch,
    BahrainContributionPayer,
    BahrainPayrollRateLookup,
    BahrainWorkerCategory,
)


class BahrainEmploymentSector(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class BahrainWorkerNationalityCategory(str, Enum):
    BAHRAINI = "bahraini"
    NON_BAHRAINI = "non_bahraini"
    GCC_NATIONAL = "gcc_national"


@dataclass(frozen=True)
class EosbEligibilityInput:
    sector: BahrainEmploymentSector
    nationality_category: BahrainWorkerNationalityCategory
    employment_injuries_branch_covered: bool
    social_insurance_law_article_3_excluded: bool = False


@dataclass(frozen=True)
class EosbEligibilityResult:
    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class EosbGratuityInput:
    monthly_basic_salary: Decimal
    monthly_social_allowance: Decimal
    service_years: Decimal

    @property
    def monthly_wage_base(self) -> Decimal:
        return self.monthly_basic_salary + self.monthly_social_allowance


@dataclass(frozen=True)
class EosbGratuityResult:
    first_tier_years: Decimal
    subsequent_tier_years: Decimal
    monthly_wage_base: Decimal
    amount: Decimal


@dataclass(frozen=True)
class EosbEmployerPenaltyRange:
    minimum: Decimal
    maximum: Decimal


def evaluate_eosb_eligibility(
    employee: EosbEligibilityInput,
) -> EosbEligibilityResult:
    reasons: list[str] = []
    if employee.sector != BahrainEmploymentSector.PRIVATE:
        reasons.append("EOSB applies to private-sector employees only.")
    if employee.nationality_category != BahrainWorkerNationalityCategory.NON_BAHRAINI:
        reasons.append("EOSB applies to non-Bahraini employees; Bahrainis and GCC nationals are out of scope.")
    if not employee.employment_injuries_branch_covered:
        reasons.append("EOSB requires coverage under the Employment Injuries insurance branch.")
    if employee.social_insurance_law_article_3_excluded:
        reasons.append("Employee is in a Social Insurance Law Article 3 excluded category.")
    return EosbEligibilityResult(eligible=not reasons, reasons=tuple(reasons))


def eosb_monthly_contribution_rate_percent(
    completed_service_years: Decimal,
    as_of: date | None = None,
) -> Decimal:
    rate = BAHRAIN_PAYROLL_RATE_REGISTRY.lookup(
        BahrainPayrollRateLookup(
            worker_category=BahrainWorkerCategory.NON_BAHRAINI_PRIVATE,
            branch=BahrainContributionBranch.EXPATRIATE_EOSB,
            payer=BahrainContributionPayer.EMPLOYER,
            as_of=as_of or eosb_effective_date(),
            completed_service_years=completed_service_years,
        )
    )
    return Decimal(str(rate.percent.value))


def eosb_monthly_employer_contribution(
    monthly_wage: Decimal,
    completed_service_years: Decimal,
) -> Decimal:
    rate = eosb_monthly_contribution_rate_percent(completed_service_years)
    return _money(monthly_wage * rate / Decimal("100"))


def calculate_eosb_gratuity_amount(
    gratuity_input: EosbGratuityInput,
) -> EosbGratuityResult:
    if gratuity_input.service_years < Decimal("0"):  # NON_STATUTORY_NUMBER: zero is the mathematical lower bound for service duration.
        raise ValueError("service_years cannot be negative")
    if gratuity_input.monthly_wage_base < Decimal("0"):  # NON_STATUTORY_NUMBER: zero is the mathematical lower bound for wages.
        raise ValueError("monthly wage base cannot be negative")

    first_tier_limit = Decimal(str(EOSB_FIRST_TIER_YEARS.value))
    first_tier_years = min(gratuity_input.service_years, first_tier_limit)
    subsequent_tier_years = max(
        gratuity_input.service_years - first_tier_limit,
        Decimal("0"),
    )
    first_tier_amount = (
        gratuity_input.monthly_wage_base
        / Decimal(str(EOSB_HALF_MONTH_DIVISOR.value))
        * first_tier_years
    )
    subsequent_tier_amount = (
        gratuity_input.monthly_wage_base
        * Decimal(str(EOSB_SUBSEQUENT_TIER_MONTHS_PER_YEAR.value))
        * subsequent_tier_years
    )
    return EosbGratuityResult(
        first_tier_years=first_tier_years,
        subsequent_tier_years=subsequent_tier_years,
        monthly_wage_base=gratuity_input.monthly_wage_base,
        amount=_money(first_tier_amount + subsequent_tier_amount),
    )


def employer_non_payment_penalty_range(
    unpaid_contribution_amount: Decimal,
) -> EosbEmployerPenaltyRange:
    if unpaid_contribution_amount < Decimal("0"):  # NON_STATUTORY_NUMBER: zero is the mathematical lower bound for unpaid amount.
        raise ValueError("unpaid_contribution_amount cannot be negative")
    return EosbEmployerPenaltyRange(
        minimum=_money(
            unpaid_contribution_amount
            * Decimal(str(EOSB_EMPLOYER_PENALTY_MIN_MULTIPLIER.value))
        ),
        maximum=_money(
            unpaid_contribution_amount
            * Decimal(str(EOSB_EMPLOYER_PENALTY_MAX_MULTIPLIER.value))
        ),
    )


def eosb_effective_date() -> date:
    return date.fromisoformat(str(EOSB_EFFECTIVE_DATE.value))


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

