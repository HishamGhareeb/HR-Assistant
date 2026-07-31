# The HTTP entrypoint (glue.app:app) is supplied by HIS-11.  Keeping the
# container definition here lets the secure API be added without introducing
# a second application implementation or embedding credentials in an image.
FROM ghcr.io/astral-sh/uv:0.9.8 AS uv
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
# Install only locked runtime dependencies.  The source is copied separately so
# dependency layers remain reusable while the image uses only the locked
# project manifest.
RUN uv sync --locked --no-dev --no-install-project

COPY glue /app/glue

RUN useradd --system --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "glue.app:app", "--host", "0.0.0.0", "--port", "8000"]
