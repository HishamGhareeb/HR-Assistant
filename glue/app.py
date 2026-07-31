"""HTTP entry point for delivery channels and future customer integrations."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from .claude_client import ClaudeClient, Suggestion
from .config import Config
from .llm_guard_scan import OutputScanner
from .onyx_client import OnyxClient
from .openfga_client import OpenFgaFilter
from .pipeline import Pipeline
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
    )


def create_app(pipeline: Pipeline | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Readiness must remain observable even before deployment secrets are
        # injected. Construct the configured pipeline on the first real request.
        app.state.pipeline = pipeline
        yield

    app = FastAPI(
        title="HR Assistant API",
        version="0.1.0",
        description="Read-only, authorization-filtered HR answers and review suggestions.",
        lifespan=lifespan,
    )

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

    async def authenticated_user(
        x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    ) -> str:
        # Internal identity handoff only. A public gateway must verify a signed token.
        if not x_user_id or not x_user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authenticated user identity",
            )
        return x_user_id.strip()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/questions", response_model=QuestionResponse)
    async def ask_question(
        body: QuestionRequest,
        user_id: str = Depends(authenticated_user),
        active_pipeline: Pipeline = Depends(get_pipeline),
    ) -> QuestionResponse:
        result = await active_pipeline.handle_question(user_id, body.question)
        return QuestionResponse(
            answer=result.answer,
            suggestions=[SuggestionResponse.from_domain(s) for s in result.suggestions],
            blocked=result.blocked,
        )

    return app


app = create_app()
