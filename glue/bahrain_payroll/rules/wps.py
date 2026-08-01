"""Bahrain Wages Protection System validation rules.

Sources:
- ``docs/BAHRAIN_PAYROLL_SOURCES.md`` §2a-ter: WPS User Manual v2
- ``docs/BAHRAIN_PAYROLL_SOURCES.md`` §2c: Resolution 68/2019 legal basis

This module validates submission shape and approval flow only. It does not
calculate wages, social insurance, or end-of-service benefits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

from glue.bahrain_payroll.statutory_values import (
    WPS_ADVANCE_SCHEDULING_WINDOW_DAYS,
    WPS_MAX_WORKER_RECORDS_PER_FILE,
)


class WpsPaymentStatus(str, Enum):
    PAID = "paid"
    PARTIAL = "partial"
    NOT_PAID = "not_paid"


class WpsRole(str, Enum):
    MAKER = "maker"
    CHECKER = "checker"
    WRP = "wage_responsible_person"


class WpsApprovalActionType(str, Enum):
    PREPARE = "prepare"
    APPROVE = "approve"


@dataclass(frozen=True)
class WpsWorkerPayment:
    employee_full_name: str
    employee_id_number: str
    wage_amount: Decimal
    payment_date: date
    employee_account_identifier: str
    employer_account_number: str
    employer_id_cr_number: str
    fixed_salary: Decimal
    social_allowance: Decimal
    variable_salary: Decimal
    payment_status: WpsPaymentStatus = WpsPaymentStatus.PAID


@dataclass(frozen=True)
class WpsApprovalAction:
    actor_user_id: str
    role: WpsRole
    action: WpsApprovalActionType
    acted_at: date


@dataclass(frozen=True)
class WpsNonPaymentJustification:
    employee_id_number: str
    payroll_month: str
    reason: str
    supporting_document_refs: tuple[str, ...]
    wps_commitment_level: str
    offense_code: str


@dataclass(frozen=True)
class WpsSalaryFile:
    payroll_month: str
    scheduled_transfer_date: date
    actual_transfer_date: date
    worker_payments: tuple[WpsWorkerPayment, ...]
    approvals: tuple[WpsApprovalAction, ...]
    non_payment_justifications: tuple[WpsNonPaymentJustification, ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class WpsValidationError:
    code: str
    message: str
    employee_id_number: str | None = None


@dataclass(frozen=True)
class WpsValidationResult:
    errors: tuple[WpsValidationError, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_wps_salary_file(salary_file: WpsSalaryFile) -> WpsValidationResult:
    errors: list[WpsValidationError] = []
    errors.extend(_validate_record_cap(salary_file))
    errors.extend(_validate_transfer_window(salary_file))
    errors.extend(_validate_worker_records(salary_file))
    errors.extend(_validate_approval_sequence(salary_file))
    errors.extend(_validate_non_payment_workflow(salary_file))
    return WpsValidationResult(errors=tuple(errors))


def _validate_record_cap(salary_file: WpsSalaryFile) -> list[WpsValidationError]:
    max_records = int(WPS_MAX_WORKER_RECORDS_PER_FILE.value)
    if len(salary_file.worker_payments) <= max_records:
        return []
    return [
        WpsValidationError(
            code="wps_file_record_cap_exceeded",
            message=(
                "WPS salary file contains "
                f"{len(salary_file.worker_payments)} worker records; maximum is {max_records}. "
                "Split larger employers into multiple files."
            ),
        )
    ]


def _validate_transfer_window(salary_file: WpsSalaryFile) -> list[WpsValidationError]:
    window_days = int(WPS_ADVANCE_SCHEDULING_WINDOW_DAYS.value)
    days_before_transfer = (
        salary_file.actual_transfer_date - salary_file.scheduled_transfer_date
    ).days
    if days_before_transfer < 0:  # NON_STATUTORY_NUMBER: zero means scheduled date is after actual date.
        return [
            WpsValidationError(
                code="wps_transfer_date_after_actual_date",
                message="Scheduled transfer date cannot be after the actual transfer date.",
            )
        ]
    if days_before_transfer > window_days:
        return [
            WpsValidationError(
                code="wps_transfer_date_too_early",
                message=(
                    "Scheduled transfer date is outside the official WPS advance "
                    f"scheduling window of {window_days} days."
                ),
            )
        ]
    return []


def _validate_worker_records(salary_file: WpsSalaryFile) -> list[WpsValidationError]:
    errors: list[WpsValidationError] = []
    for worker in salary_file.worker_payments:
        missing = _missing_required_fields(worker)
        if missing:
            errors.append(
                WpsValidationError(
                    code="wps_missing_required_disclosure_fields",
                    employee_id_number=worker.employee_id_number or None,
                    message=f"WPS worker payment is missing required fields: {', '.join(missing)}.",
                )
            )
        if _has_negative_salary_component(worker):
            errors.append(
                WpsValidationError(
                    code="wps_negative_salary_component",
                    employee_id_number=worker.employee_id_number or None,
                    message="WPS salary components must not be negative.",
                )
            )
    return errors


def _validate_approval_sequence(salary_file: WpsSalaryFile) -> list[WpsValidationError]:
    if len(salary_file.approvals) != 2:  # NON_STATUTORY_NUMBER: WPS flow has two required lifecycle actions: prepare then approve.
        return [
            WpsValidationError(
                code="wps_invalid_approval_sequence",
                message="WPS salary file must have exactly one prepare action and one approve action.",
            )
        ]

    prepare, approve = salary_file.approvals
    if prepare.action != WpsApprovalActionType.PREPARE:
        return [
            WpsValidationError(
                code="wps_invalid_approval_sequence",
                message="First WPS approval action must be prepare.",
            )
        ]
    if approve.action != WpsApprovalActionType.APPROVE:
        return [
            WpsValidationError(
                code="wps_invalid_approval_sequence",
                message="Second WPS approval action must be approve.",
            )
        ]

    wrp_prepares_and_approves = (
        prepare.role == WpsRole.WRP and approve.role == WpsRole.WRP
    )
    maker_checker_flow = (
        prepare.role == WpsRole.MAKER
        and approve.role == WpsRole.CHECKER
        and prepare.actor_user_id != approve.actor_user_id
    )
    if wrp_prepares_and_approves or maker_checker_flow:
        return []
    return [
        WpsValidationError(
            code="wps_invalid_approval_roles",
            message=(
                "WPS approval must be Maker prepare + separate Checker approve, "
                "or WRP prepare + WRP approve."
            ),
        )
    ]


def _validate_non_payment_workflow(salary_file: WpsSalaryFile) -> list[WpsValidationError]:
    justifications = {
        (item.employee_id_number, item.payroll_month): item
        for item in salary_file.non_payment_justifications
    }
    errors: list[WpsValidationError] = []
    for worker in salary_file.worker_payments:
        if worker.payment_status == WpsPaymentStatus.PAID:
            continue
        justification = justifications.get((worker.employee_id_number, salary_file.payroll_month))
        if justification is None:
            errors.append(
                WpsValidationError(
                    code="wps_missing_non_payment_justification",
                    employee_id_number=worker.employee_id_number,
                    message="Partial/non-payment requires a separate monthly WPS justification.",
                )
            )
            continue
        missing = _missing_justification_fields(justification)
        if missing:
            errors.append(
                WpsValidationError(
                    code="wps_incomplete_non_payment_justification",
                    employee_id_number=worker.employee_id_number,
                    message=f"WPS non-payment justification is missing: {', '.join(missing)}.",
                )
            )
    return errors


def _missing_required_fields(worker: WpsWorkerPayment) -> list[str]:
    required_values = {
        "employee_full_name": worker.employee_full_name,
        "employee_id_number": worker.employee_id_number,
        "wage_amount": worker.wage_amount,
        "payment_date": worker.payment_date,
        "employee_account_identifier": worker.employee_account_identifier,
        "employer_account_number": worker.employer_account_number,
        "employer_id_cr_number": worker.employer_id_cr_number,
        "fixed_salary": worker.fixed_salary,
        "social_allowance": worker.social_allowance,
        "variable_salary": worker.variable_salary,
    }
    return [
        field_name
        for field_name, value in required_values.items()
        if value is None or value == ""
    ]


def _has_negative_salary_component(worker: WpsWorkerPayment) -> bool:
    return any(
        value < Decimal("0")
        for value in (worker.fixed_salary, worker.social_allowance, worker.variable_salary)
    )


def _missing_justification_fields(justification: WpsNonPaymentJustification) -> list[str]:
    required_values = {
        "reason": justification.reason,
        "supporting_document_refs": justification.supporting_document_refs,
        "wps_commitment_level": justification.wps_commitment_level,
        "offense_code": justification.offense_code,
    }
    return [
        field_name
        for field_name, value in required_values.items()
        if value is None or value == "" or value == ()
    ]
