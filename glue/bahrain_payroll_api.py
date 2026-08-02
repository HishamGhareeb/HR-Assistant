"""HTTP request/response shapes and service functions for the Bahrain
payroll rule pack (HIS-59).

This module wires already-merged, source-cited rule-pack logic --
``glue.bahrain_payroll.rules.wps``, ``.sio_wage_update``, ``.eosb``,
``.eosb_transition``, and ``.sio_contributions`` -- into request/response
Pydantic models the API can serve. It introduces no new statutory numbers:
every figure returned here already exists in
``glue.bahrain_payroll.statutory_values`` with its own citation.

Two safety rules carried over from the rule pack itself:

- Every response that reports a statutory figure includes that figure's
  ``StatutoryCitation`` (or the full ``StatutoryValue``, when the number
  itself is worth surfacing), per HIS-59's acceptance criteria -- this is a
  product requirement, not just internal traceability.
- Endpoints backed by ``BAHRAIN_PAYROLL_RATE_REGISTRY`` (EOSB monthly
  contribution, SIO contributions) never propagate
  ``BahrainPayrollRateNotFoundError`` as a bare 5xx/4xx failure. They catch
  it and return a structured ``supported: false`` result explaining that no
  source-backed rate exists yet and the case needs HR review -- per the
  standing instruction that these APIs must never return a guessed
  calculation for an unsupported category.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel, Field

from glue.bahrain_payroll.citation_guard import StatutoryCitation, StatutoryValue
from glue.bahrain_payroll.rate_registry import (
    BAHRAIN_PAYROLL_RATE_REGISTRY,
    BahrainContributionBranch,
    BahrainContributionPayer,
    BahrainPayrollRateLookup,
    BahrainPayrollRateNotFoundError,
    BahrainWorkerCategory,
)
from glue.bahrain_payroll.rules.eosb import (
    BahrainEmploymentSector,
    BahrainWorkerNationalityCategory,
    EosbEligibilityInput,
    employer_non_payment_penalty_range,
    evaluate_eosb_eligibility,
)
from glue.bahrain_payroll.rules.eosb_transition import (
    EosbSplitGratuityInput,
    calculate_eosb_gratuity_with_pre_post_split,
    eosb_monthly_contribution_rate_percent_with_article_13_transition,
    eosb_monthly_employer_contribution_with_article_13_transition,
    split_eosb_service_years,
)
from glue.bahrain_payroll.rules.sio_wage_update import (
    SioWageComponents,
    SioWageUpdateSubmission,
    SioWageUpdateType,
    contribution_scope_components,
    validate_sio_wage_update,
)
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
    EOSB_ARTICLE_13_PRE_TRANSITION_SERVICE_YEARS_THRESHOLD,
    EOSB_EFFECTIVE_DATE,
    EOSB_EFFECTIVE_DATE_CITATION,
    EOSB_EMPLOYER_PENALTY_MAX_MULTIPLIER,
    EOSB_EMPLOYER_PENALTY_MIN_MULTIPLIER,
    EOSB_FIRST_THREE_YEARS_CONTRIBUTION_RATE_PERCENT,
    EOSB_FIRST_TIER_YEARS,
    EOSB_HALF_MONTH_DIVISOR,
    EOSB_SCOPE_CITATION,
    EOSB_SUBSEQUENT_TIER_MONTHS_PER_YEAR,
    EOSB_SUBSEQUENT_YEARS_CONTRIBUTION_RATE_PERCENT,
    LEGACY_GRATUITY_FIRST_TIER_YEARS,
    LEGACY_GRATUITY_HALF_MONTH_DIVISOR,
    LEGACY_GRATUITY_SUBSEQUENT_TIER_MONTHS_PER_YEAR,
    SIO_CONTRIBUTION_SCOPE_CITATION,
    SIO_IMMUTABLE_FIELDS_CITATION,
    SIO_NO_SALARY_DECREASE_CITATION,
    SIO_SALARY_INCREASE_CAP_PERCENT,
    SIO_TOTAL_ALLOWANCES_CITATION,
    WPS_ADVANCE_SCHEDULING_WINDOW_DAYS,
    WPS_DISCLOSURE_FIELDS_CITATION,
    WPS_MAX_WORKER_RECORDS_PER_FILE,
)


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


# --- Shared citation/explanation metadata -----------------------------------


class CitationOut(BaseModel):
    section: str
    instrument: str
    retrieved: str
    source_doc: str
    quote: str | None = None

    @classmethod
    def from_domain(cls, citation: StatutoryCitation) -> "CitationOut":
        return cls(
            section=citation.section,
            instrument=citation.instrument,
            retrieved=citation.retrieved,
            source_doc=citation.source_doc,
            quote=citation.quote,
        )


class StatutoryFigureOut(BaseModel):
    name: str
    value: str
    unit: str | None
    citation: CitationOut
    note: str | None

    @classmethod
    def from_domain(cls, value_obj: StatutoryValue) -> "StatutoryFigureOut":
        return cls(
            name=value_obj.name,
            value=str(value_obj.value),
            unit=value_obj.unit,
            citation=CitationOut.from_domain(value_obj.citation),
            note=value_obj.note,
        )


class UnsupportedReasonOut(BaseModel):
    code: str = "no_source_backed_rate"
    message: str
    requires_hr_review: bool = True


# --- WPS compliance validation ----------------------------------------------


class WpsWorkerPaymentIn(BaseModel):
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

    def to_domain(self) -> WpsWorkerPayment:
        return WpsWorkerPayment(**self.model_dump())


class WpsApprovalActionIn(BaseModel):
    actor_user_id: str
    role: WpsRole
    action: WpsApprovalActionType
    acted_at: date

    def to_domain(self) -> WpsApprovalAction:
        return WpsApprovalAction(**self.model_dump())


class WpsNonPaymentJustificationIn(BaseModel):
    employee_id_number: str
    payroll_month: str
    reason: str
    supporting_document_refs: tuple[str, ...] = ()
    wps_commitment_level: str
    offense_code: str

    def to_domain(self) -> WpsNonPaymentJustification:
        return WpsNonPaymentJustification(**self.model_dump())


class WpsSalaryFileIn(BaseModel):
    payroll_month: str
    scheduled_transfer_date: date
    actual_transfer_date: date
    worker_payments: list[WpsWorkerPaymentIn] = Field(min_length=1)
    approvals: list[WpsApprovalActionIn]
    non_payment_justifications: list[WpsNonPaymentJustificationIn] = []

    def to_domain(self) -> WpsSalaryFile:
        return WpsSalaryFile(
            payroll_month=self.payroll_month,
            scheduled_transfer_date=self.scheduled_transfer_date,
            actual_transfer_date=self.actual_transfer_date,
            worker_payments=tuple(w.to_domain() for w in self.worker_payments),
            approvals=tuple(a.to_domain() for a in self.approvals),
            non_payment_justifications=tuple(
                j.to_domain() for j in self.non_payment_justifications
            ),
        )


class WpsValidationErrorOut(BaseModel):
    code: str
    message: str
    employee_id_number: str | None


class WpsValidationResponse(BaseModel):
    is_valid: bool
    errors: list[WpsValidationErrorOut]
    citations: list[CitationOut]


def validate_wps_salary_file_request(payload: WpsSalaryFileIn) -> WpsValidationResponse:
    result = validate_wps_salary_file(payload.to_domain())
    return WpsValidationResponse(
        is_valid=result.is_valid,
        errors=[
            WpsValidationErrorOut(
                code=error.code,
                message=error.message,
                employee_id_number=error.employee_id_number,
            )
            for error in result.errors
        ],
        citations=[
            CitationOut.from_domain(WPS_MAX_WORKER_RECORDS_PER_FILE.citation),
            CitationOut.from_domain(WPS_ADVANCE_SCHEDULING_WINDOW_DAYS.citation),
            CitationOut.from_domain(WPS_DISCLOSURE_FIELDS_CITATION),
        ],
    )


# --- SIO wage-update validation ---------------------------------------------


class SioWageComponentsIn(BaseModel):
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

    def to_domain(self) -> SioWageComponents:
        return SioWageComponents(**self.model_dump())


class SioWageUpdateSubmissionIn(BaseModel):
    update_type: SioWageUpdateType
    previous_cpr_number: str
    submitted_cpr_number: str
    previous_employee_name: str
    submitted_employee_name: str
    previous_total_earnings: Decimal
    submitted_total_previous_earnings: Decimal
    previous_components: SioWageComponentsIn
    new_components: SioWageComponentsIn

    def to_domain(self) -> SioWageUpdateSubmission:
        return SioWageUpdateSubmission(
            update_type=self.update_type,
            previous_cpr_number=self.previous_cpr_number,
            submitted_cpr_number=self.submitted_cpr_number,
            previous_employee_name=self.previous_employee_name,
            submitted_employee_name=self.submitted_employee_name,
            previous_total_earnings=self.previous_total_earnings,
            submitted_total_previous_earnings=self.submitted_total_previous_earnings,
            previous_components=self.previous_components.to_domain(),
            new_components=self.new_components.to_domain(),
        )


class SioWageUpdateValidationErrorOut(BaseModel):
    code: str
    message: str


class SioWageUpdateValidationResponse(BaseModel):
    is_valid: bool
    errors: list[SioWageUpdateValidationErrorOut]
    contribution_scope_components: dict[str, Decimal]
    citations: list[CitationOut]


def validate_sio_wage_update_request(
    payload: SioWageUpdateSubmissionIn,
) -> SioWageUpdateValidationResponse:
    submission = payload.to_domain()
    result = validate_sio_wage_update(submission)
    scope = contribution_scope_components(submission.update_type, submission.new_components)
    return SioWageUpdateValidationResponse(
        is_valid=result.is_valid,
        errors=[
            SioWageUpdateValidationErrorOut(code=error.code, message=error.message)
            for error in result.errors
        ],
        contribution_scope_components=scope,
        citations=[
            CitationOut.from_domain(SIO_SALARY_INCREASE_CAP_PERCENT.citation),
            CitationOut.from_domain(SIO_NO_SALARY_DECREASE_CITATION),
            CitationOut.from_domain(SIO_TOTAL_ALLOWANCES_CITATION),
            CitationOut.from_domain(SIO_IMMUTABLE_FIELDS_CITATION),
            CitationOut.from_domain(SIO_CONTRIBUTION_SCOPE_CITATION),
        ],
    )


# --- EOSB eligibility --------------------------------------------------------


class EosbEligibilityRequest(BaseModel):
    sector: BahrainEmploymentSector
    nationality_category: BahrainWorkerNationalityCategory
    employment_injuries_branch_covered: bool
    social_insurance_law_article_3_excluded: bool = False


class EosbEligibilityResponse(BaseModel):
    eligible: bool
    reasons: list[str]
    citations: list[CitationOut]


def evaluate_eosb_eligibility_request(
    payload: EosbEligibilityRequest,
) -> EosbEligibilityResponse:
    result = evaluate_eosb_eligibility(
        EosbEligibilityInput(
            sector=payload.sector,
            nationality_category=payload.nationality_category,
            employment_injuries_branch_covered=payload.employment_injuries_branch_covered,
            social_insurance_law_article_3_excluded=payload.social_insurance_law_article_3_excluded,
        )
    )
    return EosbEligibilityResponse(
        eligible=result.eligible,
        reasons=list(result.reasons),
        citations=[
            CitationOut.from_domain(EOSB_SCOPE_CITATION),
            CitationOut.from_domain(EOSB_EFFECTIVE_DATE_CITATION),
        ],
    )


# --- EOSB gratuity, pre/post-1-March-2024 split ------------------------------


class EosbGratuityRequest(BaseModel):
    monthly_basic_salary: Decimal
    monthly_social_allowance: Decimal
    hire_date: date
    termination_date: date


class EosbGratuityResponse(BaseModel):
    pre_march_2024_service_years: Decimal
    post_march_2024_service_years: Decimal
    pre_march_2024_employer_direct_liability: Decimal
    post_march_2024_sio_funded_amount: Decimal
    total_amount: Decimal
    figures: list[StatutoryFigureOut]


def calculate_eosb_gratuity_request(payload: EosbGratuityRequest) -> EosbGratuityResponse:
    result = calculate_eosb_gratuity_with_pre_post_split(
        EosbSplitGratuityInput(
            monthly_basic_salary=payload.monthly_basic_salary,
            monthly_social_allowance=payload.monthly_social_allowance,
            hire_date=payload.hire_date,
            termination_date=payload.termination_date,
        )
    )
    return EosbGratuityResponse(
        pre_march_2024_service_years=result.service_split.pre_march_2024_years,
        post_march_2024_service_years=result.service_split.post_march_2024_years,
        pre_march_2024_employer_direct_liability=result.pre_march_2024_employer_direct_liability,
        post_march_2024_sio_funded_amount=result.post_march_2024_sio_funded_amount,
        total_amount=result.total_amount,
        figures=[
            StatutoryFigureOut.from_domain(LEGACY_GRATUITY_FIRST_TIER_YEARS),
            StatutoryFigureOut.from_domain(LEGACY_GRATUITY_HALF_MONTH_DIVISOR),
            StatutoryFigureOut.from_domain(LEGACY_GRATUITY_SUBSEQUENT_TIER_MONTHS_PER_YEAR),
            StatutoryFigureOut.from_domain(EOSB_FIRST_TIER_YEARS),
            StatutoryFigureOut.from_domain(EOSB_HALF_MONTH_DIVISOR),
            StatutoryFigureOut.from_domain(EOSB_SUBSEQUENT_TIER_MONTHS_PER_YEAR),
            StatutoryFigureOut.from_domain(EOSB_EFFECTIVE_DATE),
        ],
    )


# --- EOSB monthly contribution, Article 13 transition-aware -----------------


class EosbMonthlyContributionRequest(BaseModel):
    hire_date: date
    monthly_wage: Decimal
    as_of: date


class EosbMonthlyContributionResult(BaseModel):
    as_of: date
    pre_march_2024_completed_service_years: Decimal
    total_completed_service_years: Decimal
    contribution_rate_percent: Decimal
    employer_monthly_contribution_amount: Decimal
    figures: list[StatutoryFigureOut]


class EosbMonthlyContributionResponse(BaseModel):
    supported: bool
    result: EosbMonthlyContributionResult | None = None
    unsupported: UnsupportedReasonOut | None = None


def calculate_eosb_monthly_contribution_request(
    payload: EosbMonthlyContributionRequest,
) -> EosbMonthlyContributionResponse:
    split = split_eosb_service_years(payload.hire_date, payload.as_of)
    total_years = split.pre_march_2024_years + split.post_march_2024_years
    try:
        rate = eosb_monthly_contribution_rate_percent_with_article_13_transition(
            total_completed_service_years=total_years,
            pre_march_2024_completed_service_years=split.pre_march_2024_years,
            as_of=payload.as_of,
        )
        amount = eosb_monthly_employer_contribution_with_article_13_transition(
            monthly_wage=payload.monthly_wage,
            total_completed_service_years=total_years,
            pre_march_2024_completed_service_years=split.pre_march_2024_years,
            as_of=payload.as_of,
        )
    except BahrainPayrollRateNotFoundError as exc:
        return EosbMonthlyContributionResponse(
            supported=False,
            unsupported=UnsupportedReasonOut(message=str(exc)),
        )
    return EosbMonthlyContributionResponse(
        supported=True,
        result=EosbMonthlyContributionResult(
            as_of=payload.as_of,
            pre_march_2024_completed_service_years=split.pre_march_2024_years,
            total_completed_service_years=total_years,
            contribution_rate_percent=rate,
            employer_monthly_contribution_amount=amount,
            figures=[
                StatutoryFigureOut.from_domain(EOSB_FIRST_THREE_YEARS_CONTRIBUTION_RATE_PERCENT),
                StatutoryFigureOut.from_domain(EOSB_SUBSEQUENT_YEARS_CONTRIBUTION_RATE_PERCENT),
                StatutoryFigureOut.from_domain(
                    EOSB_ARTICLE_13_PRE_TRANSITION_SERVICE_YEARS_THRESHOLD
                ),
                StatutoryFigureOut.from_domain(EOSB_EFFECTIVE_DATE),
            ],
        ),
    )


# --- EOSB employer non-payment penalty --------------------------------------


class EosbEmployerPenaltyRequest(BaseModel):
    unpaid_contribution_amount: Decimal


class EosbEmployerPenaltyResponse(BaseModel):
    minimum: Decimal
    maximum: Decimal
    figures: list[StatutoryFigureOut]


def calculate_eosb_employer_penalty_request(
    payload: EosbEmployerPenaltyRequest,
) -> EosbEmployerPenaltyResponse:
    result = employer_non_payment_penalty_range(payload.unpaid_contribution_amount)
    return EosbEmployerPenaltyResponse(
        minimum=result.minimum,
        maximum=result.maximum,
        figures=[
            StatutoryFigureOut.from_domain(EOSB_EMPLOYER_PENALTY_MIN_MULTIPLIER),
            StatutoryFigureOut.from_domain(EOSB_EMPLOYER_PENALTY_MAX_MULTIPLIER),
        ],
    )


# --- SIO contributions (Bahraini pension, employment injury, unemployment) --
#
# Dispatches directly through BAHRAIN_PAYROLL_RATE_REGISTRY rather than one
# function per branch: the registry is already the single source of truth
# for which (worker_category, branch, payer, date) combinations are
# source-backed, and an unregistered combination -- the Bahraini pension
# employer share, employment injury, GCC/domestic/public/self-employed/Flexi
# categories, EMPLOYER payer for unemployment -- fails closed automatically
# via BahrainPayrollRateNotFoundError. No per-branch special-casing needed
# here, matching glue/bahrain_payroll/rules/sio_contributions.py's own
# design.


class SioContributionRequest(BaseModel):
    worker_category: BahrainWorkerCategory
    branch: BahrainContributionBranch
    payer: BahrainContributionPayer
    monthly_wage: Decimal
    as_of: date


class SioContributionResultOut(BaseModel):
    worker_category: BahrainWorkerCategory
    branch: BahrainContributionBranch
    payer: BahrainContributionPayer
    rate_percent: Decimal
    monthly_wage: Decimal
    amount: Decimal
    rate_code: str
    figure: StatutoryFigureOut
    note: str | None


class SioContributionResponse(BaseModel):
    supported: bool
    result: SioContributionResultOut | None = None
    unsupported: UnsupportedReasonOut | None = None


def calculate_sio_contribution_request(
    payload: SioContributionRequest,
) -> SioContributionResponse:
    if payload.monthly_wage < Decimal("0"):
        raise ValueError("monthly_wage cannot be negative")

    try:
        rate = BAHRAIN_PAYROLL_RATE_REGISTRY.lookup(
            BahrainPayrollRateLookup(
                worker_category=payload.worker_category,
                branch=payload.branch,
                payer=payload.payer,
                as_of=payload.as_of,
            )
        )
    except BahrainPayrollRateNotFoundError as exc:
        return SioContributionResponse(
            supported=False,
            unsupported=UnsupportedReasonOut(message=str(exc)),
        )

    rate_percent = Decimal(str(rate.percent.value))
    amount = _quantize_money(payload.monthly_wage * rate_percent / Decimal("100"))
    return SioContributionResponse(
        supported=True,
        result=SioContributionResultOut(
            worker_category=payload.worker_category,
            branch=payload.branch,
            payer=payload.payer,
            rate_percent=rate_percent,
            monthly_wage=payload.monthly_wage,
            amount=amount,
            rate_code=rate.code,
            figure=StatutoryFigureOut.from_domain(rate.percent),
            note=rate.note,
        ),
    )
