-- HIS-52: production schema contract for RAL HRMS sync checkpoints.
--
-- This migration extends the PostgreSQL/RLS persistence contract after the
-- SyncEngine checkpoint protocol gained a durable SQLite bridge. It is not
-- wired into application startup yet.

BEGIN;

CREATE TABLE ral_hr.sync_checkpoints (
    tenant_id TEXT NOT NULL REFERENCES ral_hr.tenants (tenant_id),
    doctype TEXT NOT NULL,
    name TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    document_id TEXT,
    tuples_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, doctype, name),
    CONSTRAINT sync_checkpoints_nonblank_doctype CHECK (length(btrim(doctype)) > 0),
    CONSTRAINT sync_checkpoints_nonblank_name CHECK (length(btrim(name)) > 0),
    CONSTRAINT sync_checkpoints_nonblank_content_hash CHECK (length(btrim(content_hash)) > 0)
);

CREATE INDEX idx_sync_checkpoints_tenant_doctype
    ON ral_hr.sync_checkpoints (tenant_id, doctype);

CREATE INDEX idx_sync_checkpoints_tenant_updated
    ON ral_hr.sync_checkpoints (tenant_id, updated_at DESC);

ALTER TABLE ral_hr.sync_checkpoints ENABLE ROW LEVEL SECURITY;

CREATE POLICY sync_checkpoints_isolation
    ON ral_hr.sync_checkpoints
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
