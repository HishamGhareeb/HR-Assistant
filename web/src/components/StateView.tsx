import type { ReactNode } from "react";

export type StateKind = "loading" | "no_info" | "blocked" | "error" | "unauthorized" | "empty";

const ICONS: Record<StateKind, string> = {
  loading: "⏳",
  no_info: "ℹ️",
  blocked: "⛔",
  error: "⚠️",
  unauthorized: "🔒",
  empty: "—",
};

/** One shared component for every "safe state" the product must render
 * distinctly rather than a generic spinner-or-error: loading, no
 * information found, blocked by the output safety scanner, a dependency
 * error, a 403 authorization denial, and an empty list. */
export function StateView({ kind, children }: { kind: StateKind; children: ReactNode }) {
  return (
    <div className={`state-banner state-banner--${kind}`} role={kind === "error" || kind === "blocked" ? "alert" : "status"}>
      <span className="state-banner__icon" aria-hidden="true">
        {ICONS[kind]}
      </span>
      <div>{children}</div>
    </div>
  );
}

export function stateFromApiError(status: number): StateKind {
  if (status === 401 || status === 403) return "unauthorized";
  if (status === 404) return "empty";
  return "error";
}
