"""Effective-dated Bahrain payroll rate registry.

The registry is the country-law versioning seam. Payroll rules ask for rates by
worker category, contribution branch, payer, date, and optional service band. If
we do not have a source-backed rate for that exact context, lookup fails closed
instead of falling back to an implied "current" number.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Iterable

from glue.bahrain_payroll.citation_guard import StatutoryValue
from glue.bahrain_payroll.statutory_values import (
    EOSB_EFFECTIVE_DATE,
    EOSB_FIRST_THREE_YEARS_CONTRIBUTION_RATE_PERCENT,
    EOSB_FIRST_TIER_YEARS,
    EOSB_SUBSEQUENT_YEARS_CONTRIBUTION_RATE_PERCENT,
)


class BahrainPayrollRateNotFoundError(LookupError):
    """Raised when no source-backed rate exists for the requested context."""


class BahrainContributionBranch(str, Enum):
    EXPATRIATE_EOSB = "expatriate_eosb"
    OLD_AGE_DISABILITY_DEATH = "old_age_disability_death"
    EMPLOYMENT_INJURY = "employment_injury"
    UNEMPLOYMENT = "unemployment"


class BahrainContributionPayer(str, Enum):
    EMPLOYER = "employer"
    EMPLOYEE = "employee"
    GOVERNMENT = "government"
    LABOUR_FUND = "labour_fund"


class BahrainWorkerCategory(str, Enum):
    BAHRAINI_PRIVATE = "bahraini_private"
    NON_BAHRAINI_PRIVATE = "non_bahraini_private"
    GCC_PRIVATE = "gcc_private"
    DOMESTIC_WORKER = "domestic_worker"
    PUBLIC_SECTOR = "public_sector"
    SELF_EMPLOYED = "self_employed"
    FLEXI_OR_SUCCESSOR = "flexi_or_successor"


@dataclass(frozen=True)
class BahrainPayrollRate:
    """One source-backed statutory rate over one effective date window."""

    code: str
    worker_category: BahrainWorkerCategory
    branch: BahrainContributionBranch
    payer: BahrainContributionPayer
    percent: StatutoryValue
    effective_from: date
    effective_to: date | None = None
    min_completed_service_years: StatutoryValue | None = None
    max_completed_service_years_exclusive: StatutoryValue | None = None
    note: str | None = None

    def applies_on(self, as_of: date) -> bool:
        if as_of < self.effective_from:
            return False
        if self.effective_to is not None and as_of > self.effective_to:
            return False
        return True

    def applies_to_service_years(
        self,
        completed_service_years: Decimal | None,
    ) -> bool:
        if (
            self.min_completed_service_years is None
            and self.max_completed_service_years_exclusive is None
        ):
            return True
        if completed_service_years is None:
            return False
        if (
            self.min_completed_service_years is not None
            and completed_service_years
            < Decimal(str(self.min_completed_service_years.value))
        ):
            return False
        if (
            self.max_completed_service_years_exclusive is not None
            and completed_service_years
            >= Decimal(str(self.max_completed_service_years_exclusive.value))
        ):
            return False
        return True


@dataclass(frozen=True)
class BahrainPayrollRateLookup:
    worker_category: BahrainWorkerCategory
    branch: BahrainContributionBranch
    payer: BahrainContributionPayer
    as_of: date
    completed_service_years: Decimal | None = None


class BahrainPayrollRateRegistry:
    def __init__(self, rates: Iterable[BahrainPayrollRate]) -> None:
        self._rates = tuple(rates)

    @property
    def rates(self) -> tuple[BahrainPayrollRate, ...]:
        return self._rates

    def lookup(self, request: BahrainPayrollRateLookup) -> BahrainPayrollRate:
        matches = [
            rate
            for rate in self._rates
            if rate.worker_category == request.worker_category
            and rate.branch == request.branch
            and rate.payer == request.payer
            and rate.applies_on(request.as_of)
            and rate.applies_to_service_years(request.completed_service_years)
        ]
        if not matches:
            raise BahrainPayrollRateNotFoundError(
                "No source-backed Bahrain payroll rate exists for "
                f"{request.worker_category.value}/"
                f"{request.branch.value}/"
                f"{request.payer.value} on {request.as_of.isoformat()}."
            )
        if len(matches) > 1:
            raise ValueError(
                "Multiple Bahrain payroll rates matched; effective windows "
                "or service-year ranges overlap."
            )
        return matches[0]


BAHRAIN_PAYROLL_RATE_REGISTRY = BahrainPayrollRateRegistry(
    rates=(
        BahrainPayrollRate(
            code="non_bahraini_eosb_first_three_years",
            worker_category=BahrainWorkerCategory.NON_BAHRAINI_PRIVATE,
            branch=BahrainContributionBranch.EXPATRIATE_EOSB,
            payer=BahrainContributionPayer.EMPLOYER,
            percent=EOSB_FIRST_THREE_YEARS_CONTRIBUTION_RATE_PERCENT,
            effective_from=date.fromisoformat(str(EOSB_EFFECTIVE_DATE.value)),
            max_completed_service_years_exclusive=EOSB_FIRST_TIER_YEARS,
            note="Post-1-March-2024 funded EOSB contribution; first service tier.",
        ),
        BahrainPayrollRate(
            code="non_bahraini_eosb_after_three_years",
            worker_category=BahrainWorkerCategory.NON_BAHRAINI_PRIVATE,
            branch=BahrainContributionBranch.EXPATRIATE_EOSB,
            payer=BahrainContributionPayer.EMPLOYER,
            percent=EOSB_SUBSEQUENT_YEARS_CONTRIBUTION_RATE_PERCENT,
            effective_from=date.fromisoformat(str(EOSB_EFFECTIVE_DATE.value)),
            min_completed_service_years=EOSB_FIRST_TIER_YEARS,
            note="Post-1-March-2024 funded EOSB contribution; subsequent service tier.",
        ),
    )
)
