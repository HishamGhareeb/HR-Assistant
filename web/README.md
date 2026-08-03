# RAL HRMS frontend

React + Vite + TypeScript frontend for the HR Assistant pilot.

## What the demo includes

The default demo tenant is `demo-org`, representing **Pearl Horizon Trading
W.L.L.**, a synthetic 25-person Bahrain company. The seed data includes:

- 25 employees across 8 departments
- employee profiles
- leave applications
- performance appraisals
- salary slips
- tenant-wide HR policies
- Bahrain payroll/WPS policy coverage

Representative login personas are shown on the sign-in screen:

- `priya` — employee
- `noura` — Bahraini employee
- `farah` — engineering manager
- `reem` — finance manager
- `hr-demo` — HR admin

## Run locally

From the repository root:

```powershell
uv sync --extra dev
uv run python scripts/generate_dev_auth_keypair.py
```

Copy the printed values into your local `.env`, then start the API:

```powershell
uv run uvicorn glue.app:app --reload
```

In a second terminal:

```powershell
cd web
npm install
npm run dev
```

Open the Vite URL printed in the terminal, usually `http://localhost:5173`.

## Seed the 25-person demo organization

The UI can mint demo tokens locally, but real chat answers require the demo
records to be loaded into Onyx/OpenFGA:

```powershell
uv run python scripts/seed_demo_org.py
```

The script expects these environment variables to point at your local stack:

- `ONYX_API_URL`
- `ONYX_API_KEY`
- `OPENFGA_API_URL`
- `OPENFGA_STORE_ID`
- `OPENFGA_MODEL_ID` when applicable

Safe to re-run: the sync engine is idempotent and reports unchanged records
instead of duplicating the demo data.

## Useful walkthrough

1. Sign in as `priya` and ask: “How many days of annual leave do employees get per year?”
2. As `priya`, ask: “What did my last performance review say?”
3. Switch to `farah` and ask: “What is Priya's salary?” The expected result is no information, proving managers cannot see salary data.
4. Switch to `hr-demo` and ask the same salary question. HR should be able to see the HR-only record.
5. Open Feedback & Quality to see unanswered/escalated feedback.
6. Open Bahrain Payroll and run SIO, EOSB, and WPS sample validations.

## Verify before pushing

From `web/`:

```powershell
npm test
npm run build
```

From the repository root:

```powershell
uv run --extra dev pytest
```
