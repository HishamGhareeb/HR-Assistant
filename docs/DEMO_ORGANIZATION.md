# Seeded demo organization and guided pilot setup

A working pilot needs data and users before anyone can ask it a question.
`glue/demo_seed.py` defines a small, fixed, entirely synthetic dataset for
tenant `demo-org`, and `scripts/seed_demo_org.py` is the one-command guided
setup path that loads it. No real employee data is involved anywhere in
this flow.

## What gets seeded

Every doctype `glue/frappe_sync.py` maps, across every classification tier
the pipeline enforces:

| Doctype | Record | Classification |
|---|---|---|
| Employee | Farah Al Zayani (engineering) | INTERNAL |
| Employee | Priya Nair (engineering, reports to Farah) | INTERNAL |
| Leave Application | Priya's approved annual leave | INTERNAL |
| Appraisal | Priya's H1 2026 performance review | MANAGER_ONLY |
| Salary Slip | Priya's July 2026 salary slip | HR_ONLY |
| HR Policy | Annual Leave Policy | PUBLIC |
| HR Policy | Remote Work Policy | PUBLIC |
| HR Policy | Public Holiday Calendar | PUBLIC |

This is deliberately the same `FrappeRecord` shape and the same
`SyncEngine` every other Frappe record goes through (`docs/FRAPPE_SYNC.md`)
-- seeding a demo organization is not a parallel ingestion path, just a
synthetic source feeding the real one.

## Scripted personas

| user_id | Name | Role |
|---|---|---|
| `priya` | Priya Nair | Employee -- sees her own records and public policies |
| `farah` | Farah Al Zayani | Priya's manager -- sees her department's records, never salary data |
| `hr-demo` | Demo HR Admin | Full visibility; authorized for the suggestion review inbox, admin controls, and the answer-feedback quality dashboard |

Mint a signed bearer token for any persona the same way you would for a
real user (`tenant_id="demo-org"`, `sub="<persona user_id>"`) -- the demo
tenant is not a special case in `glue/auth.py`.

## Sample questions for a guided walkthrough

Six questions, each annotated with the `model_outcome` it should produce
and why -- deliberately covering the classification boundary, not just the
happy path:

1. **priya**: "How many days of annual leave do employees get per year?" -> `answered` (public policy)
2. **priya**: "What is the remote work policy?" -> `answered` (public policy)
3. **priya**: "What did my last performance review say?" -> `answered` (owner of a MANAGER_ONLY record)
4. **farah**: "What is Priya's salary?" -> `no_info` -- **not a bug**: `salary_record` has no "manager from department" relation in `openfga/model.fga` by design, so even Priya's own manager cannot see it
5. **hr-demo**: "What is Priya's salary?" -> `answered` (hr_admin viewer access)
6. **priya**: "Do we offer unlimited sabbaticals?" -> `no_info` -- not covered by the seeded policies; demonstrates the safe fallback and gets logged as an `UnansweredQuestion` on the HR quality dashboard (`docs/ANSWER_FEEDBACK_AND_QUALITY_ANALYTICS.md`)

Question 4 is worth walking a pilot prospect through explicitly: it is the
clearest, lowest-stakes demonstration that the assistant's authorization
boundary is real and enforced per-record, not just per-document-type.

## Running the guided setup

```bash
ONYX_API_URL=... ONYX_API_KEY=... OPENFGA_API_URL=... OPENFGA_STORE_ID=... \
    python scripts/seed_demo_org.py
```

Requires an already-provisioned OpenFGA store/model (`scripts/provision_openfga.py`)
and a reachable Onyx instance. Safe to re-run: `SyncEngine` diffs against
its checkpoint store, so a second run reports everything as unchanged
rather than re-creating records.

The script prints the personas, the sample questions, and the
`HR_REVIEWERS_JSON` / `HR_ADMINS_JSON` / `HR_FEEDBACK_REVIEWERS_JSON`
snippets for the `hr-demo` persona -- it does not write those environment
variables for you, so it can never silently overwrite a real deployment's
reviewer/admin map with demo values. Merge the printed snippet into
whichever of those variables your deployment already uses.
