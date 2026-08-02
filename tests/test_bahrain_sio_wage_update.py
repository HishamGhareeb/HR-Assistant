from decimal import Decimal

from glue.bahrain_payroll.rules.sio_wage_update import (
    SioWageComponents,
    SioWageUpdateSubmission,
    SioWageUpdateType,
    contribution_scope_components,
    validate_sio_wage_update,
)
from glue.bahrain_payroll.statutory_values import (
    SIO_CONTRIBUTION_SCOPE_CITATION,
    SIO_IMMUTABLE_FIELDS_CITATION,
    SIO_NO_SALARY_DECREASE_CITATION,
    SIO_SALARY_INCREASE_CAP_PERCENT,
    SIO_TOTAL_ALLOWANCES_CITATION,
)


def test_sio_wage_update_values_cite_official_source_inventory() -> None:
    assert SIO_SALARY_INCREASE_CAP_PERCENT.citation.section == "§2a-ter"
    assert SIO_SALARY_INCREASE_CAP_PERCENT.citation.instrument == "SIO employer wage-reporting guides"
    assert SIO_NO_SALARY_DECREASE_CITATION.section == "§2a-ter"
    assert SIO_TOTAL_ALLOWANCES_CITATION.section == "§2a-ter"
    assert SIO_CONTRIBUTION_SCOPE_CITATION.section == "§2a-ter"
    assert SIO_IMMUTABLE_FIELDS_CITATION.section == "§2a-ter"


def test_valid_sio_wage_update_passes() -> None:
    result = validate_sio_wage_update(_submission())

    assert result.is_valid
    assert result.errors == ()


def test_rejects_salary_increase_above_40_percent_cap() -> None:
    result = validate_sio_wage_update(
        _submission(
            previous_components=SioWageComponents(basic_salary=Decimal("1000")),
            new_components=SioWageComponents(basic_salary=Decimal("1400.001")),
        )
    )

    assert not result.is_valid
    assert _error_codes(result) == {"sio_salary_increase_cap_exceeded"}


def test_allows_salary_increase_at_40_percent_cap() -> None:
    result = validate_sio_wage_update(
        _submission(
            previous_components=SioWageComponents(basic_salary=Decimal("1000")),
            new_components=SioWageComponents(basic_salary=Decimal("1400")),
        )
    )

    assert result.is_valid


def test_rejects_salary_decrease() -> None:
    result = validate_sio_wage_update(
        _submission(
            previous_components=SioWageComponents(basic_salary=Decimal("1000")),
            new_components=SioWageComponents(basic_salary=Decimal("999.999")),
        )
    )

    assert not result.is_valid
    assert _error_codes(result) == {"sio_salary_decrease_not_permitted"}


def test_rejects_total_allowances_above_basic_salary() -> None:
    result = validate_sio_wage_update(
        _submission(
            new_components=SioWageComponents(
                basic_salary=Decimal("500"),
                social_allowance=Decimal("250"),
                housing_allowance=Decimal("251"),
            )
        )
    )

    assert not result.is_valid
    assert _error_codes(result) == {"sio_total_allowances_exceed_basic_salary"}


def test_rejects_immutable_field_changes() -> None:
    result = validate_sio_wage_update(
        _submission(
            submitted_cpr_number="999999999",
            submitted_employee_name="Changed Name",
            submitted_total_previous_earnings=Decimal("999"),
        )
    )

    assert not result.is_valid
    assert _error_codes(result) == {"sio_immutable_fields_changed"}
    assert "CPR number" in result.errors[0].message
    assert "employee name" in result.errors[0].message
    assert "Total Previous Earnings" in result.errors[0].message


def test_annual_update_scope_uses_all_salary_components() -> None:
    components = _rich_components()

    scoped = contribution_scope_components(SioWageUpdateType.ANNUAL, components)

    assert scoped == components.as_component_map()


def test_monthly_update_scope_uses_basic_plus_social_only() -> None:
    components = _rich_components()

    scoped = contribution_scope_components(SioWageUpdateType.MONTHLY, components)

    assert scoped == {
        "basic_salary": Decimal("600"),
        "social_allowance": Decimal("75"),
    }


def _submission(
    *,
    update_type: SioWageUpdateType = SioWageUpdateType.MONTHLY,
    previous_cpr_number: str = "800000001",
    submitted_cpr_number: str = "800000001",
    previous_employee_name: str = "Ahmed Hassan",
    submitted_employee_name: str = "Ahmed Hassan",
    previous_total_earnings: Decimal = Decimal("1000"),
    submitted_total_previous_earnings: Decimal = Decimal("1000"),
    previous_components: SioWageComponents | None = None,
    new_components: SioWageComponents | None = None,
) -> SioWageUpdateSubmission:
    return SioWageUpdateSubmission(
        update_type=update_type,
        previous_cpr_number=previous_cpr_number,
        submitted_cpr_number=submitted_cpr_number,
        previous_employee_name=previous_employee_name,
        submitted_employee_name=submitted_employee_name,
        previous_total_earnings=previous_total_earnings,
        submitted_total_previous_earnings=submitted_total_previous_earnings,
        previous_components=previous_components
        or SioWageComponents(basic_salary=Decimal("1000")),
        new_components=new_components
        or SioWageComponents(basic_salary=Decimal("1100")),
    )


def _rich_components() -> SioWageComponents:
    return SioWageComponents(
        basic_salary=Decimal("600"),
        social_allowance=Decimal("75"),
        housing_allowance=Decimal("100"),
        transportation_allowance=Decimal("20"),
        telephone_allowance=Decimal("10"),
        supervision_allowance=Decimal("15"),
        shift_allowance=Decimal("25"),
        nature_of_work_allowance=Decimal("30"),
        commission=Decimal("50"),
        sales_revenue_percentage=Decimal("40"),
        annual_bonus=Decimal("200"),
    )


def _error_codes(result) -> set[str]:
    return {error.code for error in result.errors}

