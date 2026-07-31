"""HTTP entry point for delivery channels and future customer integrations."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from .audit import AuditLogger, HashChainedJsonlAuditSink
from .auth import TokenVerifier, build_identity_dependency, jwks_key_resolver, static_key_resolver
from .claude_client import ClaudeClient, Suggestion
from .config import Config
from .domain import Identity
from .llm_guard_scan import OutputScanner
from .observability import Metrics
from .onyx_client import OnyxClient
from .openfga_client import OpenFgaFilter
from .pipeline import Pipeline
from .resilience import bind_request_id
from .tracer import Tracer


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)


class SuggestionResponse(BaseModel):
    category: str
    reasoning: str
    record_reference: str | None

    @classmethod
    def from_domain(cls, suggestion: Suggestion) -> "SuggestionResponse":
        return cls(
            category=suggestion.category,
            reasoning=suggestion.reasoning,
            record_reference=suggestion.record_reference,
        )


class QuestionResponse(BaseModel):
    answer: str
    suggestions: list[SuggestionResponse]
    blocked: bool


def build_pipeline(config: Config) -> Pipeline:
    return Pipeline(
        onyx=OnyxClient(config.onyx_api_url, config.onyx_api_key),
        openfga=OpenFgaFilter(
            config.openfga_api_url,
            config.openfga_store_id,
            config.openfga_model_id,
        ),
        claude=ClaudeClient(config.anthropic_api_key, config.claude_model),
        guard=OutputScanner(),
        tracer=Tracer(
            config.langfuse_public_key,
            config.langfuse_secret_key,
            config.langfuse_host,
        ),
        audit_logger=AuditLogger(
            HashChainedJsonlAuditSink(Path(config.audit_log_path)),
            privacy_key=config.audit_privacy_key,
        ),
        metrics=Metrics(),
    )


def build_token_verifier(config: Config) -> TokenVerifier:
    if config.auth_jwks_url:
        key_resolver = jwks_key_resolver(config.auth_jwks_url)
    elif config.auth_static_keys_json:
        try:
            keys = json.loads(config.auth_static_keys_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"AUTH_STATIC_KEYS_JSON is not valid JSON: {exc}") from exc
        key_resolver = static_key_resolver(keys)
    else:
        raise RuntimeError("either AUTH_JWKS_URL or AUTH_STATIC_KEYS_JSON must be set")
    return TokenVerifier(key_resolver=key_resolver, issuer=config.auth_issuer, audience=config.auth_audience)


def create_app(pipeline: Pipeline | None = None, verifier: TokenVerifier | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Readiness must remain observable even before deployment secrets are
        # injected. Construct the configured pipeline/verifier on first use.
        app.state.pipeline = pipeline
        app.state.verifier = verifier
        app.state.identity_dependency = build_identity_dependency(verifier) if verifier is not None else None
        yield

    app = FastAPI(
        title="HR Assistant API",
        version="0.1.0",
        description="Read-only, authorization-filtered HR answers and review suggestions.",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def bind_request_id_middleware(request: Request, call_next):
        # Reuse a caller-supplied request ID for correlation across
        # services when present; otherwise generate one. Either way it's
        # bound to this task's contextvar before anything downstream
        # (pipeline, audit, resilience errors) runs, and echoed back so a
        # caller can correlate their own logs against ours.
        request_id = bind_request_id(request.headers.get("X-Request-ID"))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    def get_pipeline(request: Request) -> Pipeline:
        active_pipeline = request.app.state.pipeline
        if active_pipeline is not None:
            return active_pipeline
        try:
            active_pipeline = build_pipeline(Config())
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"HR Assistant is not configured: {exc}",
            ) from exc
        request.app.state.pipeline = active_pipeline
        return active_pipeline

    def get_identity_dependency(request: Request):
        """Lazily build (once) and cache the identity dependency from
        glue.auth, bound to a lazily-constructed TokenVerifier -- mirrors
        get_pipeline's fail-fast-but-lazy config pattern above, and keeps
        the actual header parsing / 401 logic in glue.auth rather than
        duplicated here."""
        cached = request.app.state.identity_dependency
        if cached is not None:
            return cached
        try:
            active_verifier = build_token_verifier(Config())
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"HR Assistant is not configured: {exc}",
            ) from exc
        request.app.state.verifier = active_verifier
        dependency = build_identity_dependency(active_verifier)
        request.app.state.identity_dependency = dependency
        return dependency

    async def get_identity(request: Request) -> Identity:
        dependency = get_identity_dependency(request)
        return await dependency(authorization=request.headers.get("Authorization"))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics(active_pipeline: Pipeline = Depends(get_pipeline)) -> Response:
        body, content_type = active_pipeline.metrics.render()
        return Response(content=body, media_type=content_type)

    @app.post("/v1/questions", response_model=QuestionResponse)
    async def ask_question(
        body: QuestionRequest,
        identity: Identity = Depends(get_identity),
        active_pipeline: Pipeline = Depends(get_pipeline),
    ) -> QuestionResponse:
        result = await active_pipeline.handle_question(identity, body.question)
        return QuestionResponse(
            answer=result.answer,
            suggestions=[SuggestionResponse.from_domain(s) for s in result.suggestions],
            blocked=result.blocked,
        )

    return app


app = create_app()
