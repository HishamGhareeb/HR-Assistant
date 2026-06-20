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
- For Python deps (`glue/requirements*.txt`), create the venv on D: too, e.g. `python -m venv D:\hr-assistant-venv` then `D:\hr-assistant-venv\Scripts\Activate.ps1`, rather than `.venv` inside this repo on C:.

Frappe HR and Onyx each manage their own compose lifecycle in their own directories — follow the printed next steps to bring each one up.

## Repo layout

- `docker/` — compose files for services we own directly (OpenFGA now; Langfuse later)
- `external/` — git-ignored clones of Frappe HR / Onyx, created by setup scripts
- `glue/` — Python pipeline: Onyx retrieval -> OpenFGA filtering -> Claude -> LLM Guard -> Langfuse trace -> WhatsApp
- `openfga/` — authorization model and test tuples (Stage 2)
- `scripts/` — setup and data-seeding scripts
- `tests/promptfoo/` — automated adversarial test suite (Stage 8)
