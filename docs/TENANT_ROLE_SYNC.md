# Tenant Role Sync

Tenant role sync turns RAL-managed tenant user roles into OpenFGA tuples.

This is the bridge between:

- Frappe/RAL tenant role assignments;
- durable admin/provisioning state;
- OpenFGA tenant relations;
- pre-retrieval AI authorization.

## Mapping

| RAL tenant role | OpenFGA tenant relation | OpenFGA object |
|---|---|---|
| `employee` | `employee` | `tenant:<tenant_id>` |
| `manager` | `manager` | `tenant:<tenant_id>` |
| `hr_admin` | `hr_admin` | `tenant:<tenant_id>` |
| `system_admin` | `system_admin` | `tenant:<tenant_id>` |

Example:

```text
AccessRoleAssignment(tenant_id="acme", user_id="sarah", roles=("employee", "manager"))
        ↓
("user:sarah", "employee", "tenant:acme")
("user:sarah", "manager", "tenant:acme")
```

## Rules

- Role sync is tenant-scoped.
- Foreign-tenant existing tuples are ignored.
- Stale role tuples for the active tenant can be deleted.
- Desired tuples are written deterministically.
- Tuple writes remain idempotent through the existing OpenFGA writer behavior.
- This controls classification masks before retrieval; it does not replace document-level authorization.

## Current implementation

`glue.tenant_role_sync` provides:

- `tenant_role_tuples(...)`
- `plan_tenant_role_sync(...)`
- `sync_tenant_roles(...)`

The sync function accepts a role-assignment store protocol and tuple-writer protocol, so it can work with:

- in-memory admin controls;
- SQLite admin controls;
- future PostgreSQL tenant provisioning stores;
- test fakes;
- the real OpenFGA tuple writer.

`glue.app.create_app(..., tenant_role_syncer=...)` can inject this sync path into the HR admin role-assignment API.

When configured:

1. the role assignment is persisted through `AdminControlStore`;
2. the tenant role syncer is called for the authenticated tenant;
3. if the sync fails, the API returns a retryable `503`.

When no syncer is configured, the route preserves local/test behavior and only stores the assignment. Production deployments should configure a syncer so role changes update OpenFGA promptly.

## Future work

The next production step is to trigger this sync from durable tenant provisioning and Frappe role changes. The trigger must be idempotent, retryable, and audited, including a background reconciliation job for failed syncs.
