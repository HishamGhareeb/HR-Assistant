import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api, ApiError } from "../api/client";
import type { FeedbackResponse, QualitySummaryResponse, UnansweredQuestionResponse } from "../api/types";
import { StateView, stateFromApiError } from "../components/StateView";
import { StatusChip } from "../components/StatusChip";

type EscalatedFilter = "all" | "escalated";

export function FeedbackPage() {
  const { session } = useAuth();
  const [summary, setSummary] = useState<QualitySummaryResponse | null>(null);
  const [feedback, setFeedback] = useState<FeedbackResponse[] | null>(null);
  const [unanswered, setUnanswered] = useState<UnansweredQuestionResponse[] | null>(null);
  const [filter, setFilter] = useState<EscalatedFilter>("escalated");
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    if (!session) return;
    setLoading(true);
    setErrorMessage(null);
    setErrorStatus(null);
    try {
      const [summaryResult, feedbackResult, unansweredResult] = await Promise.all([
        api.getQualitySummary(session.token),
        api.listFeedback(session.token, { escalatedOnly: filter === "escalated" }),
        api.listUnansweredQuestions(session.token),
      ]);
      setSummary(summaryResult);
      setFeedback(feedbackResult);
      setUnanswered(unansweredResult);
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.detail : "Could not reach the API.");
      setErrorStatus(err instanceof ApiError ? err.status : null);
    } finally {
      setLoading(false);
    }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    load();
  }, [filter, session?.token]);

  async function resolve(feedbackId: string, note: string) {
    if (!session) return;
    try {
      const updated = await api.resolveFeedback(session.token, feedbackId, { note: note || undefined });
      setFeedback((prev) => (prev ? prev.map((f) => (f.feedback_id === feedbackId ? updated : f)) : prev));
      setSummary((prev) => (prev ? { ...prev, unresolved_escalation_count: Math.max(0, prev.unresolved_escalation_count - 1) } : prev));
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.detail : "Could not resolve this escalation.");
    }
  }

  if (loading) {
    return (
      <>
        <div className="page-header">
          <h1>Feedback &amp; Quality</h1>
        </div>
        <StateView kind="loading">Loading quality dashboard…</StateView>
      </>
    );
  }

  if (errorMessage) {
    return (
      <>
        <div className="page-header">
          <h1>Feedback &amp; Quality</h1>
        </div>
        <StateView kind={errorStatus ? stateFromApiError(errorStatus) : "error"}>
          {errorStatus === 403 ? "You're not authorized to view answer feedback for this tenant." : errorMessage}
        </StateView>
      </>
    );
  }

  return (
    <>
      <div className="page-header">
        <h1>Feedback &amp; Quality</h1>
        <p>Aggregate counts only below — no question or answer text is ever included in the summary.</p>
      </div>

      {summary && (
        <div className="tile-grid">
          <Tile label="Total feedback" value={summary.total_feedback} />
          <Tile label="Helpful rate" value={summary.helpful_rate === null ? "—" : `${Math.round(summary.helpful_rate * 100)}%`} />
          <Tile label="Not helpful" value={summary.not_helpful_count} />
          <Tile label="Unresolved escalations" value={summary.unresolved_escalation_count} tone="warning" />
          <Tile label="Unanswered questions" value={summary.unanswered_count} tone="warning" />
        </div>
      )}

      {summary && Object.keys(summary.reason_code_counts).length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Not-helpful reasons</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {Object.entries(summary.reason_code_counts).map(([code, count]) => (
              <StatusChip key={code} tone="neutral">
                {code}: {count}
              </StatusChip>
            ))}
          </div>
        </div>
      )}

      <div className="section-title">Feedback</div>
      <div className="toolbar">
        <button className={`btn btn-sm ${filter === "escalated" ? "btn-primary" : "btn-ghost"}`} onClick={() => setFilter("escalated")}>
          Escalated only
        </button>
        <button className={`btn btn-sm ${filter === "all" ? "btn-primary" : "btn-ghost"}`} onClick={() => setFilter("all")}>
          All feedback
        </button>
      </div>

      {feedback && feedback.length === 0 && <StateView kind="empty">No feedback matches this filter.</StateView>}
      {feedback && feedback.length > 0 && (
        <div className="stack">
          {feedback.map((f) => (
            <FeedbackCard key={f.feedback_id} feedback={f} onResolve={resolve} />
          ))}
        </div>
      )}

      <div className="section-title">Unanswered questions</div>
      <p className="muted" style={{ marginTop: -6, marginBottom: 12 }}>
        Recorded automatically whenever a question doesn&apos;t get an answer — no feedback required.
      </p>
      {unanswered && unanswered.length === 0 && <StateView kind="empty">No unanswered questions recorded.</StateView>}
      {unanswered && unanswered.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Outcome</th>
                <th>User</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {unanswered.map((u) => (
                <tr key={u.record_id}>
                  <td>{u.question}</td>
                  <td>
                    <StatusChip tone="neutral">{u.model_outcome}</StatusChip>
                  </td>
                  <td>{u.user_id}</td>
                  <td className="timestamp">{new Date(u.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function Tile({ label, value, tone }: { label: string; value: string | number; tone?: "warning" }) {
  return (
    <div className="tile">
      <div className="tile__value" style={tone === "warning" && Number(value) > 0 ? { color: "var(--color-warning)" } : undefined}>
        {value}
      </div>
      <div className="tile__label">{label}</div>
    </div>
  );
}

function FeedbackCard({ feedback, onResolve }: { feedback: FeedbackResponse; onResolve: (id: string, note: string) => void }) {
  const [note, setNote] = useState("");

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontWeight: 600 }}>{feedback.question}</div>
          <p className="muted" style={{ margin: "6px 0" }}>
            {feedback.answer}
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
          <StatusChip tone={feedback.helpful ? "success" : "escalated"}>{feedback.helpful ? "helpful" : "not helpful"}</StatusChip>
          {feedback.reason_code && <StatusChip tone="neutral">{feedback.reason_code}</StatusChip>}
        </div>
      </div>
      {feedback.note && <p className="muted" style={{ fontStyle: "italic" }}>&ldquo;{feedback.note}&rdquo;</p>}
      <div className="chat-meta">
        {feedback.user_id} — <span className="timestamp">{new Date(feedback.created_at).toLocaleString()}</span>
      </div>

      {feedback.escalated && !feedback.resolved && (
        <div className="inline-form" style={{ marginTop: 12 }}>
          <div className="field" style={{ flex: 1, minWidth: 220, margin: 0 }}>
            <label>Resolution note (optional)</label>
            <input value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => onResolve(feedback.feedback_id, note)}>
            Resolve
          </button>
        </div>
      )}
      {feedback.resolved && feedback.resolution && (
        <div className="muted" style={{ marginTop: 10, fontSize: "0.85rem" }}>
          <StatusChip tone="resolved">resolved</StatusChip> by {feedback.resolution.resolved_by} —{" "}
          <span className="timestamp">{new Date(feedback.resolution.resolved_at).toLocaleString()}</span>
          {feedback.resolution.note && <div>{feedback.resolution.note}</div>}
        </div>
      )}
    </div>
  );
}
