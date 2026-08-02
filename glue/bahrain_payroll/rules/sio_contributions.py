"""Bahrain SIO standard contribution rule pack (HIS-68, HIS-69).

Covers the old-age/disability/death pension branch (Bahraini employees),
employment injury, and unemployment insurance -- explicitly separate from
the non-Bahraini EOSB scheme (``glue.bahrain_payroll.rules.eosb``).

Shared between HIS-68 (Bahraini SIO) and HIS-69 (non-Bahraini standard SIO)
because the employment-injury and unemployment-insurance branches are
nationality-neutral per docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md §1 -- one
implementation, two worker categories, rather than duplicated logic.

Sources:
- ``docs/BAHRAIN_SIO_CONTRIBUTION_RATES.md`` §1: Article 33 pension branch,
  Law No. (14) of 2022 phase-in.
- ``docs/BAHRAIN_NON_BAHRAINI_SIO_RATES.md`` §1: employment injury (Article
  47) and unemployment insurance (Law 78/2006 Article 6) branches.
- ``docs/BAHRAIN_RATE_VERSIONING.md``: the standing scope decision on which
  of these rates are executable today versus deliberately withheld.

Every calculation here goes through
``glue.bahrain_payroll.rate_registry.BAHRAIN_PAYROLL_RATE_REGISTRY``. There
is no special-cased "unsupported" branch: an unregistered combination (the
Bahraini pension employer share, employment injury, GCC nationals, domestic
workers, public sector, self-employed, Flexi/successor categories) simply
has no matching rate row, so the registry's own fail-closed lookup raises
``BahrainPayrollRateNotFoundError`` -- this module never guesses a number
for those cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from glue.bahrain_payroll.rate_registry import (
    BAHRAIN_PAYROLL_RATE_REGISTRY,
    BahrainContributionBranch,
    BahrainContributionPayer,
    BahrainPayrollRateLookup,
    BahrainWorkerCategory,
)


@dataclass(frozen=True)
class SioContributionResult:
    """One payer's contribution amount for one branch, with its rate context."""

    worker_category: BahrainWorkerCategory
    branch: BahrainContributionBranch
    payer: BahrainContributionPayer
    rate_percent: Decimal
    monthly_wage: Decimal
    amount: Decimal
    rate_code: str


def _contribution(
    worker_category: BahrainWorkerCategory,
    branch: BahrainContributionBranch,
    payer: BahrainContributionPayer,
    monthly_wage: Decimal,
    as_of: date,
) -> SioContributionResult:
    if monthly_wage < Decimal("0"):  # NON_STATUTORY_NUMBER: zero is the mathematical lower bound for wages.
        raise ValueError("monthly_wage cannot be negative")

    rate = BAHRAIN_PAYROLL_RATE_REGISTRY.lookup(
        BahrainPayrollRateLookup(
            worker_category=worker_category,
            branch=branch,
            payer=payer,
            as_of=as_of,
        )
    )
    rate_percent = Decimal(str(rate.percent.value))
    return SioContributionResult(
        worker_category=worker_category,
        branch=branch,
        payer=payer,
        rate_percent=rate_percent,
        monthly_wage=monthly_wage,
        amount=_money(monthly_wage * rate_percent / Decimal("100")),
        rate_code=rate.code,
    )


def bahraini_pension_employee_contribution(
    monthly_wage: Decimal,
    as_of: date,
) -> SioContributionResult:
    """Old-age/disability/death pension branch, employee share.

    The employer share is intentionally not implemented here -- see the
    module docstring and docs/BAHRAIN_RATE_VERSIONING.md. Calling
    ``bahraini_pension_employer_contribution`` raises
    ``BahrainPayrollRateNotFoundError`` by design, not by omission.
    """

    return _contribution(
        worker_category=BahrainWorkerCategory.BAHRAINI_PRIVATE,
        branch=BahrainContributionBranch.OLD_AGE_DISABILITY_DEATH,
        payer=BahrainContributionPayer.EMPLOYEE,
        monthly_wage=monthly_wage,
        as_of=as_of,
    )


def bahraini_pension_employer_contribution(
    monthly_wage: Decimal,
    as_of: date,
) -> SioContributionResult:
    """Old-age/disability/death pension branch, employer share.

    Deliberately unregistered: the exact annual step-up trigger date for the
    employer's 11%->17% phase-in (Law 14/2022) is not source-confirmed. This
    call fails closed with ``BahrainPayrollRateNotFoundError`` until a human
    /payroll reviewer confirms the trigger convention and a follow-up ticket
    adds the rate rows.
    """

    return _contribution(
        worker_category=BahrainWorkerCategory.BAHRAINI_PRIVATE,
        branch=BahrainContributionBranch.OLD_AGE_DISABILITY_DEATH,
        payer=BahrainContributionPayer.EMPLOYER,
        monthly_wage=monthly_wage,
        as_of=as_of,
    )


def employment_injury_contribution(
    worker_category: BahrainWorkerCategory,
    monthly_wage: Decimal,
    as_of: date,
) -> SioContributionResult:
    """Employment injury branch, employer-only, nationality-neutral.

    Deliberately unregistered: the 3% rate's amendment currency is not fully
    confirmed (LLOC pagination for this law's older amendments could not be
    reached). Fails closed with ``BahrainPayrollRateNotFoundError`` until
    that verification pass completes.
    """

    return _contribution(
        worker_category=worker_category,
        branch=BahrainContributionBranch.EMPLOYMENT_INJURY,
        payer=BahrainContributionPayer.EMPLOYER,
        monthly_wage=monthly_wage,
        as_of=as_of,
    )


def unemployment_insurance_contribution(
    worker_category: BahrainWorkerCategory,
    payer: BahrainContributionPayer,
    monthly_wage: Decimal,
    as_of: date,
) -> SioContributionResult:
    """Unemployment insurance branch (Law 78/2006 Article 6).

    Nationality-neutral: works identically for
    ``BahrainWorkerCategory.BAHRAINI_PRIVATE`` and
    ``BahrainWorkerCategory.NON_BAHRAINI_PRIVATE``. The private-sector
    "employer share" is paid by the Labour Fund (Tamkeen), not the employer
    -- callers must pass ``BahrainContributionPayer.LABOUR_FUND``, not
    ``EMPLOYER``, to get that share; passing ``EMPLOYER`` fails closed since
    no such rate is registered (private-sector employers do not pay this
    branch directly).
    """

    return _contribution(
        worker_category=worker_category,
        branch=BahrainContributionBranch.UNEMPLOYMENT,
        payer=payer,
        monthly_wage=monthly_wage,
        as_of=as_of,
    )


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
