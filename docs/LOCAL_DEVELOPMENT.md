# Local development

The default local stack starts only OpenFGA. It is intentionally isolated from Frappe HR, Onyx, and any production data. Use synthetic data until the adversarial-testing release gate is passed.

## Prerequisites

- Docker Desktop with the WSL2 backend running.
- Python 3.12 for the test suite.
- An untracked `.env` file only when starting the API profile. Never put API keys, employee records, or Frappe credentials in Compose files, GitHub Actions, or committed fixtures.

## Start authorization locally

From the repository root, run:

```powershell
docker compose up -d
```

This starts OpenFGA with the pinned `v1.8.12` image. Confirm it is ready:

```powershell
docker compose ps
```

The local-only playground is available at `http://localhost:3000`, and the HTTP API at `http://localhost:8080`. Compose binds every published port to `127.0.0.1`, so none are reachable from the local network.

Stop it with `docker compose down`. This removes containers but keeps no production data because the stack uses OpenFGA's in-memory datastore.

## Start the API profile

After HIS-11's FastAPI entrypoint is present, create `.env` from the documented environment variables and run:

```powershell
docker compose --profile api up --build
```

The API container runs as a non-root user, has a read-only filesystem, and receives only the environment variables supplied locally. Its OpenFGA endpoint is fixed to the internal Docker hostname; no authorization service is exposed to an external network by the application configuration.

## Run the same checks as CI

```powershell
uv sync --locked --extra dev
uv run python -m compileall -q glue tests
uv run pytest -q
docker compose config --quiet
docker build --tag hr-assistant-api:local .
```

CI also builds the API image and confirms its credential-free `/health` endpoint.
