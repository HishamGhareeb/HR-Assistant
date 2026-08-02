-- HIS-43: PostgreSQL tenant and row-level-security foundation.
--
-- This migration is the production target contract for durable SaaS
-- persistence. It is intentionally not wired into application startup yet.
-- Route handlers must continue to depend on protocols while concrete stores
-- move from JSONL/SQLite bridges to PostgreSQL-backed implementations.

BEGIN;

CREATE SCHEMA IF NOT EXISTS ral_hr;

CREATE TYPE ral_hr.tenant_status AS ENUM (
    'active',
    'suspended',
    'disabled'
);

CREATE TYPE ral_hr.tenant_role AS ENUM (
    'employee',
    'manager',
    'hr_admin',
    'system_admin'
);

CREATE TYPE ral_hr.suggestion_status AS ENUM (
    'pending',
    'approved',
    'rejected',
    'dismissed'
);

CREATE TABLE ral_hr.tenants (
    tenant_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    country_code CHAR(2) NOT NULL,
    status ral_hr.tenant_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT tenants_nonblank_id CHECK (length(btrim(tenant_id)) > 0),
    CONSTRAINT tenants_country_uppercase CHECK (country_code = upper(country_code))
);

CREATE TABLE ral_hr.tenant_users (
    tenant_id TEXT NOT NULL REFERENCES ral_hr.tenants (tenant_id),
    user_id TEXT NOT NULL,
    display_name TEXT,
    email TEXT,
    status ral_hr.tenant_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, user_id),
    CONSTRAINT tenant_users_nonblank_user CHECK (length(btrim(user_id)) > 0)
);

CREATE TABLE ral_hr.tenant_user_roles (
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role ral_hr.tenant_role NOT NULL,
    granted_by TEXT NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, user_id, role),
    FOREIGN KEY (tenant_id, user_id)
        REFERENCES ral_hr.tenant_users (tenant_id, user_id),
    FOREIGN KEY (tenant_id, granted_by)
        REFERENCES ral_hr.tenant_users (tenant_id, user_id)
);

CREATE TABLE ral_hr.suggestions (
    tenant_id TEXT NOT NULL REFERENCES ral_hr.tenants (tenant_id),
    suggestion_id TEXT NOT NULL,
    status ral_hr.suggestion_status NOT NULL DEFAULT 'pending',
    category TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    record_reference TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ,
    decided_by TEXT,
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, suggestion_id),
    CONSTRAINT suggestions_decision_consistency CHECK (
        (status = 'pending' AND decided_at IS NULL AND decided_by IS NULL)
        OR
        (status IN ('approved', 'rejected', 'dismissed') AND decided_at IS NOT NULL AND decided_by IS NOT NULL)
    )
);

CREATE TABLE ral_hr.suggestion_decisions (
    tenant_id TEXT NOT NULL,
    suggestion_id TEXT NOT NULL,
    decision_id TEXT NOT NULL,
    action ral_hr.suggestion_status NOT NULL,
    decided_by TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL,
    note TEXT,
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, decision_id),
    FOREIGN KEY (tenant_id, suggestion_id)
        REFERENCES ral_hr.suggestions (tenant_id, suggestion_id),
    FOREIGN KEY (tenant_id, decided_by)
        REFERENCES ral_hr.tenant_users (tenant_id, user_id),
    CONSTRAINT suggestion_decisions_terminal_only CHECK (action IN ('approved', 'rejected', 'dismissed'))
);

CREATE TABLE ral_hr.integration_sync_runs (
    tenant_id TEXT NOT NULL REFERENCES ral_hr.tenants (tenant_id),
    run_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    created_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    deleted_count INTEGER NOT NULL DEFAULT 0,
    unchanged_count INTEGER NOT NULL DEFAULT 0,
    failed_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, run_id),
    CONSTRAINT integration_sync_runs_nonnegative_counts CHECK (
        created_count >= 0
        AND updated_count >= 0
        AND deleted_count >= 0
        AND unchanged_count >= 0
    )
);

CREATE TABLE ral_hr.integration_source_statuses (
    tenant_id TEXT NOT NULL REFERENCES ral_hr.tenants (tenant_id),
    source_id TEXT NOT NULL,
    last_action TEXT NOT NULL,
    last_status TEXT NOT NULL,
    last_run_id TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, source_id),
    FOREIGN KEY (tenant_id, last_run_id)
        REFERENCES ral_hr.integration_sync_runs (tenant_id, run_id)
);

CREATE INDEX idx_tenant_users_tenant_status
    ON ral_hr.tenant_users (tenant_id, status);

CREATE INDEX idx_tenant_user_roles_tenant_role
    ON ral_hr.tenant_user_roles (tenant_id, role);

CREATE INDEX idx_suggestions_tenant_status_created
    ON ral_hr.suggestions (tenant_id, status, created_at DESC);

CREATE INDEX idx_suggestion_decisions_tenant_suggestion_decided
    ON ral_hr.suggestion_decisions (tenant_id, suggestion_id, decided_at ASC);

CREATE INDEX idx_sync_runs_tenant_started
    ON ral_hr.integration_sync_runs (tenant_id, started_at DESC);

CREATE INDEX idx_source_statuses_tenant_updated
    ON ral_hr.integration_source_statuses (tenant_id, updated_at DESC);

ALTER TABLE ral_hr.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE ral_hr.tenant_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE ral_hr.tenant_user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE ral_hr.suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ral_hr.suggestion_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ral_hr.integration_sync_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ral_hr.integration_source_statuses ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_users_isolation
    ON ral_hr.tenant_users
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY tenant_user_roles_isolation
    ON ral_hr.tenant_user_roles
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY suggestions_isolation
    ON ral_hr.suggestions
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY suggestion_decisions_isolation
    ON ral_hr.suggestion_decisions
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY integration_sync_runs_isolation
    ON ral_hr.integration_sync_runs
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY integration_source_statuses_isolation
    ON ral_hr.integration_source_statuses
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Tenants are only readable/writable through provisioning/service-owner paths.
-- Ordinary tenant-scoped application roles should not query this table directly.
CREATE POLICY tenants_no_direct_tenant_access
    ON ral_hr.tenants
    USING (false)
    WITH CHECK (false);

COMMIT;
