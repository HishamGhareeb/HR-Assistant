from datetime import date
from decimal import Decimal

import pytest

from glue.bahrain_payroll.rules.eosb import (
    BahrainEmploymentSector,
    BahrainWorkerNationalityCategory,
    EosbEligibilityInput,
    EosbGratuityInput,
    calculate_eosb_gratuity_amount,
    employer_non_payment_penalty_range,
    eosb_effective_date,
    eosb_monthly_contribution_rate_percent,
    eosb_monthly_employer_contribution,
    evaluate_eosb_eligibility,
)
from glue.bahrain_payroll.statutory_values import (
    EOSB_EMPLOYER_PENALTY_MAX_MULTIPLIER,
    EOSB_EMPLOYER_PENALTY_MIN_MULTIPLIER,
    EOSB_FIRST_THREE_YEARS_CONTRIBUTION_RATE_PERCENT,
    EOSB_FIRST_TIER_YEARS,
    EOSB_HALF_MONTH_DIVISOR,
    EOSB_SCOPE_CITATION,
    EOSB_SUBSEQUENT_YEARS_CONTRIBUTION_RATE_PERCENT,
)


def test_eosb_values_cite_official_source_inventory_and_human_interpretation() -> None:
    assert EOSB_FIRST_THREE_YEARS_CONTRIBUTION_RATE_PERCENT.citation.section == "§2a"
    assert EOSB_FIRST_THREE_YEARS_CONTRIBUTION_RATE_PERCENT.citation.instrument == "Decision No. (109) of 2023"
    assert EOSB_SUBSEQUENT_YEARS_CONTRIBUTION_RATE_PERCENT.citation.section == "§2a"
    assert EOSB_FIRST_TIER_YEARS.citation.section == "§2a"
    assert EOSB_HALF_MONTH_DIVISOR.citation.section == "§2a"
    assert EOSB_HALF_MONTH_DIVISOR.note is not None
    assert "monthly wage ÷ 2" in EOSB_HALF_MONTH_DIVISOR.note
    assert EOSB_SCOPE_CITATION.section == "§2a"
    assert EOSB_EMPLOYER_PENALTY_MIN_MULTIPLIER.citation.section == "§2a-ter"
    assert EOSB_EMPLOYER_PENALTY_MAX_MULTIPLIER.citation.section == "§2a-ter"


def test_private_non_bahraini_employee_covered_by_employment_injuries_is_eligible() -> None:
    result = evaluate_eosb_eligibility(
        EosbEligibilityInput(
            sector=BahrainEmploymentSector.PRIVATE,
            nationality_category=BahrainWorkerNationalityCategory.NON_BAHRAINI,
            employment_injuries_branch_covered=True,
        )
    )

    assert result.eligible
    assert result.reasons == ()


def test_eosb_scope_excludes_public_bahraini_gcc_and_article_3_categories() -> None:
    result = evaluate_eosb_eligibility(
        EosbEligibilityInput(
            sector=BahrainEmploymentSector.PUBLIC,
            nationality_category=BahrainWorkerNationalityCategory.GCC_NATIONAL,
            employment_injuries_branch_covered=False,
            social_insurance_law_article_3_excluded=True,
        )
    )

    assert not result.eligible
    assert result.reasons == (
        "EOSB applies to private-sector employees only.",
        "EOSB applies to non-Bahraini employees; Bahrainis and GCC nationals are out of scope.",
        "EOSB requires coverage under the Employment Injuries insurance branch.",
        "Employee is in a Social Insurance Law Article 3 excluded category.",
    )


def test_eosb_monthly_contribution_rate_is_4_2_percent_before_three_years() -> None:
    assert eosb_monthly_contribution_rate_percent(Decimal("2.999")) == Decimal("4.2")


def test_eosb_monthly_contribution_rate_is_8_4_percent_after_first_three_years() -> None:
    assert eosb_monthly_contribution_rate_percent(Decimal("3")) == Decimal("8.4")


def test_eosb_monthly_employer_contribution_uses_monthly_wage_base() -> None:
    assert eosb_monthly_employer_contribution(
        monthly_wage=Decimal("1000"),
        completed_service_years=Decimal("1"),
    ) == Decimal("42.000")
    assert eosb_monthly_employer_contribution(
        monthly_wage=Decimal("1000"),
        completed_service_years=Decimal("3"),
    ) == Decimal("84.000")


def test_eosb_gratuity_uses_monthly_wage_divided_by_two_for_first_three_years() -> None:
    result = calculate_eosb_gratuity_amount(
        EosbGratuityInput(
            monthly_basic_salary=Decimal("900"),
            monthly_social_allowance=Decimal("100"),
            service_years=Decimal("3"),
        )
    )

    assert result.monthly_wage_base == Decimal("1000")
    assert result.first_tier_years == Decimal("3")
    assert result.subsequent_tier_years == Decimal("0")
    assert result.amount == Decimal("1500.000")


def test_eosb_gratuity_uses_one_month_for_subsequent_years() -> None:
    result = calculate_eosb_gratuity_amount(
        EosbGratuityInput(
            monthly_basic_salary=Decimal("900"),
            monthly_social_allowance=Decimal("100"),
            service_years=Decimal("5"),
        )
    )

    assert result.first_tier_years == Decimal("3")
    assert result.subsequent_tier_years == Decimal("2")
    assert result.amount == Decimal("3500.000")


def test_eosb_gratuity_supports_fractional_service_years() -> None:
    result = calculate_eosb_gratuity_amount(
        EosbGratuityInput(
            monthly_basic_salary=Decimal("900"),
            monthly_social_allowance=Decimal("100"),
            service_years=Decimal("3.5"),
        )
    )

    assert result.first_tier_years == Decimal("3")
    assert result.subsequent_tier_years == Decimal("0.5")
    assert result.amount == Decimal("2000.000")


def test_eosb_gratuity_rejects_negative_inputs() -> None:
    with pytest.raises(ValueError, match="service_years cannot be negative"):
        calculate_eosb_gratuity_amount(
            EosbGratuityInput(
                monthly_basic_salary=Decimal("1000"),
                monthly_social_allowance=Decimal("0"),
                service_years=Decimal("-1"),
            )
        )


def test_employer_non_payment_penalty_range_is_unpaid_amount_to_three_times() -> None:
    penalty = employer_non_payment_penalty_range(Decimal("250.125"))

    assert penalty.minimum == Decimal("250.125")
    assert penalty.maximum == Decimal("750.375")


def test_employer_non_payment_penalty_rejects_negative_amount() -> None:
    with pytest.raises(ValueError, match="unpaid_contribution_amount cannot be negative"):
        employer_non_payment_penalty_range(Decimal("-1"))


def test_eosb_effective_date_is_march_2024() -> None:
    assert eosb_effective_date() == date.fromisoformat("2024-03-01")

