# Seeded 25-person demo organization and guided pilot setup

A credible pilot needs enough data to feel like a real company. `glue/demo_seed.py`
defines a fixed, entirely synthetic 25-person Bahrain company for tenant
`demo-org`, and `scripts/seed_demo_org.py` loads it through the same
`HrSourceRecord` / `SyncEngine` path used by normal RAL HRMS source data.
No real employee data is involved anywhere in this flow.

## Demo company

| Field | Value |
|---|---|
| Company | Pearl Horizon Trading W.L.L. |
| Tenant ID | `demo-org` |
| Employee count | 25 |
| Departments | Leadership, Engineering, Product, Sales, Customer Success, Finance, People Ops, Operations |
| Payroll country | Bahrain |

## What gets seeded

The seed covers every record type `glue/hr_source_sync.py` maps, every
classification tier the pipeline enforces, and enough records to make the
frontend demo feel populated rather than toy-sized.

| Record type | Count | Classification / purpose |
|---|---:|---|
| Department | 8 | Source structure for manager/team relationships |
| Employee | 25 | INTERNAL employee profiles across the full org chart |
| Leave Application | 24 | INTERNAL leave records for employees below the CEO |
| Appraisal | 23 | MANAGER_ONLY performance records for non-executive staff |
| Salary Slip | 25 | HR_ONLY salary records for every employee |
| HR Policy | 7 | PUBLIC tenant-wide policy documents |

The policies include annual leave, remote work, public holidays, Bahrain
payroll compliance, HR data access, probation/reviews, and expense claims.

## Org shape

| Department | Example seeded users |
|---|---|
| Leadership | `layla`, `omar` |
| Engineering | `farah`, `priya`, `yusuf`, `noura`, `daniel` |
| Product | `mariam`, `ahmed`, `sara` |
| Sales | `khalid`, `fatima`, `raj`, `lina` |
| Customer Success | `hassan`, `amina`, `joel` |
| Finance | `reem`, `zainab`, `miguel` |
| People Ops | `hr-demo`, `salma`, `ravi` |
| Operations | `tariq`, `mei` |

## Scripted personas shown in the frontend

The frontend sign-in screen intentionally shows a small representative set,
not all 25 employees:

| user_id | Name | Demo role |
|---|---|---|
| `priya` | Priya Nair | Employee; sees her own records and public policies |
| `noura` | Noura Al Khalifa | Bahraini employee persona for payroll/localization walkthroughs |
| `farah` | Farah Al Zayani | Engineering manager; sees team HR/performance records, never salary |
| `reem` | Reem Al Saffar | Finance manager; useful for payroll/WPS demos |
| `hr-demo` | Demo HR Admin | Full HR visibility plus suggestion, admin, and feedback dashboards |

Mint a signed bearer token for any persona the same way you would for a
real user (`tenant_id="demo-org"`, `sub="<persona user_id>"`). The demo
tenant is not a special case in `glue/auth.py`.

## Sample questions for a guided walkthrough

These questions deliberately cover the authorization boundary, not just the
happy path:

1. **priya**: "How many days of annual leave do employees get per year?" -> `answered` (public policy)
2. **priya**: "What is the remote work policy?" -> `answered` (public policy)
3. **priya**: "What did my last performance review say?" -> `answered` (owner of a MANAGER_ONLY record)
4. **farah**: "What is Priya's salary?" -> `no_info` -- **not a bug**: `salary_record` has no "manager from department" relation in `openfga/model.fga` by design, so even Priya's own manager cannot see it
5. **hr-demo**: "What is Priya's salary?" -> `answered` (hr_admin viewer access)
6. **reem**: "What is the Bahrain payroll compliance policy?" -> `answered` (public policy, useful before opening the Payroll page)
7. **priya**: "Do we offer unlimited sabbaticals?" -> `no_info` -- not covered by the seeded policies; demonstrates the safe fallback and gets logged as an `UnansweredQuestion` on the HR quality dashboard

Question 4 is worth walking a pilot prospect through explicitly: it is the
clearest, lowest-stakes demonstration that the assistant's authorization
boundary is real and enforced per record.

## Running the guided setup

```bash
ONYX_API_URL=... ONYX_API_KEY=... OPENFGA_API_URL=... OPENFGA_STORE_ID=... \
    python scripts/seed_demo_org.py
```

Requires an already-provisioned OpenFGA store/model (`scripts/provision_openfga.py`)
and a reachable Onyx instance. Safe to re-run: `SyncEngine` diffs against
its checkpoint store, so a second run reports everything as unchanged
rather than re-creating records.

The script prints the personas, sample questions, and the
`HR_REVIEWERS_JSON` / `HR_ADMINS_JSON` / `HR_FEEDBACK_REVIEWERS_JSON`
snippets for the `hr-demo` persona. It does not write those environment
variables for you, so it can never silently overwrite a real deployment's
reviewer/admin map with demo values.
