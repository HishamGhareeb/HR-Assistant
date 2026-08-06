import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const NAV_ITEMS = [
  { to: "/chat", label: "Chat" },
  { to: "/suggestions", label: "Suggestion Inbox" },
  { to: "/feedback", label: "Feedback & Quality" },
  { to: "/payroll", label: "Bahrain Payroll" },
  { to: "/admin", label: "Admin Console" },
];

export function Layout() {
  const { session, logout } = useAuth();
  if (!session) return null;

  const initial = session.userId.slice(0, 1).toUpperCase();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar__brand">HR Assistant</div>

        <div className="sidebar__persona">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span
              style={{
                width: 30,
                height: 30,
                borderRadius: "50%",
                background: "rgba(255,255,255,0.16)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              {initial}
            </span>
            <div>
              <div className="sidebar__persona-name">{session.userId}</div>
              <div className="sidebar__persona-meta">tenant: {session.tenantId}</div>
            </div>
          </div>
        </div>

        <nav className="sidebar__nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `sidebar__link${isActive ? " active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">
          <button className="sidebar__signout" onClick={logout}>
            Switch persona / sign out
          </button>
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
