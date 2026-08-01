from datetime import date
from decimal import Decimal

from glue.bahrain_payroll.rules.wps import (
    WpsApprovalAction,
    WpsApprovalActionType,
    WpsNonPaymentJustification,
    WpsPaymentStatus,
    WpsRole,
    WpsSalaryFile,
    WpsWorkerPayment,
    validate_wps_salary_file,
)
from glue.bahrain_payroll.statutory_values import (
    WPS_ADVANCE_SCHEDULING_WINDOW_DAYS,
    WPS_DISCLOSURE_FIELDS_CITATION,
    WPS_MAX_WORKER_RECORDS_PER_FILE,
)


def test_wps_statutory_values_cite_official_source_inventory() -> None:
    assert WPS_MAX_WORKER_RECORDS_PER_FILE.citation.section == "§2a-ter"
    assert WPS_MAX_WORKER_RECORDS_PER_FILE.citation.instrument == "WPS User Manual"
    assert WPS_ADVANCE_SCHEDULING_WINDOW_DAYS.citation.section == "§2a-ter"
    assert WPS_DISCLOSURE_FIELDS_CITATION.section == "§2c"
    assert WPS_DISCLOSURE_FIELDS_CITATION.instrument == "Resolution No. 68 of 2019"


def test_valid_wps_salary_file_passes_with_maker_checker_flow() -> None:
    result = validate_wps_salary_file(_salary_file())

    assert result.is_valid
    assert result.errors == ()


def test_rejects_file_exceeding_1000_worker_record_cap() -> None:
    workers = tuple(_worker(employee_id_number=f"EMP-{index}") for index in range(1001))
    result = validate_wps_salary_file(_salary_file(worker_payments=workers))

    assert not result.is_valid
    assert _error_codes(result) == {"wps_file_record_cap_exceeded"}


def test_rejects_transfer_date_outside_14_day_window() -> None:
    result = validate_wps_salary_file(
        _salary_file(
            scheduled_transfer_date=date(2026, 1, 1),
            actual_transfer_date=date(2026, 1, 16),
        )
    )

    assert not result.is_valid
    assert _error_codes(result) == {"wps_transfer_date_too_early"}


def test_rejects_transfer_date_after_actual_transfer_date() -> None:
    result = validate_wps_salary_file(
        _salary_file(
            scheduled_transfer_date=date(2026, 1, 20),
            actual_transfer_date=date(2026, 1, 19),
        )
    )

    assert not result.is_valid
    assert _error_codes(result) == {"wps_transfer_date_after_actual_date"}


def test_rejects_missing_required_disclosure_fields() -> None:
    result = validate_wps_salary_file(
        _salary_file(
            worker_payments=(
                _worker(employee_full_name="", employer_id_cr_number=""),
            )
        )
    )

    assert not result.is_valid
    assert _error_codes(result) == {"wps_missing_required_disclosure_fields"}
    assert "employee_full_name" in result.errors[0].message
    assert "employer_id_cr_number" in result.errors[0].message


def test_rejects_malformed_maker_checker_approval_sequence() -> None:
    result = validate_wps_salary_file(
        _salary_file(
            approvals=(
                _approval("user-1", WpsRole.MAKER, WpsApprovalActionType.PREPARE),
                _approval("user-1", WpsRole.CHECKER, WpsApprovalActionType.APPROVE),
            )
        )
    )

    assert not result.is_valid
    assert _error_codes(result) == {"wps_invalid_approval_roles"}


def test_allows_wrp_to_prepare_and_approve() -> None:
    result = validate_wps_salary_file(
        _salary_file(
            approvals=(
                _approval("wrp-1", WpsRole.WRP, WpsApprovalActionType.PREPARE),
                _approval("wrp-1", WpsRole.WRP, WpsApprovalActionType.APPROVE),
            )
        )
    )

    assert result.is_valid


def test_requires_separate_non_payment_justification_workflow() -> None:
    result = validate_wps_salary_file(
        _salary_file(
            worker_payments=(
                _worker(payment_status=WpsPaymentStatus.PARTIAL),
            )
        )
    )

    assert not result.is_valid
    assert _error_codes(result) == {"wps_missing_non_payment_justification"}


def test_accepts_partial_payment_when_distinct_justification_is_complete() -> None:
    result = validate_wps_salary_file(
        _salary_file(
            worker_payments=(
                _worker(payment_status=WpsPaymentStatus.PARTIAL),
            ),
            non_payment_justifications=(
                WpsNonPaymentJustification(
                    employee_id_number="EMP-1",
                    payroll_month="2026-01",
                    reason="Approved unpaid leave",
                    supporting_document_refs=("leave-approval.pdf",),
                    wps_commitment_level="justified",
                    offense_code="none",
                ),
            ),
        )
    )

    assert result.is_valid


def _salary_file(
    *,
    payroll_month: str = "2026-01",
    scheduled_transfer_date: date = date(2026, 1, 10),
    actual_transfer_date: date = date(2026, 1, 20),
    worker_payments: tuple[WpsWorkerPayment, ...] | None = None,
    approvals: tuple[WpsApprovalAction, ...] | None = None,
    non_payment_justifications: tuple[WpsNonPaymentJustification, ...] = (),
) -> WpsSalaryFile:
    return WpsSalaryFile(
        payroll_month=payroll_month,
        scheduled_transfer_date=scheduled_transfer_date,
        actual_transfer_date=actual_transfer_date,
        worker_payments=worker_payments or (_worker(),),
        approvals=approvals
        or (
            _approval("maker-1", WpsRole.MAKER, WpsApprovalActionType.PREPARE),
            _approval("checker-1", WpsRole.CHECKER, WpsApprovalActionType.APPROVE),
        ),
        non_payment_justifications=non_payment_justifications,
    )


def _worker(
    *,
    employee_full_name: str = "Fatima Ali",
    employee_id_number: str = "EMP-1",
    wage_amount: Decimal = Decimal("750.000"),
    payment_date: date = date(2026, 1, 20),
    employee_account_identifier: str = "BH00TESTACCOUNT",
    employer_account_number: str = "BH00EMPLOYERACCOUNT",
    employer_id_cr_number: str = "196651-1",
    fixed_salary: Decimal = Decimal("500.000"),
    social_allowance: Decimal = Decimal("100.000"),
    variable_salary: Decimal = Decimal("150.000"),
    payment_status: WpsPaymentStatus = WpsPaymentStatus.PAID,
) -> WpsWorkerPayment:
    return WpsWorkerPayment(
        employee_full_name=employee_full_name,
        employee_id_number=employee_id_number,
        wage_amount=wage_amount,
        payment_date=payment_date,
        employee_account_identifier=employee_account_identifier,
        employer_account_number=employer_account_number,
        employer_id_cr_number=employer_id_cr_number,
        fixed_salary=fixed_salary,
        social_allowance=social_allowance,
        variable_salary=variable_salary,
        payment_status=payment_status,
    )


def _approval(
    actor_user_id: str,
    role: WpsRole,
    action: WpsApprovalActionType,
) -> WpsApprovalAction:
    return WpsApprovalAction(
        actor_user_id=actor_user_id,
        role=role,
        action=action,
        acted_at=date(2026, 1, 15),
    )


def _error_codes(result) -> set[str]:
    return {error.code for error in result.errors}

