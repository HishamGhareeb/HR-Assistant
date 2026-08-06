import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api, ApiError } from "../api/client";
import type { AdminRoleAssignmentResponse, AdminSourceStatusResponse, AdminSyncRunResponse, TenantRole } from "../api/types";
import { StateView, stateFromApiError } from "../components/StateView";
import { StatusChip } from "../components/StatusChip";

const ALL_ROLES: TenantRole[] = ["employee", "manager", "hr_admin", "system_admin"];

export function AdminPage() {
  const { session } = useAuth();
  const [sources, setSources] = useState<AdminSourceStatusResponse[] | null>(null);
  const [runs, setRuns] = useState<AdminSyncRunResponse[] | null>(null);
  const [roles, setRoles] = useState<AdminRoleAssignmentResponse[] | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    if (!session) return;
    setLoading(true);
    setErrorMessage(null);
    setErrorStatus(null);
    try {
      const [sourcesResult, runsResult, rolesResult] = await Promise.all([
        api.listAdminSources(session.token),
        api.listAdminSyncRuns(session.token),
        api.listRoleAssignments(session.token),
      ]);
      setSources(sourcesResult);
      setRuns(runsResult);
      setRoles(rolesResult);
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
  }, [session?.token]);

  async function resync(sourceId: string, doctype: string, name: string, fieldsJson: string, deleted: boolean) {
    if (!session) return;
    setNotice(null);
    let fields: Record<string, unknown> = {};
    try {
      fields = fieldsJson.trim() ? JSON.parse(fieldsJson) : {};
    } catch {
      setNotice("Fields must be valid JSON, e.g. {\"user_id\": \"priya\", \"department\": \"engineering\"}");
      return;
    }
    try {
      const run = await api.resyncAdminRecords(session.token, {
        source_id: sourceId,
        records: [{ doctype, name, fields, deleted }],
      });
      setNotice(`Sync run ${run.run_id}: ${run.status} (created ${run.created}, updated ${run.updated}, failed ${run.failed.length})`);
      load();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.detail : "Resync failed.");
    }
  }

  async function revoke(sourceId: string, doctype: string, name: string) {
    if (!session) return;
    setNotice(null);
    try {
      const run = await api.revokeAdminRecord(session.token, { source_id: sourceId, doctype, name });
      setNotice(`Sync run ${run.run_id}: ${run.status} (deleted ${run.deleted})`);
      load();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.detail : "Revoke failed.");
    }
  }

  async function setRoles_(userId: string, nextRoles: TenantRole[]) {
    if (!session) return;
    try {
      const updated = await api.setRoleAssignment(session.token, userId, { roles: nextRoles });
      setRoles((prev) => {
        const withoutUser = (prev ?? []).filter((r) => r.user_id !== userId);
        return [...withoutUser, updated];
      });
    } catch (err) {
      setNotice(err instanceof ApiError ? err.detail : "Could not update role assignment.");
    }
  }

  if (loading) {
    return (
      <>
        <div className="page-header">
          <h1>Admin Console</h1>
        </div>
        <StateView kind="loading">Loading admin console…</StateView>
      </>
    );
  }

  if (errorMessage) {
    return (
      <>
        <div className="page-header">
          <h1>Admin Console</h1>
        </div>
        <StateView kind={errorStatus ? stateFromApiError(errorStatus) : "error"}>
          {errorStatus === 403 ? "You're not authorized for HR admin controls on this tenant." : errorMessage}
        </StateView>
      </>
    );
  }

  return (
    <>
      <div className="page-header">
        <h1>Admin Console</h1>
        <p>Ingestion status, resync/revoke controls, and tenant role assignment.</p>
      </div>

      {notice && (
        <div className="state-banner state-banner--empty" style={{ marginBottom: 16 }}>
          {notice}
        </div>
      )}

      <div className="section-title">Source status</div>
      {sources && sources.length === 0 && <StateView kind="empty">No sources have synced yet.</StateView>}
      {sources && sources.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Last action</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.source_id}>
                  <td>{s.source_id}</td>
                  <td>{s.last_action}</td>
                  <td>
                    <StatusChip tone={s.last_status === "completed" ? "success" : s.last_status === "failed" ? "failed" : "pending"}>
                      {s.last_status}
                    </StatusChip>
                  </td>
                  <td className="timestamp">{new Date(s.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="section-title">Sync runs</div>
      {runs && runs.length === 0 && <StateView kind="empty">No sync runs yet.</StateView>}
      {runs && runs.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Run</th>
                <th>Action</th>
                <th>Status</th>
                <th>Created / Updated / Deleted / Failed</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.run_id}>
                  <td className="chat-meta">{r.run_id}</td>
                  <td>{r.action}</td>
                  <td>
                    <StatusChip tone={r.status === "completed" ? "success" : r.status === "failed" ? "failed" : "pending"}>
                      {r.status}
                    </StatusChip>
                  </td>
                  <td>
                    {r.created} / {r.updated} / {r.deleted} / {r.failed.length}
                  </td>
                  <td className="timestamp">{new Date(r.started_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="section-title">Resync a record</div>
      <ResyncForm onSubmit={resync} />

      <div className="section-title">Revoke a record</div>
      <RevokeForm onSubmit={revoke} />

      <div className="section-title">Role assignments</div>
      <RoleAssignments roles={roles ?? []} onSetRoles={setRoles_} />
    </>
  );
}

function ResyncForm({
  onSubmit,
}: {
  onSubmit: (sourceId: string, doctype: string, name: string, fieldsJson: string, deleted: boolean) => void;
}) {
  const [sourceId, setSourceId] = useState("synthetic");
  const [doctype, setDoctype] = useState("HR Policy");
  const [name, setName] = useState("");
  const [fieldsJson, setFieldsJson] = useState('{"title": "New Policy", "body": "..."}');

  return (
    <div className="card">
      <div className="inline-form">
        <div className="field" style={{ margin: 0 }}>
          <label>Source ID</label>
          <input value={sourceId} onChange={(e) => setSourceId(e.target.value)} />
        </div>
        <div className="field" style={{ margin: 0 }}>
          <label>Record type</label>
          <input value={doctype} onChange={(e) => setDoctype(e.target.value)} />
        </div>
        <div className="field" style={{ margin: 0 }}>
          <label>Record name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. POL-remote-work" />
        </div>
      </div>
      <div className="field">
        <label>Fields (JSON)</label>
        <textarea value={fieldsJson} onChange={(e) => setFieldsJson(e.target.value)} rows={3} />
      </div>
      <button
        className="btn btn-primary btn-sm"
        disabled={!name.trim()}
        onClick={() => onSubmit(sourceId, doctype, name, fieldsJson, false)}
      >
        Resync
      </button>
    </div>
  );
}

function RevokeForm({ onSubmit }: { onSubmit: (sourceId: string, doctype: string, name: string) => void }) {
  const [sourceId, setSourceId] = useState("synthetic");
  const [doctype, setDoctype] = useState("HR Policy");
  const [name, setName] = useState("");

  return (
    <div className="card">
      <div className="inline-form">
        <div className="field" style={{ margin: 0 }}>
          <label>Source ID</label>
          <input value={sourceId} onChange={(e) => setSourceId(e.target.value)} />
        </div>
        <div className="field" style={{ margin: 0 }}>
          <label>Record type</label>
          <input value={doctype} onChange={(e) => setDoctype(e.target.value)} />
        </div>
        <div className="field" style={{ margin: 0 }}>
          <label>Record name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <button className="btn btn-danger btn-sm" disabled={!name.trim()} onClick={() => onSubmit(sourceId, doctype, name)}>
          Revoke
        </button>
      </div>
    </div>
  );
}

function RoleAssignments({
  roles,
  onSetRoles,
}: {
  roles: AdminRoleAssignmentResponse[];
  onSetRoles: (userId: string, roles: TenantRole[]) => void;
}) {
  const [userId, setUserId] = useState("");
  const [selected, setSelected] = useState<Set<TenantRole>>(new Set());

  function toggle(role: TenantRole) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(role)) next.delete(role);
      else next.add(role);
      return next;
    });
  }

  return (
    <>
      {roles.length > 0 && (
        <div className="table-wrap" style={{ marginBottom: 14 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Roles</th>
                <th>Updated by</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((r) => (
                <tr key={r.user_id}>
                  <td>{r.user_id}</td>
                  <td style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                    {r.roles.map((role) => (
                      <StatusChip key={role} tone="neutral">
                        {role}
                      </StatusChip>
                    ))}
                  </td>
                  <td>{r.updated_by}</td>
                  <td className="timestamp">{new Date(r.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card">
        <div className="field">
          <label>User ID</label>
          <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="e.g. hr-2" />
        </div>
        <div style={{ display: "flex", gap: 14, marginBottom: 14 }}>
          {ALL_ROLES.map((role) => (
            <label key={role} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.88rem" }}>
              <input type="checkbox" checked={selected.has(role)} onChange={() => toggle(role)} />
              {role}
            </label>
          ))}
        </div>
        <button
          className="btn btn-primary btn-sm"
          disabled={!userId.trim()}
          onClick={() => onSetRoles(userId.trim(), Array.from(selected))}
        >
          Save role assignment
        </button>
      </div>
    </>
  );
}
