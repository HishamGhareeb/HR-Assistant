import type {
  AdminResyncRequest,
  AdminRevokeRequest,
  AdminRoleAssignmentRequest,
  AdminRoleAssignmentResponse,
  AdminSourceStatusResponse,
  AdminSyncRunResponse,
  DevTokenRequest,
  DevTokenResponse,
  EosbGratuityRequest,
  EosbGratuityResponse,
  EosbMonthlyContributionRequest,
  EosbMonthlyContributionResponse,
  FeedbackResponse,
  QualitySummaryResponse,
  QuestionRequest,
  QuestionResponse,
  ResolveFeedbackRequest,
  ReviewSuggestionResponse,
  ReviewDecisionRequest,
  SubmitFeedbackRequest,
  SuggestionStatus,
  SioContributionRequest,
  SioContributionResponse,
  UnansweredQuestionResponse,
  WpsSalaryFileIn,
  WpsValidationResponse,
} from "./types";

/** Thrown for any non-2xx response. Callers switch on `status` to render
 * the distinct loading/no-info/blocked/error/unauthorized states the
 * product requires -- never a single generic "something went wrong". */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`API error ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  options: { method?: string; token?: string | null; body?: unknown; searchParams?: Record<string, string | boolean | undefined> } = {},
): Promise<T> {
  const { method = "GET", token, body, searchParams } = options;

  let url = path;
  if (searchParams) {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(searchParams)) {
      if (value !== undefined) query.set(key, String(value));
    }
    const qs = query.toString();
    if (qs) url += `?${qs}`;
  }

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = typeof payload?.detail === "string" ? payload.detail : JSON.stringify(payload);
    } catch {
      // Non-JSON error body (e.g. a bare 404) -- fall back to statusText.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  // --- dev auth ---
  mintDevToken: (body: DevTokenRequest) => request<DevTokenResponse>("/v1/dev/token", { method: "POST", body }),

  // --- employee chat + feedback ---
  askQuestion: (token: string, body: QuestionRequest) =>
    request<QuestionResponse>("/v1/questions", { method: "POST", token, body }),

  submitFeedback: (token: string, requestId: string, body: SubmitFeedbackRequest) =>
    request<FeedbackResponse>(`/v1/questions/${encodeURIComponent(requestId)}/feedback`, {
      method: "POST",
      token,
      body,
    }),

  // --- HR suggestion inbox ---
  listSuggestions: (token: string, statusFilter?: SuggestionStatus) =>
    request<ReviewSuggestionResponse[]>("/v1/hr/suggestions", {
      token,
      searchParams: { status_filter: statusFilter },
    }),

  decideSuggestion: (token: string, suggestionId: string, body: ReviewDecisionRequest) =>
    request<ReviewSuggestionResponse>(`/v1/hr/suggestions/${encodeURIComponent(suggestionId)}/decision`, {
      method: "POST",
      token,
      body,
    }),

  // --- HR admin console ---
  listAdminSources: (token: string) => request<AdminSourceStatusResponse[]>("/v1/hr/admin/sources", { token }),

  listAdminSyncRuns: (token: string) => request<AdminSyncRunResponse[]>("/v1/hr/admin/sync/runs", { token }),

  resyncAdminRecords: (token: string, body: AdminResyncRequest) =>
    request<AdminSyncRunResponse>("/v1/hr/admin/sync/resync", { method: "POST", token, body }),

  revokeAdminRecord: (token: string, body: AdminRevokeRequest) =>
    request<AdminSyncRunResponse>("/v1/hr/admin/sync/revoke", { method: "POST", token, body }),

  listRoleAssignments: (token: string) =>
    request<AdminRoleAssignmentResponse[]>("/v1/hr/admin/access/roles", { token }),

  setRoleAssignment: (token: string, userId: string, body: AdminRoleAssignmentRequest) =>
    request<AdminRoleAssignmentResponse>(`/v1/hr/admin/access/roles/${encodeURIComponent(userId)}`, {
      method: "PUT",
      token,
      body,
    }),

  // --- HR feedback & quality dashboard ---
  listFeedback: (token: string, opts: { helpful?: boolean; escalatedOnly?: boolean } = {}) =>
    request<FeedbackResponse[]>("/v1/hr/feedback", {
      token,
      searchParams: { helpful: opts.helpful, escalated_only: opts.escalatedOnly },
    }),

  listUnansweredQuestions: (token: string) =>
    request<UnansweredQuestionResponse[]>("/v1/hr/feedback/unanswered", { token }),

  getQualitySummary: (token: string) => request<QualitySummaryResponse>("/v1/hr/feedback/quality-summary", { token }),

  resolveFeedback: (token: string, feedbackId: string, body: ResolveFeedbackRequest) =>
    request<FeedbackResponse>(`/v1/hr/feedback/${encodeURIComponent(feedbackId)}/resolve`, {
      method: "POST",
      token,
      body,
    }),

  // --- Bahrain payroll ---
  calculateSioContribution: (token: string, body: SioContributionRequest) =>
    request<SioContributionResponse>("/v1/hr/payroll/bahrain/sio-contributions/calculate", {
      method: "POST",
      token,
      body,
    }),

  calculateEosbMonthlyContribution: (token: string, body: EosbMonthlyContributionRequest) =>
    request<EosbMonthlyContributionResponse>("/v1/hr/payroll/bahrain/eosb/monthly-contribution", {
      method: "POST",
      token,
      body,
    }),

  calculateEosbGratuity: (token: string, body: EosbGratuityRequest) =>
    request<EosbGratuityResponse>("/v1/hr/payroll/bahrain/eosb/gratuity", {
      method: "POST",
      token,
      body,
    }),

  validateWpsSalaryFile: (token: string, body: WpsSalaryFileIn) =>
    request<WpsValidationResponse>("/v1/hr/payroll/bahrain/wps/validate", {
      method: "POST",
      token,
      body,
    }),
};
