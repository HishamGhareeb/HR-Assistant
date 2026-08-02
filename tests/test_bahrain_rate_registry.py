from datetime import date
from decimal import Decimal

import pytest

from glue.bahrain_payroll.rate_registry import (
    BAHRAIN_PAYROLL_RATE_REGISTRY,
    BahrainContributionBranch,
    BahrainContributionPayer,
    BahrainPayrollRateLookup,
    BahrainPayrollRateNotFoundError,
    BahrainWorkerCategory,
)


def test_eosb_first_tier_rate_is_effective_dated() -> None:
    rate = BAHRAIN_PAYROLL_RATE_REGISTRY.lookup(
        BahrainPayrollRateLookup(
            worker_category=BahrainWorkerCategory.NON_BAHRAINI_PRIVATE,
            branch=BahrainContributionBranch.EXPATRIATE_EOSB,
            payer=BahrainContributionPayer.EMPLOYER,
            as_of=date.fromisoformat("2024-03-01"),
            completed_service_years=Decimal("2.999"),
        )
    )

    assert rate.code == "non_bahraini_eosb_first_three_years"
    assert Decimal(str(rate.percent.value)) == Decimal("4.2")
    assert rate.effective_from == date.fromisoformat("2024-03-01")


def test_eosb_subsequent_tier_rate_is_selected_after_three_completed_years() -> None:
    rate = BAHRAIN_PAYROLL_RATE_REGISTRY.lookup(
        BahrainPayrollRateLookup(
            worker_category=BahrainWorkerCategory.NON_BAHRAINI_PRIVATE,
            branch=BahrainContributionBranch.EXPATRIATE_EOSB,
            payer=BahrainContributionPayer.EMPLOYER,
            as_of=date.fromisoformat("2026-08-02"),
            completed_service_years=Decimal("3"),
        )
    )

    assert rate.code == "non_bahraini_eosb_after_three_years"
    assert Decimal(str(rate.percent.value)) == Decimal("8.4")


def test_rate_lookup_fails_before_effective_date() -> None:
    with pytest.raises(BahrainPayrollRateNotFoundError):
        BAHRAIN_PAYROLL_RATE_REGISTRY.lookup(
            BahrainPayrollRateLookup(
                worker_category=BahrainWorkerCategory.NON_BAHRAINI_PRIVATE,
                branch=BahrainContributionBranch.EXPATRIATE_EOSB,
                payer=BahrainContributionPayer.EMPLOYER,
                as_of=date.fromisoformat("2024-02-29"),
                completed_service_years=Decimal("1"),
            )
        )


def test_unsourced_bahraini_sio_rate_fails_closed() -> None:
    with pytest.raises(BahrainPayrollRateNotFoundError):
        BAHRAIN_PAYROLL_RATE_REGISTRY.lookup(
            BahrainPayrollRateLookup(
                worker_category=BahrainWorkerCategory.BAHRAINI_PRIVATE,
                branch=BahrainContributionBranch.OLD_AGE_DISABILITY_DEATH,
                payer=BahrainContributionPayer.EMPLOYER,
                as_of=date.fromisoformat("2026-08-02"),
            )
        )
