import { useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import { api, ApiError } from "../api/client";
import type { FeedbackReasonCode, QuestionResponse } from "../api/types";
import { StateView, stateFromApiError } from "../components/StateView";

const REASON_CODES: { value: FeedbackReasonCode; label: string }[] = [
  { value: "incorrect", label: "Incorrect" },
  { value: "incomplete", label: "Incomplete" },
  { value: "irrelevant", label: "Irrelevant" },
  { value: "outdated", label: "Outdated" },
  { value: "other", label: "Other" },
];

type FeedbackState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "submitted"; helpful: boolean; escalated: boolean }
  | { status: "error"; message: string };

interface Turn {
  id: string;
  question: string;
  result: QuestionResponse | null;
  errorMessage: string | null;
  errorStatus: number | null;
  feedback: FeedbackState;
}

/** No conversation history is persisted server-side today -- each
 * POST /v1/questions call is independent. This turn list is client-side
 * only and resets on reload; that's an honest reflection of the current
 * API, not a missing feature hidden from the user. */
export function ChatPage() {
  const { session } = useAuth();
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pending, setPending] = useState(false);

  if (!session) return null;

  async function ask(event: FormEvent) {
    event.preventDefault();
    if (!session) return;
    const text = question.trim();
    if (!text || pending) return;

    const turnId = crypto.randomUUID();
    setTurns((prev) => [
      ...prev,
      { id: turnId, question: text, result: null, errorMessage: null, errorStatus: null, feedback: { status: "idle" } },
    ]);
    setQuestion("");
    setPending(true);

    try {
      const result = await api.askQuestion(session.token, { question: text });
      setTurns((prev) => prev.map((t) => (t.id === turnId ? { ...t, result } : t)));
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : "Could not reach the API.";
      const status = err instanceof ApiError ? err.status : null;
      setTurns((prev) => prev.map((t) => (t.id === turnId ? { ...t, errorMessage: message, errorStatus: status } : t)));
    } finally {
      setPending(false);
    }
  }

  function updateFeedback(turnId: string, feedback: FeedbackState) {
    setTurns((prev) => prev.map((t) => (t.id === turnId ? { ...t, feedback } : t)));
  }

  async function submitFeedback(turn: Turn, helpful: boolean, reasonCode?: FeedbackReasonCode, note?: string) {
    if (!turn.result || !session) return;
    updateFeedback(turn.id, { status: "submitting" });
    try {
      const feedback = await api.submitFeedback(session.token, turn.result.request_id, {
        question: turn.question,
        answer: turn.result.answer,
        helpful,
        reason_code: reasonCode,
        note,
      });
      updateFeedback(turn.id, { status: "submitted", helpful: feedback.helpful, escalated: feedback.escalated });
    } catch (err) {
      updateFeedback(turn.id, {
        status: "error",
        message: err instanceof ApiError ? err.detail : "Could not submit feedback.",
      });
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Ask HR Assistant</h1>
        <p>Answers are grounded only in what {session.tenantId} has authorized you to see.</p>
      </div>

      <div className="chat-log">
        {turns.length === 0 && (
          <StateView kind="empty">Ask something like &ldquo;How many days of annual leave do I get?&rdquo;</StateView>
        )}
        {turns.map((turn) => (
          <ChatTurnView key={turn.id} turn={turn} onFeedback={(h, r, n) => submitFeedback(turn, h, r, n)} />
        ))}
      </div>

      <form className="chat-composer" onSubmit={ask}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question…"
          disabled={pending}
          aria-label="Question"
        />
        <button type="submit" className="btn btn-primary" disabled={pending || !question.trim()}>
          {pending ? "Asking…" : "Ask"}
        </button>
      </form>
    </>
  );
}

function ChatTurnView({
  turn,
  onFeedback,
}: {
  turn: Turn;
  onFeedback: (helpful: boolean, reasonCode?: FeedbackReasonCode, note?: string) => void;
}) {
  return (
    <div className="chat-turn">
      <div className="chat-turn chat-turn--question">
        <div className="chat-bubble chat-bubble--question">{turn.question}</div>
      </div>

      <div className="chat-turn chat-turn--answer">
        {!turn.result && !turn.errorMessage && <StateView kind="loading">Thinking…</StateView>}

        {turn.errorMessage && (
          <StateView kind={turn.errorStatus ? stateFromApiError(turn.errorStatus) : "error"}>
            {turn.errorMessage}
          </StateView>
        )}

        {turn.result && (
          <>
            <div className={`chat-bubble chat-bubble--answer${turn.result.blocked ? " state-banner--blocked" : ""}`}>
              {turn.result.blocked && (
                <div className="chat-meta" style={{ marginBottom: 6, color: "var(--color-danger)" }}>
                  ⛔ Held by the output safety scanner
                </div>
              )}
              {turn.result.answer}
              {turn.result.suggestions.map((s, i) => (
                <div className="suggestion-badge" key={i}>
                  <span className="suggestion-badge__category">{s.category.replace(/_/g, " ")}</span>
                  <span>{s.reasoning}</span>
                  {s.record_reference && <span className="chat-meta">Ref: {s.record_reference}</span>}
                </div>
              ))}
            </div>
            <div className="chat-meta">request_id: {turn.result.request_id}</div>
            <FeedbackControl feedback={turn.feedback} onFeedback={onFeedback} />
          </>
        )}
      </div>
    </div>
  );
}

function FeedbackControl({
  feedback,
  onFeedback,
}: {
  feedback: FeedbackState;
  onFeedback: (helpful: boolean, reasonCode?: FeedbackReasonCode, note?: string) => void;
}) {
  const [pickingReason, setPickingReason] = useState(false);
  const [reason, setReason] = useState<FeedbackReasonCode>("incomplete");
  const [note, setNote] = useState("");

  if (feedback.status === "submitted") {
    return (
      <div className="feedback-row">
        <span className="feedback-row__label">
          {feedback.helpful ? "Thanks for the feedback." : feedback.escalated ? "Thanks — flagged for HR review." : "Thanks for the feedback."}
        </span>
      </div>
    );
  }

  if (pickingReason) {
    return (
      <div className="stack" style={{ marginTop: 6, maxWidth: "40ch" }}>
        <div className="field" style={{ margin: 0 }}>
          <label>Why wasn&apos;t this helpful?</label>
          <select value={reason} onChange={(e) => setReason(e.target.value as FeedbackReasonCode)}>
            {REASON_CODES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field" style={{ margin: 0 }}>
          <label>Note (optional)</label>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} />
        </div>
        <button
          className="btn btn-primary btn-sm"
          disabled={feedback.status === "submitting"}
          onClick={() => onFeedback(false, reason, note || undefined)}
        >
          {feedback.status === "submitting" ? "Submitting…" : "Submit"}
        </button>
      </div>
    );
  }

  return (
    <div className="feedback-row">
      <span className="feedback-row__label">Was this helpful?</span>
      <button
        className="icon-btn"
        aria-label="Helpful"
        disabled={feedback.status === "submitting"}
        onClick={() => onFeedback(true)}
      >
        👍
      </button>
      <button
        className="icon-btn"
        aria-label="Not helpful"
        disabled={feedback.status === "submitting"}
        onClick={() => setPickingReason(true)}
      >
        👎
      </button>
      {feedback.status === "error" && <span className="muted">{feedback.message}</span>}
    </div>
  );
}
