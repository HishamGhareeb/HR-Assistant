from datetime import date
from decimal import Decimal

import pytest

from glue.bahrain_payroll.rate_registry import BahrainPayrollRateNotFoundError
from glue.bahrain_payroll.rules.eosb_transition import (
    EosbSplitGratuityInput,
    calculate_eosb_gratuity_with_pre_post_split,
    eosb_monthly_contribution_rate_percent_with_article_13_transition,
    eosb_monthly_employer_contribution_with_article_13_transition,
    split_eosb_service_years,
)


# --- Service-period splitting -----------------------------------------------


def test_employee_hired_and_terminated_entirely_before_march_2024_is_all_pre_period() -> None:
    split = split_eosb_service_years(
        hire_date=date.fromisoformat("2018-03-01"),
        termination_date=date.fromisoformat("2023-03-01"),
    )

    # 1826 calendar days (includes one leap day) / 365 -- day-count-based
    # year conversion is a NON_STATUTORY_NUMBER convention, not a legal one.
    assert split.pre_march_2024_years == Decimal("1826") / Decimal("365")
    assert split.post_march_2024_years == Decimal("0")


def test_employee_hired_and_terminated_entirely_after_march_2024_is_all_post_period() -> None:
    split = split_eosb_service_years(
        hire_date=date.fromisoformat("2024-03-01"),
        termination_date=date.fromisoformat("2026-03-01"),
    )

    assert split.pre_march_2024_years == Decimal("0")
    assert split.post_march_2024_years == Decimal("2")


def test_employee_spanning_the_boundary_is_split_into_both_periods() -> None:
    split = split_eosb_service_years(
        hire_date=date.fromisoformat("2020-03-01"),
        termination_date=date.fromisoformat("2026-03-01"),
    )

    # 1461 pre-period days (includes the 2020 and 2024 leap days) / 365.
    assert split.pre_march_2024_years == Decimal("1461") / Decimal("365")
    # Post-period starts exactly at 2024-03-01 (after that year's leap day),
    # so it is an exact whole-year span with no leap-day noise.
    assert split.post_march_2024_years == Decimal("2")


def test_split_rejects_termination_before_hire() -> None:
    with pytest.raises(ValueError, match="termination_date cannot be before hire_date"):
        split_eosb_service_years(
            hire_date=date.fromisoformat("2024-03-01"),
            termination_date=date.fromisoformat("2020-03-01"),
        )


# --- Gratuity amount: pre-period (employer-direct) vs post-period (SIO-funded) --


def test_gratuity_for_hire_entirely_post_march_2024_has_zero_pre_period_liability() -> None:
    result = calculate_eosb_gratuity_with_pre_post_split(
        EosbSplitGratuityInput(
            monthly_basic_salary=Decimal("900"),
            monthly_social_allowance=Decimal("100"),
            hire_date=date.fromisoformat("2024-03-01"),
            termination_date=date.fromisoformat("2026-03-01"),
        )
    )

    assert result.pre_march_2024_employer_direct_liability == Decimal("0.000")
    # 2 years, both within the post-period's own first tier (< 3 years):
    # 1000 / 2 * 2 = 1000
    assert result.post_march_2024_sio_funded_amount == Decimal("1000.000")
    assert result.total_amount == Decimal("1000.000")


def test_gratuity_for_hire_entirely_pre_march_2024_has_zero_post_period_liability() -> None:
    result = calculate_eosb_gratuity_with_pre_post_split(
        EosbSplitGratuityInput(
            monthly_basic_salary=Decimal("900"),
            monthly_social_allowance=Decimal("100"),
            hire_date=date.fromisoformat("2018-03-01"),
            termination_date=date.fromisoformat("2023-03-01"),
        )
    )

    # ~5.0027 years pre-period (1826 days / 365): first 3 years at
    # half-month, ~2.0027 subsequent years at full month.
    assert result.pre_march_2024_employer_direct_liability == Decimal("3502.740")
    assert result.post_march_2024_sio_funded_amount == Decimal("0.000")
    assert result.total_amount == Decimal("3502.740")


def test_gratuity_spanning_the_boundary_reports_both_portions_separately() -> None:
    result = calculate_eosb_gratuity_with_pre_post_split(
        EosbSplitGratuityInput(
            monthly_basic_salary=Decimal("900"),
            monthly_social_allowance=Decimal("100"),
            hire_date=date.fromisoformat("2020-03-01"),
            termination_date=date.fromisoformat("2026-03-01"),
        )
    )

    # Pre-period: ~4.0027 years (1461 days / 365) -- first 3 at half-month,
    # ~1.0027 subsequent at full month.
    assert result.pre_march_2024_employer_direct_liability == Decimal("2502.740")
    # Post-period: exactly 2 years, entirely within its own first tier: 1000/2*2 = 1000
    assert result.post_march_2024_sio_funded_amount == Decimal("1000.000")
    assert result.total_amount == Decimal("3502.740")
    assert result.service_split.pre_march_2024_years == Decimal("1461") / Decimal("365")
    assert result.service_split.post_march_2024_years == Decimal("2")


def test_gratuity_rejects_negative_wage_base() -> None:
    with pytest.raises(ValueError, match="monthly wage base cannot be negative"):
        calculate_eosb_gratuity_with_pre_post_split(
            EosbSplitGratuityInput(
                monthly_basic_salary=Decimal("-1"),
                monthly_social_allowance=Decimal("0"),
                hire_date=date.fromisoformat("2024-03-01"),
                termination_date=date.fromisoformat("2025-03-01"),
            )
        )


# --- Monthly contribution rate: Article 13 transition ----------------------


def test_article_13_transition_gives_flat_8_4_percent_for_over_three_years_pre_2024_service() -> None:
    rate = eosb_monthly_contribution_rate_percent_with_article_13_transition(
        total_completed_service_years=Decimal("4.1"),
        pre_march_2024_completed_service_years=Decimal("4"),
        as_of=date.fromisoformat("2024-03-01"),
    )

    assert rate == Decimal("8.4")


def test_article_13_transition_falls_back_to_standard_schedule_at_or_under_threshold() -> None:
    rate = eosb_monthly_contribution_rate_percent_with_article_13_transition(
        total_completed_service_years=Decimal("2.999"),
        pre_march_2024_completed_service_years=Decimal("2.999"),
        as_of=date.fromisoformat("2024-03-01"),
    )

    assert rate == Decimal("4.2")


def test_article_13_transition_fails_closed_before_scheme_effective_date() -> None:
    """No SIO-fund contribution exists for any month before 2024-03-01,
    inherited automatically from the underlying rate registry."""

    with pytest.raises(BahrainPayrollRateNotFoundError):
        eosb_monthly_contribution_rate_percent_with_article_13_transition(
            total_completed_service_years=Decimal("1"),
            pre_march_2024_completed_service_years=Decimal("1"),
            as_of=date.fromisoformat("2024-02-29"),
        )


def test_employer_contribution_with_article_13_transition_uses_flat_rate() -> None:
    amount = eosb_monthly_employer_contribution_with_article_13_transition(
        monthly_wage=Decimal("1000"),
        total_completed_service_years=Decimal("4.1"),
        pre_march_2024_completed_service_years=Decimal("4"),
        as_of=date.fromisoformat("2024-03-01"),
    )

    assert amount == Decimal("84.000")
