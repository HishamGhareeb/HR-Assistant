import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { api, ApiError } from "../api/client";

export interface Session {
  tenantId: string;
  userId: string;
  token: string;
  expiresAt: number; // epoch ms
}

interface AuthContextValue {
  session: Session | null;
  loginError: string | null;
  loggingIn: boolean;
  login: (tenantId: string, userId: string) => Promise<void>;
  logout: () => void;
}

const STORAGE_KEY = "hr-assistant-session";

const AuthContext = createContext<AuthContextValue | null>(null);

function loadStoredSession(): Session | null {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const session = JSON.parse(raw) as Session;
    if (session.expiresAt <= Date.now()) return null;
    return session;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => loadStoredSession());
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loggingIn, setLoggingIn] = useState(false);

  const login = useCallback(async (tenantId: string, userId: string) => {
    setLoggingIn(true);
    setLoginError(null);
    try {
      const minted = await api.mintDevToken({ tenant_id: tenantId, user_id: userId });
      const next: Session = {
        tenantId,
        userId,
        token: minted.access_token,
        expiresAt: Date.now() + minted.expires_in * 1000,
      };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setSession(next);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setLoginError(
          "Dev sign-in is not enabled on this API. Set DEV_AUTH_ENABLED=true locally " +
            "(see scripts/generate_dev_auth_keypair.py), or use a real signed token from your identity provider.",
        );
      } else if (err instanceof ApiError) {
        setLoginError(err.detail);
      } else {
        setLoginError("Could not reach the API. Is it running?");
      }
      throw err;
    } finally {
      setLoggingIn(false);
    }
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    setSession(null);
  }, []);

  const value = useMemo(
    () => ({ session, loginError, loggingIn, login, logout }),
    [session, loginError, loggingIn, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside an AuthProvider");
  return ctx;
}
