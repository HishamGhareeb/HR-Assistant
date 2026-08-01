from glue.postgres_rls_contract import TENANT_SCOPED_TABLES, load_tenant_rls_migration


def normalized_sql() -> str:
    return " ".join(load_tenant_rls_migration().lower().split())


def test_migration_enables_rls_on_every_tenant_scoped_table() -> None:
    sql = normalized_sql()

    for table in TENANT_SCOPED_TABLES:
        assert f"alter table ral_hr.{table} enable row level security" in sql


def test_every_tenant_scoped_table_has_current_tenant_policy() -> None:
    sql = normalized_sql()

    for table in TENANT_SCOPED_TABLES:
        assert f"on ral_hr.{table}" in sql
        assert "using (tenant_id = current_setting('app.tenant_id', true))" in sql
        assert "with check (tenant_id = current_setting('app.tenant_id', true))" in sql


def test_suggestions_keep_domain_state_invariants() -> None:
    sql = normalized_sql()

    assert "create type ral_hr.suggestion_status as enum" in sql
    assert "'pending'" in sql
    assert "'approved'" in sql
    assert "'rejected'" in sql
    assert "'dismissed'" in sql
    assert "suggestions_decision_consistency" in sql
    assert "status = 'pending' and decided_at is null and decided_by is null" in sql
    assert "status in ('approved', 'rejected', 'dismissed') and decided_at is not null and decided_by is not null" in sql


def test_decision_history_is_terminal_and_tenant_keyed() -> None:
    sql = normalized_sql()

    assert "create table ral_hr.suggestion_decisions" in sql
    assert "primary key (tenant_id, decision_id)" in sql
    assert "foreign key (tenant_id, suggestion_id) references ral_hr.suggestions (tenant_id, suggestion_id)" in sql
    assert "suggestion_decisions_terminal_only" in sql
    assert "action in ('approved', 'rejected', 'dismissed')" in sql


def test_admin_sync_tables_preserve_tenant_composite_keys() -> None:
    sql = normalized_sql()

    assert "create table ral_hr.integration_sync_runs" in sql
    assert "primary key (tenant_id, run_id)" in sql
    assert "create table ral_hr.integration_source_statuses" in sql
    assert "primary key (tenant_id, source_id)" in sql
    assert "foreign key (tenant_id, last_run_id) references ral_hr.integration_sync_runs (tenant_id, run_id)" in sql


def test_tenant_table_has_no_direct_tenant_scoped_access_policy() -> None:
    sql = normalized_sql()

    assert "alter table ral_hr.tenants enable row level security" in sql
    assert "create policy tenants_no_direct_tenant_access" in sql
    assert "using (false) with check (false)" in sql
