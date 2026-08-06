import { useState, type FormEvent } from "react";
import { useAuth } from "./AuthContext";
import { DEMO_PERSONAS, DEMO_TENANT_ID } from "../demo/personas";

export function PersonaLoginPage() {
  const { login, loginError, loggingIn } = useAuth();
  const [tenantId, setTenantId] = useState(DEMO_TENANT_ID);
  const [userId, setUserId] = useState("");
  const [pendingPersona, setPendingPersona] = useState<string | null>(null);

  async function loginAsPersona(personaUserId: string) {
    setPendingPersona(personaUserId);
    try {
      await login(DEMO_TENANT_ID, personaUserId);
    } catch {
      // loginError is already set by the auth context; nothing else to do.
    } finally {
      setPendingPersona(null);
    }
  }

  async function handleManualSubmit(event: FormEvent) {
    event.preventDefault();
    if (!tenantId.trim() || !userId.trim()) return;
    try {
      await login(tenantId.trim(), userId.trim());
    } catch {
      // loginError already set.
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-card__brand">HR Assistant</div>
        <p className="login-card__tagline">
          Ask a question, get a grounded answer, and let HR review what needs a human — sign in as a
          scripted demo persona to try it.
        </p>

        <div className="persona-list">
          {DEMO_PERSONAS.map((persona) => (
            <button
              key={persona.userId}
              className="persona-option"
              disabled={loggingIn}
              onClick={() => loginAsPersona(persona.userId)}
            >
              <span className="persona-avatar">{persona.displayName.slice(0, 1)}</span>
              <span>
                <span className="persona-option__name">
                  {persona.displayName}
                  {loggingIn && pendingPersona === persona.userId ? " — signing in…" : ""}
                </span>
                <span className="persona-option__desc">{persona.roleDescription}</span>
              </span>
            </button>
          ))}
        </div>

        <div className="divider">or sign in manually</div>

        <form onSubmit={handleManualSubmit} className="stack">
          <div className="field">
            <label htmlFor="tenantId">Tenant ID</label>
            <input id="tenantId" value={tenantId} onChange={(e) => setTenantId(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="userId">User ID</label>
            <input id="userId" value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="e.g. hr-demo" />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loggingIn}>
            {loggingIn ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {loginError && (
          <div className="state-banner state-banner--error" style={{ marginTop: 16 }} role="alert">
            <span className="state-banner__icon" aria-hidden="true">
              ⚠️
            </span>
            <div>{loginError}</div>
          </div>
        )}
      </div>
    </div>
  );
}
