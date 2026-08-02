from datetime import date
from decimal import Decimal

import pytest

from glue.bahrain_payroll.rate_registry import (
    BahrainContributionPayer,
    BahrainPayrollRateNotFoundError,
    BahrainWorkerCategory,
)
from glue.bahrain_payroll.rules.sio_contributions import (
    bahraini_pension_employee_contribution,
    bahraini_pension_employer_contribution,
    employment_injury_contribution,
    unemployment_insurance_contribution,
)


# --- Bahraini pension branch (Article 33, Law 14/2022): employee share ----


def test_bahraini_pension_employee_rate_is_6_percent_before_2023() -> None:
    result = bahraini_pension_employee_contribution(
        monthly_wage=Decimal("1000"),
        as_of=date.fromisoformat("2022-12-31"),
    )

    assert result.rate_percent == Decimal("6")
    assert result.amount == Decimal("60.000")
    assert result.rate_code == "bahraini_pension_employee_initial"


def test_bahraini_pension_employee_rate_is_7_percent_from_2023() -> None:
    result = bahraini_pension_employee_contribution(
        monthly_wage=Decimal("1000"),
        as_of=date.fromisoformat("2023-01-01"),
    )

    assert result.rate_percent == Decimal("7")
    assert result.amount == Decimal("70.000")
    assert result.rate_code == "bahraini_pension_employee_target"


def test_bahraini_pension_employee_rate_still_7_percent_in_2026() -> None:
    result = bahraini_pension_employee_contribution(
        monthly_wage=Decimal("1000"),
        as_of=date.fromisoformat("2026-08-02"),
    )

    assert result.rate_percent == Decimal("7")


def test_bahraini_pension_employee_rate_fails_closed_before_law_enforcement() -> None:
    with pytest.raises(BahrainPayrollRateNotFoundError):
        bahraini_pension_employee_contribution(
            monthly_wage=Decimal("1000"),
            as_of=date.fromisoformat("2022-04-18"),
        )


def test_bahraini_pension_employer_share_fails_closed_by_design() -> None:
    """The employer share's phase-in trigger date is not source-confirmed.

    This must never silently return a number -- see
    docs/BAHRAIN_RATE_VERSIONING.md for the scope decision.
    """

    with pytest.raises(BahrainPayrollRateNotFoundError):
        bahraini_pension_employer_contribution(
            monthly_wage=Decimal("1000"),
            as_of=date.fromisoformat("2026-08-02"),
        )


# --- Employment injury (Decree-Law 24/1976 Article 47): withheld ----------


def test_employment_injury_fails_closed_for_bahraini_by_design() -> None:
    """3% is documented but amendment currency is not fully confirmed."""

    with pytest.raises(BahrainPayrollRateNotFoundError):
        employment_injury_contribution(
            worker_category=BahrainWorkerCategory.BAHRAINI_PRIVATE,
            monthly_wage=Decimal("1000"),
            as_of=date.fromisoformat("2026-08-02"),
        )


def test_employment_injury_fails_closed_for_non_bahraini_by_design() -> None:
    with pytest.raises(BahrainPayrollRateNotFoundError):
        employment_injury_contribution(
            worker_category=BahrainWorkerCategory.NON_BAHRAINI_PRIVATE,
            monthly_wage=Decimal("1000"),
            as_of=date.fromisoformat("2026-08-02"),
        )


# --- Unemployment insurance (Law 78/2006 Article 6): nationality-neutral --


@pytest.mark.parametrize(
    "category",
    [BahrainWorkerCategory.BAHRAINI_PRIVATE, BahrainWorkerCategory.NON_BAHRAINI_PRIVATE],
)
def test_unemployment_employee_share_is_1_percent_for_both_categories(
    category: BahrainWorkerCategory,
) -> None:
    result = unemployment_insurance_contribution(
        worker_category=category,
        payer=BahrainContributionPayer.EMPLOYEE,
        monthly_wage=Decimal("1000"),
        as_of=date.fromisoformat("2026-08-02"),
    )

    assert result.rate_percent == Decimal("1")
    assert result.amount == Decimal("10.000")


@pytest.mark.parametrize(
    "category",
    [BahrainWorkerCategory.BAHRAINI_PRIVATE, BahrainWorkerCategory.NON_BAHRAINI_PRIVATE],
)
def test_unemployment_labour_fund_share_is_1_percent_not_employer(
    category: BahrainWorkerCategory,
) -> None:
    result = unemployment_insurance_contribution(
        worker_category=category,
        payer=BahrainContributionPayer.LABOUR_FUND,
        monthly_wage=Decimal("1000"),
        as_of=date.fromisoformat("2026-08-02"),
    )

    assert result.rate_percent == Decimal("1")
    assert result.payer == BahrainContributionPayer.LABOUR_FUND


def test_unemployment_employer_payer_fails_closed_private_sector_does_not_pay_directly() -> None:
    """Private-sector employers do not pay this branch -- Tamkeen does.

    Requesting BahrainContributionPayer.EMPLOYER must fail closed rather
    than silently returning the Labour Fund's rate under the wrong payer.
    """

    with pytest.raises(BahrainPayrollRateNotFoundError):
        unemployment_insurance_contribution(
            worker_category=BahrainWorkerCategory.BAHRAINI_PRIVATE,
            payer=BahrainContributionPayer.EMPLOYER,
            monthly_wage=Decimal("1000"),
            as_of=date.fromisoformat("2026-08-02"),
        )


def test_unemployment_government_share_is_1_percent() -> None:
    result = unemployment_insurance_contribution(
        worker_category=BahrainWorkerCategory.NON_BAHRAINI_PRIVATE,
        payer=BahrainContributionPayer.GOVERNMENT,
        monthly_wage=Decimal("1000"),
        as_of=date.fromisoformat("2026-08-02"),
    )

    assert result.rate_percent == Decimal("1")


# --- Unsupported worker categories fail closed across every branch --------


@pytest.mark.parametrize(
    "category",
    [
        BahrainWorkerCategory.GCC_PRIVATE,
        BahrainWorkerCategory.DOMESTIC_WORKER,
        BahrainWorkerCategory.PUBLIC_SECTOR,
        BahrainWorkerCategory.SELF_EMPLOYED,
        BahrainWorkerCategory.FLEXI_OR_SUCCESSOR,
    ],
)
def test_unemployment_fails_closed_for_unsupported_categories(
    category: BahrainWorkerCategory,
) -> None:
    with pytest.raises(BahrainPayrollRateNotFoundError):
        unemployment_insurance_contribution(
            worker_category=category,
            payer=BahrainContributionPayer.EMPLOYEE,
            monthly_wage=Decimal("1000"),
            as_of=date.fromisoformat("2026-08-02"),
        )


# --- Input validation ------------------------------------------------------


def test_negative_wage_is_rejected() -> None:
    with pytest.raises(ValueError, match="monthly_wage cannot be negative"):
        bahraini_pension_employee_contribution(
            monthly_wage=Decimal("-1"),
            as_of=date.fromisoformat("2026-08-02"),
        )
