# HR Assistant

Flag-and-suggest HR assistant: RAL HRMS (system of record) + Onyx (retrieval/chat) + OpenFGA (per-user authorization) + Claude (reasoning) + LLM Guard (output scanning) + Langfuse (tracing) + Promptfoo (adversarial regression) + WhatsApp delivery via `RAL HRMS/waba_integration`.

No autonomous writes anywhere in scope. The assistant answers questions and raises suggestions for HR to review; only a human ever takes a real action in RAL HRMS.

See `docs/` for the full build manifesto, adversarial test protocol, and DPA draft.

For the reproducible local authorization stack and CI checks, see
[`docs/LOCAL_DEVELOPMENT.md`](docs/LOCAL_DEVELOPMENT.md).

## Status

Stage 0 (foundation systems) — scaffolding in progress. Synthetic data only until the full adversarial-testing gate (Stage 9) is passed.

## Stage 0: local foundation

Requires Docker Desktop (WSL2 backend) running.

**C: is nearly full, so everything heavy is routed to D::**
- Right after installing Docker Desktop (before pulling any images), run `./scripts/move_docker_data_to_d.ps1` to relocate Docker's image/volume storage to `D:\docker-data`.
- `./scripts/stage0_setup.ps1` clones `RAL HRMS/hrms` and the Onyx installer into `D:\hr-assistant-external` (override with `-ExternalDir`) and starts OpenFGA via the root `compose.yaml`. All published local ports are loopback-only.
- For Python dependencies, `pyproject.toml` and `uv.lock` are the single
  reproducible source of truth. If space is tight, set `UV_PROJECT_ENVIRONMENT`
  to a directory on D: before running `uv sync`.

RAL HRMS and Onyx each manage their own compose lifecycle in their own directories — follow the printed next steps to bring each one up.

## Repo layout

- `docker/` — compose files for services we own directly (OpenFGA now; Langfuse later)
- `external/` — git-ignored clones of RAL HRMS / Onyx, created by setup scripts
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

The API exposes `GET /health`, `GET /metrics` (Prometheus exposition format),
and `POST /v1/questions`. The question endpoint requires a signed
`Authorization: Bearer <JWT>` (see `docs/AUTHENTICATION.md`) carrying
`tenant_id`/`sub` claims -- the old `X-User-ID` handoff header is no longer
accepted. `/health` starts and responds without service credentials so an
orchestrator can distinguish a live process from a configured one.
`/v1/questions` returns `503` until all required values in `.env.example`
are configured. See `docs/API_INTEGRATION.md` for how the pieces built
across HIS-12–HIS-18 are wired into this request path.
