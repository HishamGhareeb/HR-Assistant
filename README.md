# HR Assistant

Flag-and-suggest HR assistant: Frappe HR (system of record) + Onyx (retrieval/chat) + OpenFGA (per-user authorization) + Claude (reasoning) + LLM Guard (output scanning) + Langfuse (tracing) + Promptfoo (adversarial regression) + WhatsApp delivery via `frappe/waba_integration`.

No autonomous writes anywhere in scope. The assistant answers questions and raises suggestions for HR to review; only a human ever takes a real action in Frappe HR.

See `docs/` for the full build manifesto, adversarial test protocol, and DPA draft.

## Status

Stage 0 (foundation systems) — scaffolding in progress. Synthetic data only until the full adversarial-testing gate (Stage 9) is passed.

## Stage 0: local foundation

Requires Docker Desktop (WSL2 backend) running.

**C: is nearly full, so everything heavy is routed to D::**
- Right after installing Docker Desktop (before pulling any images), run `./scripts/move_docker_data_to_d.ps1` to relocate Docker's image/volume storage to `D:\docker-data`.
- `./scripts/stage0_setup.ps1` clones `frappe/hrms` and the Onyx installer into `D:\hr-assistant-external` (override with `-ExternalDir`) and starts OpenFGA via `docker/openfga/docker-compose.yml`.
- For Python dependencies, `pyproject.toml` and `uv.lock` are the single
  reproducible source of truth. If space is tight, set `UV_PROJECT_ENVIRONMENT`
  to a directory on D: before running `uv sync`.

Frappe HR and Onyx each manage their own compose lifecycle in their own directories — follow the printed next steps to bring each one up.

## Repo layout

- `docker/` — compose files for services we own directly (OpenFGA now; Langfuse later)
- `external/` — git-ignored clones of Frappe HR / Onyx, created by setup scripts
- `glue/` — Python pipeline: Onyx retrieval -> OpenFGA filtering -> Claude -> LLM Guard -> Langfuse trace -> WhatsApp
- `openfga/` — authorization model and test tuples (Stage 2)
- `scripts/` — setup and data-seeding scripts
- `tests/promptfoo/` — automated adversarial test suite (Stage 8)

## API development

The architecture and release gates are documented in `docs/ARCHITECTURE.md` and
`docs/PRODUCT_ROADMAP.md`.

Install the project with development dependencies, copy `.env.example` to `.env`,
and run:

```powershell
uv sync --extra dev
uv run uvicorn glue.app:app --reload
```

The first API slice exposes `GET /health` and `POST /v1/questions`. The question
endpoint currently accepts `X-User-ID` only as a trusted internal identity handoff;
a public deployment must put signed authentication in front of it. `/health`
starts and responds without service credentials so an orchestrator can distinguish
a live process from a configured one. `/v1/questions` returns `503` until all
required values in `.env.example` are configured.
