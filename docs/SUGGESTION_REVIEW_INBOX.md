# HR suggestion review inbox

The assistant remains read-only. Model suggestions are persisted as review
items so authorized HR users can make explicit human decisions, but an
approval only records that decision. It does not call RAL HRMS, Onyx, or any
other HR source-system mutation API.

## Lifecycle

Suggestions start as `pending` and can transition once to one of:

- `approved`
- `rejected`
- `dismissed`

Each transition appends a decision-history entry with the suggestion ID,
tenant ID, reviewer user ID, timestamp, action, and optional reviewer note.
Decision history is immutable at the service layer: repeating the same
decision by the same reviewer is idempotent, while changing an already
decided suggestion returns a conflict.

## Authorization and tenant isolation

The review endpoints first verify the signed bearer token into
`Identity(tenant_id, user_id)`, then authorize that identity as an HR
reviewer before listing, viewing, or deciding any suggestion. The static
reviewer map is tenant-scoped:

```json
{"acme": ["hr-1", "hr-2"]}
```

A reviewer authorized for one tenant is not authorized for another tenant
unless that tenant has its own explicit entry. Store lookups always include
the caller tenant ID, so a guessed suggestion ID from another tenant is
reported as not found.

## API

- `GET /v1/hr/suggestions?status_filter=pending`
- `GET /v1/hr/suggestions/{suggestion_id}`
- `POST /v1/hr/suggestions/{suggestion_id}/decision`

Decision request body:

```json
{"action": "approved", "note": "Verified by HR."}
```

`action` must be `approved`, `rejected`, or `dismissed`.

## Persistence

`SUGGESTION_STORE_PATH` controls the append-only JSONL state file and
defaults to `.tmp/suggestions.jsonl`. `HR_REVIEWERS_JSON` controls the
tenant-scoped reviewer map and defaults to `{}`, which means no user can
access the inbox until reviewers are explicitly provisioned.

The suggestion store is application state, not an audit log. Existing audit
and observability surfaces continue to avoid raw questions, document chunks,
and user identifiers beyond the established privacy-preserving fields.
