/**
 * Mirrors glue/app.py's Pydantic request/response models exactly. Keep in
 * sync by hand -- there is no shared schema generator wired up yet (a
 * natural follow-up: emit these from FastAPI's OpenAPI schema instead).
 */

export type FeedbackReasonCode = "incorrect" | "incomplete" | "irrelevant" | "outdated" | "other";

export type SuggestionStatus = "pending" | "approved" | "rejected" | "dismissed";

export type TenantRole = "employee" | "manager" | "hr_admin" | "system_admin";

// --- /v1/dev/token -----------------------------------------------------

export interface DevTokenRequest {
  tenant_id: string;
  user_id: string;
}

export interface DevTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// --- /v1/questions -------------------------------------------------------

export interface QuestionRequest {
  question: string;
}

export interface SuggestionResponse {
  category: string;
  reasoning: string;
  record_reference: string | null;
}

export interface QuestionResponse {
  answer: string;
  suggestions: SuggestionResponse[];
  blocked: boolean;
  request_id: string;
}

// --- /v1/questions/{request_id}/feedback, /v1/hr/feedback/* -------------

export interface SubmitFeedbackRequest {
  question: string;
  answer: string;
  helpful: boolean;
  reason_code?: FeedbackReasonCode | null;
  note?: string | null;
}

export interface FeedbackResolutionResponse {
  resolved_by: string;
  resolved_at: string;
  note: string | null;
}

export interface FeedbackResponse {
  feedback_id: string;
  tenant_id: string;
  user_id: string;
  request_id: string;
  question: string;
  answer: string;
  helpful: boolean;
  reason_code: FeedbackReasonCode | null;
  note: string | null;
  escalated: boolean;
  resolved: boolean;
  resolution: FeedbackResolutionResponse | null;
  created_at: string;
}

export interface UnansweredQuestionResponse {
  record_id: string;
  tenant_id: string;
  user_id: string;
  request_id: string;
  question: string;
  model_outcome: string;
  created_at: string;
}

export interface ResolveFeedbackRequest {
  note?: string | null;
}

export interface QualitySummaryResponse {
  tenant_id: string;
  total_feedback: number;
  helpful_count: number;
  not_helpful_count: number;
  helpful_rate: number | null;
  reason_code_counts: Record<string, number>;
  unresolved_escalation_count: number;
  unanswered_count: number;
}

// --- /v1/hr/suggestions/* -------------------------------------------------

export interface ReviewDecisionRequest {
  action: SuggestionStatus;
  note?: string | null;
}

export interface ReviewDecisionResponse {
  decision_id: string;
  action: SuggestionStatus;
  decided_by: string;
  decided_at: string;
  note: string | null;
}

export interface ReviewSuggestionResponse {
  suggestion_id: string;
  tenant_id: string;
  category: string;
  reasoning: string;
  record_reference: string | null;
  status: SuggestionStatus;
  created_at: string;
  decided_at: string | null;
  decided_by: string | null;
  decision_history: ReviewDecisionResponse[];
}

// --- /v1/hr/admin/* --------------------------------------------------------

export interface AdminRecordFailureResponse {
  doctype: string;
  name: string;
  reason: string;
}

export interface AdminSyncRunResponse {
  run_id: string;
  tenant_id: string;
  source_id: string;
  action: string;
  status: string;
  created: number;
  updated: number;
  deleted: number;
  unchanged: number;
  failed: AdminRecordFailureResponse[];
  started_at: string;
  finished_at: string | null;
}

export interface AdminSourceStatusResponse {
  tenant_id: string;
  source_id: string;
  last_action: string;
  last_status: string;
  last_run_id: string;
  updated_at: string;
}

export interface AdminHrSourceRecordRequest {
  doctype: string;
  name: string;
  fields: Record<string, unknown>;
  deleted: boolean;
}

export interface AdminResyncRequest {
  source_id: string;
  records: AdminHrSourceRecordRequest[];
}

export interface AdminRevokeRequest {
  source_id: string;
  doctype: string;
  name: string;
}

export interface AdminRoleAssignmentRequest {
  roles: TenantRole[];
}

export interface AdminRoleAssignmentResponse {
  tenant_id: string;
  user_id: string;
  roles: TenantRole[];
  updated_by: string;
  updated_at: string;
}

// --- /v1/hr/payroll/bahrain/* ----------------------------------------------

export interface CitationOut {
  section: string;
  instrument: string;
  retrieved: string;
  source_doc: string;
  quote: string | null;
}

export interface StatutoryFigureOut {
  name: string;
  value: string;
  unit: string | null;
  citation: CitationOut;
  note: string | null;
}

export interface UnsupportedReasonOut {
  code: string;
  message: string;
  requires_hr_review: boolean;
}

export type BahrainWorkerCategory =
  | "bahraini_private_sector"
  | "non_bahraini_private_sector"
  | "gcc_national"
  | "domestic_worker"
  | "public_sector"
  | "self_employed"
  | "flexi_or_successor";

export type BahrainContributionBranch =
  | "pension"
  | "employment_injury"
  | "unemployment"
  | "end_of_service_benefit";

export type BahrainContributionPayer = "employee" | "employer" | "labour_fund" | "government";

export interface SioContributionRequest {
  worker_category: BahrainWorkerCategory;
  branch: BahrainContributionBranch;
  payer: BahrainContributionPayer;
  monthly_wage: string;
  as_of: string;
}

export interface SioContributionResultOut {
  worker_category: BahrainWorkerCategory;
  branch: BahrainContributionBranch;
  payer: BahrainContributionPayer;
  rate_percent: string;
  monthly_wage: string;
  amount: string;
  rate_code: string;
  figure: StatutoryFigureOut;
  note: string | null;
}

export interface SioContributionResponse {
  supported: boolean;
  result: SioContributionResultOut | null;
  unsupported: UnsupportedReasonOut | null;
}

export interface EosbMonthlyContributionRequest {
  hire_date: string;
  monthly_wage: string;
  as_of: string;
}

export interface EosbMonthlyContributionResult {
  as_of: string;
  pre_march_2024_completed_service_years: string;
  total_completed_service_years: string;
  contribution_rate_percent: string;
  employer_monthly_contribution_amount: string;
  figures: StatutoryFigureOut[];
}

export interface EosbMonthlyContributionResponse {
  supported: boolean;
  result: EosbMonthlyContributionResult | null;
  unsupported: UnsupportedReasonOut | null;
}

export interface EosbGratuityRequest {
  monthly_basic_salary: string;
  monthly_social_allowance: string;
  hire_date: string;
  termination_date: string;
}

export interface EosbGratuityResponse {
  pre_march_2024_service_years: string;
  post_march_2024_service_years: string;
  pre_march_2024_employer_direct_liability: string;
  post_march_2024_sio_funded_amount: string;
  total_amount: string;
  figures: StatutoryFigureOut[];
}

export type WpsRole = "maker" | "checker" | "wrp";
export type WpsApprovalActionType = "submitted" | "approved" | "rejected";
export type WpsPaymentStatus = "paid" | "unpaid";

export interface WpsWorkerPaymentIn {
  employee_full_name: string;
  employee_id_number: string;
  wage_amount: string;
  payment_date: string;
  employee_account_identifier: string;
  employer_account_number: string;
  employer_id_cr_number: string;
  fixed_salary: string;
  social_allowance: string;
  variable_salary: string;
  payment_status: WpsPaymentStatus;
}

export interface WpsApprovalActionIn {
  actor_user_id: string;
  role: WpsRole;
  action: WpsApprovalActionType;
  acted_at: string;
}

export interface WpsSalaryFileIn {
  payroll_month: string;
  scheduled_transfer_date: string;
  actual_transfer_date: string;
  worker_payments: WpsWorkerPaymentIn[];
  approvals: WpsApprovalActionIn[];
  non_payment_justifications: unknown[];
}

export interface WpsValidationErrorOut {
  code: string;
  message: string;
  employee_id_number: string | null;
}

export interface WpsValidationResponse {
  is_valid: boolean;
  errors: WpsValidationErrorOut[];
  citations: CitationOut[];
}
