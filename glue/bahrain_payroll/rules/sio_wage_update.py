"""SIO wage-update validation rules for Bahrain employers.

Sources:
- ``docs/BAHRAIN_PAYROLL_SOURCES.md`` §2a-ter: SIO employer wage-reporting
  guides and Taminat wage-update guidance.

This module validates employer wage-update submissions and selects the correct
salary-component scope for downstream deterministic contribution calculations.
It does not calculate statutory contribution amounts.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from glue.bahrain_payroll.statutory_values import SIO_SALARY_INCREASE_CAP_PERCENT


class SioWageUpdateType(str, Enum):
    ANNUAL = "annual"
    MONTHLY = "monthly"


@dataclass(frozen=True)
class SioWageComponents:
    basic_salary: Decimal
    social_allowance: Decimal = Decimal("0")
    housing_allowance: Decimal = Decimal("0")
    transportation_allowance: Decimal = Decimal("0")
    telephone_allowance: Decimal = Decimal("0")
    supervision_allowance: Decimal = Decimal("0")
    shift_allowance: Decimal = Decimal("0")
    nature_of_work_allowance: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    sales_revenue_percentage: Decimal = Decimal("0")
    annual_bonus: Decimal = Decimal("0")

    @property
    def total_allowances(self) -> Decimal:
        return sum(
            (
                self.social_allowance,
                self.housing_allowance,
                self.transportation_allowance,
                self.telephone_allowance,
                self.supervision_allowance,
                self.shift_allowance,
                self.nature_of_work_allowance,
            ),
            Decimal("0"),
        )

    @property
    def total_salary(self) -> Decimal:
        return sum(self.as_component_map().values(), Decimal("0"))

    def as_component_map(self) -> dict[str, Decimal]:
        return {
            "basic_salary": self.basic_salary,
            "social_allowance": self.social_allowance,
            "housing_allowance": self.housing_allowance,
            "transportation_allowance": self.transportation_allowance,
            "telephone_allowance": self.telephone_allowance,
            "supervision_allowance": self.supervision_allowance,
            "shift_allowance": self.shift_allowance,
            "nature_of_work_allowance": self.nature_of_work_allowance,
            "commission": self.commission,
            "sales_revenue_percentage": self.sales_revenue_percentage,
            "annual_bonus": self.annual_bonus,
        }


@dataclass(frozen=True)
class SioWageUpdateSubmission:
    update_type: SioWageUpdateType
    previous_cpr_number: str
    submitted_cpr_number: str
    previous_employee_name: str
    submitted_employee_name: str
    previous_total_earnings: Decimal
    submitted_total_previous_earnings: Decimal
    previous_components: SioWageComponents
    new_components: SioWageComponents


@dataclass(frozen=True)
class SioWageUpdateValidationError:
    code: str
    message: str


@dataclass(frozen=True)
class SioWageUpdateValidationResult:
    errors: tuple[SioWageUpdateValidationError, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_sio_wage_update(
    submission: SioWageUpdateSubmission,
) -> SioWageUpdateValidationResult:
    errors: list[SioWageUpdateValidationError] = []
    errors.extend(_validate_immutable_fields(submission))
    errors.extend(_validate_no_salary_decrease(submission))
    errors.extend(_validate_salary_increase_cap(submission))
    errors.extend(_validate_allowances_do_not_exceed_basic_salary(submission))
    return SioWageUpdateValidationResult(errors=tuple(errors))


def contribution_scope_components(
    update_type: SioWageUpdateType,
    components: SioWageComponents,
) -> dict[str, Decimal]:
    """Return the salary components applicable to the update type.

    Annual SIO updates use every salary component in the submitted file. Monthly
    EOSB contribution scope uses only basic salary plus social allowance.
    """

    if update_type == SioWageUpdateType.ANNUAL:
        return components.as_component_map()
    return {
        "basic_salary": components.basic_salary,
        "social_allowance": components.social_allowance,
    }


def _validate_immutable_fields(
    submission: SioWageUpdateSubmission,
) -> list[SioWageUpdateValidationError]:
    changed_fields: list[str] = []
    if submission.previous_cpr_number != submission.submitted_cpr_number:
        changed_fields.append("CPR number")
    if submission.previous_employee_name != submission.submitted_employee_name:
        changed_fields.append("employee name")
    if submission.previous_total_earnings != submission.submitted_total_previous_earnings:
        changed_fields.append("Total Previous Earnings")
    if not changed_fields:
        return []
    return [
        SioWageUpdateValidationError(
            code="sio_immutable_fields_changed",
            message=f"SIO wage-update file cannot modify: {', '.join(changed_fields)}.",
        )
    ]


def _validate_no_salary_decrease(
    submission: SioWageUpdateSubmission,
) -> list[SioWageUpdateValidationError]:
    if submission.new_components.total_salary >= submission.previous_components.total_salary:
        return []
    return [
        SioWageUpdateValidationError(
            code="sio_salary_decrease_not_permitted",
            message="SIO wage update cannot decrease salary.",
        )
    ]


def _validate_salary_increase_cap(
    submission: SioWageUpdateSubmission,
) -> list[SioWageUpdateValidationError]:
    previous_salary = submission.previous_components.total_salary
    new_salary = submission.new_components.total_salary
    allowed_increase = previous_salary * (
        Decimal(str(SIO_SALARY_INCREASE_CAP_PERCENT.value)) / Decimal("100")
    )
    if new_salary <= previous_salary + allowed_increase:
        return []
    return [
        SioWageUpdateValidationError(
            code="sio_salary_increase_cap_exceeded",
            message=(
                "SIO wage update exceeds the official salary-increase cap of "
                f"{SIO_SALARY_INCREASE_CAP_PERCENT.value}%."
            ),
        )
    ]


def _validate_allowances_do_not_exceed_basic_salary(
    submission: SioWageUpdateSubmission,
) -> list[SioWageUpdateValidationError]:
    if submission.new_components.total_allowances <= submission.new_components.basic_salary:
        return []
    return [
        SioWageUpdateValidationError(
            code="sio_total_allowances_exceed_basic_salary",
            message="SIO wage update cannot have total allowances above basic salary.",
        )
    ]

