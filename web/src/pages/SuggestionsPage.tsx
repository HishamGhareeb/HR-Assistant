import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api, ApiError } from "../api/client";
import type { ReviewSuggestionResponse, SuggestionStatus } from "../api/types";
import { StateView, stateFromApiError } from "../components/StateView";
import { StatusChip } from "../components/StatusChip";

const FILTERS: { value: SuggestionStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "dismissed", label: "Dismissed" },
];

export function SuggestionsPage() {
  const { session } = useAuth();
  const [filter, setFilter] = useState<SuggestionStatus | "all">("pending");
  const [suggestions, setSuggestions] = useState<ReviewSuggestionResponse[] | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    if (!session) return;
    setLoading(true);
    setErrorMessage(null);
    setErrorStatus(null);
    try {
      const result = await api.listSuggestions(session.token, filter === "all" ? undefined : filter);
      setSuggestions(result);
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.detail : "Could not reach the API.");
      setErrorStatus(err instanceof ApiError ? err.status : null);
      setSuggestions(null);
    } finally {
      setLoading(false);
    }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    load();
  }, [filter, session?.token]);

  async function decide(suggestionId: string, action: SuggestionStatus, note: string) {
    if (!session) return;
    try {
      const updated = await api.decideSuggestion(session.token, suggestionId, { action, note: note || undefined });
      setSuggestions((prev) => (prev ? prev.map((s) => (s.suggestion_id === suggestionId ? updated : s)) : prev));
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.detail : "Could not submit the decision.");
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Suggestion Review Inbox</h1>
        <p>Model suggestions are review records only — approving one never mutates RAL HRMS automatically.</p>
      </div>

      <div className="toolbar">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            className={`btn btn-sm ${filter === f.value ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && <StateView kind="loading">Loading suggestions…</StateView>}
      {!loading && errorMessage && (
        <StateView kind={errorStatus ? stateFromApiError(errorStatus) : "error"}>
          {errorStatus === 403
            ? "You're not authorized to review suggestions for this tenant."
            : errorMessage}
        </StateView>
      )}
      {!loading && !errorMessage && suggestions && suggestions.length === 0 && (
        <StateView kind="empty">No suggestions match this filter.</StateView>
      )}

      {!loading && suggestions && suggestions.length > 0 && (
        <div className="stack">
          {suggestions.map((s) => (
            <SuggestionCard key={s.suggestion_id} suggestion={s} onDecide={decide} />
          ))}
        </div>
      )}
    </>
  );
}

function SuggestionCard({
  suggestion,
  onDecide,
}: {
  suggestion: ReviewSuggestionResponse;
  onDecide: (id: string, action: SuggestionStatus, note: string) => void;
}) {
  const [note, setNote] = useState("");

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontWeight: 700 }}>{suggestion.category.replace(/_/g, " ")}</div>
          <p className="muted" style={{ margin: "4px 0" }}>
            {suggestion.reasoning}
          </p>
          {suggestion.record_reference && <div className="chat-meta">Ref: {suggestion.record_reference}</div>}
        </div>
        <StatusChip tone={suggestion.status}>{suggestion.status}</StatusChip>
      </div>

      {suggestion.status === "pending" ? (
        <div className="inline-form" style={{ marginTop: 14 }}>
          <div className="field" style={{ flex: 1, minWidth: 220, margin: 0 }}>
            <label>Note (optional)</label>
            <input value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => onDecide(suggestion.suggestion_id, "approved", note)}>
            Approve
          </button>
          <button className="btn btn-danger btn-sm" onClick={() => onDecide(suggestion.suggestion_id, "rejected", note)}>
            Reject
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => onDecide(suggestion.suggestion_id, "dismissed", note)}>
            Dismiss
          </button>
        </div>
      ) : (
        <div className="muted" style={{ marginTop: 10, fontSize: "0.85rem" }}>
          Decided by {suggestion.decided_by} at{" "}
          <span className="timestamp">{suggestion.decided_at && new Date(suggestion.decided_at).toLocaleString()}</span>
        </div>
      )}

      {suggestion.decision_history.length > 0 && (
        <details style={{ marginTop: 10 }}>
          <summary className="muted" style={{ cursor: "pointer", fontSize: "0.82rem" }}>
            Decision history ({suggestion.decision_history.length})
          </summary>
          <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: "0.85rem" }}>
            {suggestion.decision_history.map((d) => (
              <li key={d.decision_id}>
                <StatusChip tone={d.action}>{d.action}</StatusChip> by {d.decided_by} —{" "}
                <span className="timestamp">{new Date(d.decided_at).toLocaleString()}</span>
                {d.note && <div className="muted">{d.note}</div>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
