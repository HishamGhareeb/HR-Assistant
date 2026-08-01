"""HTTP entry point for delivery channels and future customer integrations."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from .admin_controls import (
    AdminAuthorizationError,
    AdminControlStore,
    AdminSyncNotConfiguredError,
    HrAdminAuthorizer,
    InMemoryAdminControlStore,
    StaticHrAdminAuthorizer,
    SyncRunSummary,
    SourceStatus,
    TenantRole,
    AccessRoleAssignment,
)
from .audit import AuditLogger, HashChainedJsonlAuditSink
from .auth import TokenVerifier, build_identity_dependency, jwks_key_resolver, static_key_resolver
from .claude_client import ClaudeClient
from .config import Config
from .domain import Identity, Suggestion, SuggestionStatus
from .frappe_sync import FrappeRecord, SyncEngine
from .llm_guard_scan import OutputScanner
from .observability import Metrics
from .onyx_client import OnyxClient
from .openfga_client import OpenFgaFilter
from .pipeline import Pipeline
from .resilience import bind_request_id
from .suggestions import (
    HrReviewAuthorizer,
    JsonlSuggestionStore,
    StaticHrReviewAuthorizer,
    StoredSuggestion,
    SuggestionAuthorizationError,
    SuggestionNotFoundError,
    SuggestionStore,
    SuggestionTransitionError,
)
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


class ReviewDecisionRequest(BaseModel):
    action: SuggestionStatus
    note: str | None = Field(default=None, max_length=2_000)


class ReviewDecisionResponse(BaseModel):
    decision_id: str
    action: SuggestionStatus
    decided_by: str
    decided_at: str
    note: str | None


class ReviewSuggestionResponse(BaseModel):
    suggestion_id: str
    tenant_id: str
    category: str
    reasoning: str
    record_reference: str | None
    status: SuggestionStatus
    created_at: str
    decided_at: str | None
    decided_by: str | None
    decision_history: list[ReviewDecisionResponse] = []

    @classmethod
    def from_stored(cls, stored: StoredSuggestion) -> "ReviewSuggestionResponse":
        suggestion = stored.suggestion
        return cls(
            suggestion_id=suggestion.suggestion_id,
            tenant_id=suggestion.tenant_id,
            category=suggestion.category,
            reasoning=suggestion.reasoning,
            record_reference=suggestion.record_reference,
            status=suggestion.status,
            created_at=suggestion.created_at.isoformat(),
            decided_at=suggestion.decided_at.isoformat() if suggestion.decided_at else None,
            decided_by=suggestion.decided_by,
            decision_history=[
                ReviewDecisionResponse(
                    decision_id=decision.decision_id,
                    action=decision.action,
                    decided_by=decision.decided_by,
                    decided_at=decision.decided_at.isoformat(),
                    note=decision.note,
                )
                for decision in stored.decision_history
            ],
        )


class AdminRecordFailureResponse(BaseModel):
    doctype: str
    name: str
    reason: str


class AdminSyncRunResponse(BaseModel):
    run_id: str
    tenant_id: str
    source_id: str
    action: str
    status: str
    created: int
    updated: int
    deleted: int
    unchanged: int
    failed: list[AdminRecordFailureResponse]
    started_at: str
    finished_at: str | None

    @classmethod
    def from_summary(cls, summary: SyncRunSummary) -> "AdminSyncRunResponse":
        return cls(
            run_id=summary.run_id,
            tenant_id=summary.tenant_id,
            source_id=summary.source_id,
            action=summary.action,
            status=summary.status,
            created=summary.created,
            updated=summary.updated,
            deleted=summary.deleted,
            unchanged=summary.unchanged,
            failed=[
                AdminRecordFailureResponse(doctype=f.doctype, name=f.name, reason=f.reason)
                for f in summary.failed
            ],
            started_at=summary.started_at.isoformat(),
            finished_at=summary.finished_at.isoformat() if summary.finished_at else None,
        )


class AdminSourceStatusResponse(BaseModel):
    tenant_id: str
    source_id: str
    last_action: str
    last_status: str
    last_run_id: str
    updated_at: str

    @classmethod
    def from_status(cls, source: SourceStatus) -> "AdminSourceStatusResponse":
        return cls(
            tenant_id=source.tenant_id,
            source_id=source.source_id,
            last_action=source.last_action,
            last_status=source.last_status,
            last_run_id=source.last_run_id,
            updated_at=source.updated_at.isoformat(),
        )


class AdminFrappeRecordRequest(BaseModel):
    doctype: str = Field(min_length=1)
    name: str = Field(min_length=1)
    fields: dict = Field(default_factory=dict)
    deleted: bool = False


class AdminResyncRequest(BaseModel):
    source_id: str = Field(default="synthetic", min_length=1)
    records: list[AdminFrappeRecordRequest]


class AdminRevokeRequest(BaseModel):
    source_id: str = Field(default="synthetic", min_length=1)
    doctype: str = Field(min_length=1)
    name: str = Field(min_length=1)


class AdminRoleAssignmentRequest(BaseModel):
    roles: list[TenantRole]


class AdminRoleAssignmentResponse(BaseModel):
    tenant_id: str
    user_id: str
    roles: list[TenantRole]
    updated_by: str
    updated_at: str

    @classmethod
    def from_assignment(cls, assignment: AccessRoleAssignment) -> "AdminRoleAssignmentResponse":
        return cls(
            tenant_id=assignment.tenant_id,
            user_id=assignment.user_id,
            roles=list(assignment.roles),
            updated_by=assignment.updated_by,
            updated_at=assignment.updated_at.isoformat(),
        )


def build_pipeline(config: Config, suggestion_store: SuggestionStore | None = None) -> Pipeline:
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
        suggestion_store=suggestion_store,
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


def build_review_authorizer(config: Config) -> HrReviewAuthorizer:
    try:
        reviewers = json.loads(config.hr_reviewers_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"HR_REVIEWERS_JSON is not valid JSON: {exc}") from exc
    if not isinstance(reviewers, dict):
        raise RuntimeError("HR_REVIEWERS_JSON must be a JSON object keyed by tenant_id")
    return StaticHrReviewAuthorizer(reviewers)


def build_admin_authorizer(config: Config) -> HrAdminAuthorizer:
    try:
        admins = json.loads(config.hr_admins_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"HR_ADMINS_JSON is not valid JSON: {exc}") from exc
    if not isinstance(admins, dict):
        raise RuntimeError("HR_ADMINS_JSON must be a JSON object keyed by tenant_id")
    return StaticHrAdminAuthorizer(admins)


def create_app(
    pipeline: Pipeline | None = None,
    verifier: TokenVerifier | None = None,
    suggestion_store: SuggestionStore | None = None,
    review_authorizer: HrReviewAuthorizer | None = None,
    admin_store: AdminControlStore | None = None,
    admin_authorizer: HrAdminAuthorizer | None = None,
    sync_engine: SyncEngine | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Readiness must remain observable even before deployment secrets are
        # injected. Construct the configured pipeline/verifier on first use.
        app.state.pipeline = pipeline
        app.state.verifier = verifier
        app.state.identity_dependency = build_identity_dependency(verifier) if verifier is not None else None
        app.state.suggestion_store = suggestion_store
        app.state.review_authorizer = review_authorizer
        app.state.admin_store = admin_store
        app.state.admin_authorizer = admin_authorizer
        app.state.sync_engine = sync_engine
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
            config = Config()
            active_pipeline = build_pipeline(config, suggestion_store=_get_or_build_suggestion_store(request, config))
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"HR Assistant is not configured: {exc}",
            ) from exc
        request.app.state.pipeline = active_pipeline
        return active_pipeline

    def _get_or_build_suggestion_store(request: Request, config: Config) -> SuggestionStore:
        active_store = request.app.state.suggestion_store
        if active_store is not None:
            return active_store
        active_store = JsonlSuggestionStore(Path(config.suggestion_store_path))
        request.app.state.suggestion_store = active_store
        return active_store

    def get_suggestion_store(request: Request) -> SuggestionStore:
        active_store = request.app.state.suggestion_store
        if active_store is not None:
            return active_store
        try:
            return _get_or_build_suggestion_store(request, Config())
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"HR Assistant is not configured: {exc}",
            ) from exc

    def get_review_authorizer(request: Request) -> HrReviewAuthorizer:
        active_authorizer = request.app.state.review_authorizer
        if active_authorizer is not None:
            return active_authorizer
        try:
            active_authorizer = build_review_authorizer(Config())
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"HR Assistant is not configured: {exc}",
            ) from exc
        request.app.state.review_authorizer = active_authorizer
        return active_authorizer

    def get_admin_store(request: Request) -> AdminControlStore:
        active_store = request.app.state.admin_store
        if active_store is not None:
            return active_store
        active_store = InMemoryAdminControlStore()
        request.app.state.admin_store = active_store
        return active_store

    def get_admin_authorizer(request: Request) -> HrAdminAuthorizer:
        active_authorizer = request.app.state.admin_authorizer
        if active_authorizer is not None:
            return active_authorizer
        try:
            active_authorizer = build_admin_authorizer(Config())
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"HR Assistant is not configured: {exc}",
            ) from exc
        request.app.state.admin_authorizer = active_authorizer
        return active_authorizer

    def get_sync_engine(request: Request) -> SyncEngine:
        active_engine = request.app.state.sync_engine
        if active_engine is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="HR Assistant ingestion sync is not configured",
            )
        return active_engine

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

    def authorize_hr_review(identity: Identity, authorizer: HrReviewAuthorizer) -> None:
        try:
            authorizer.authorize(identity)
        except SuggestionAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to review suggestions") from exc

    def authorize_hr_admin(identity: Identity, authorizer: HrAdminAuthorizer) -> None:
        try:
            authorizer.authorize(identity)
        except AdminAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for HR admin controls") from exc

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

    @app.get("/v1/hr/suggestions", response_model=list[ReviewSuggestionResponse])
    async def list_suggestions(
        status_filter: SuggestionStatus | None = None,
        identity: Identity = Depends(get_identity),
        store: SuggestionStore = Depends(get_suggestion_store),
        authorizer: HrReviewAuthorizer = Depends(get_review_authorizer),
    ) -> list[ReviewSuggestionResponse]:
        authorize_hr_review(identity, authorizer)
        return [
            ReviewSuggestionResponse.from_stored(stored)
            for stored in store.list(tenant_id=identity.tenant_id, status=status_filter)
        ]

    @app.get("/v1/hr/suggestions/{suggestion_id}", response_model=ReviewSuggestionResponse)
    async def get_suggestion(
        suggestion_id: str,
        identity: Identity = Depends(get_identity),
        store: SuggestionStore = Depends(get_suggestion_store),
        authorizer: HrReviewAuthorizer = Depends(get_review_authorizer),
    ) -> ReviewSuggestionResponse:
        authorize_hr_review(identity, authorizer)
        try:
            return ReviewSuggestionResponse.from_stored(store.get(tenant_id=identity.tenant_id, suggestion_id=suggestion_id))
        except SuggestionNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found") from exc

    @app.post("/v1/hr/suggestions/{suggestion_id}/decision", response_model=ReviewSuggestionResponse)
    async def decide_suggestion(
        suggestion_id: str,
        body: ReviewDecisionRequest,
        identity: Identity = Depends(get_identity),
        store: SuggestionStore = Depends(get_suggestion_store),
        authorizer: HrReviewAuthorizer = Depends(get_review_authorizer),
    ) -> ReviewSuggestionResponse:
        authorize_hr_review(identity, authorizer)
        try:
            stored = store.decide(
                identity=identity,
                suggestion_id=suggestion_id,
                action=body.action,
                note=body.note,
            )
        except SuggestionNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found") from exc
        except SuggestionTransitionError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return ReviewSuggestionResponse.from_stored(stored)

    @app.get("/v1/hr/admin/sources", response_model=list[AdminSourceStatusResponse])
    async def list_admin_sources(
        identity: Identity = Depends(get_identity),
        store: AdminControlStore = Depends(get_admin_store),
        authorizer: HrAdminAuthorizer = Depends(get_admin_authorizer),
    ) -> list[AdminSourceStatusResponse]:
        authorize_hr_admin(identity, authorizer)
        return [AdminSourceStatusResponse.from_status(source) for source in store.list_sources(identity.tenant_id)]

    @app.get("/v1/hr/admin/sync/runs", response_model=list[AdminSyncRunResponse])
    async def list_admin_sync_runs(
        identity: Identity = Depends(get_identity),
        store: AdminControlStore = Depends(get_admin_store),
        authorizer: HrAdminAuthorizer = Depends(get_admin_authorizer),
    ) -> list[AdminSyncRunResponse]:
        authorize_hr_admin(identity, authorizer)
        return [AdminSyncRunResponse.from_summary(run) for run in store.list_runs(identity.tenant_id)]

    @app.post("/v1/hr/admin/sync/resync", response_model=AdminSyncRunResponse)
    async def synthetic_admin_resync(
        body: AdminResyncRequest,
        identity: Identity = Depends(get_identity),
        store: AdminControlStore = Depends(get_admin_store),
        authorizer: HrAdminAuthorizer = Depends(get_admin_authorizer),
        engine: SyncEngine = Depends(get_sync_engine),
    ) -> AdminSyncRunResponse:
        authorize_hr_admin(identity, authorizer)
        records = [
            FrappeRecord(
                doctype=record.doctype,
                name=record.name,
                tenant_id=identity.tenant_id,
                fields=dict(record.fields),
                deleted=record.deleted,
            )
            for record in body.records
        ]
        summary = await store.synthetic_resync(
            identity=identity,
            source_id=body.source_id,
            records=records,
            sync_engine=engine,
        )
        return AdminSyncRunResponse.from_summary(summary)

    @app.post("/v1/hr/admin/sync/revoke", response_model=AdminSyncRunResponse)
    async def synthetic_admin_revoke(
        body: AdminRevokeRequest,
        identity: Identity = Depends(get_identity),
        store: AdminControlStore = Depends(get_admin_store),
        authorizer: HrAdminAuthorizer = Depends(get_admin_authorizer),
        engine: SyncEngine = Depends(get_sync_engine),
    ) -> AdminSyncRunResponse:
        authorize_hr_admin(identity, authorizer)
        summary = await store.synthetic_revoke(
            identity=identity,
            source_id=body.source_id,
            doctype=body.doctype,
            name=body.name,
            sync_engine=engine,
        )
        return AdminSyncRunResponse.from_summary(summary)

    @app.get("/v1/hr/admin/access/roles", response_model=list[AdminRoleAssignmentResponse])
    async def list_admin_role_assignments(
        identity: Identity = Depends(get_identity),
        store: AdminControlStore = Depends(get_admin_store),
        authorizer: HrAdminAuthorizer = Depends(get_admin_authorizer),
    ) -> list[AdminRoleAssignmentResponse]:
        authorize_hr_admin(identity, authorizer)
        return [
            AdminRoleAssignmentResponse.from_assignment(assignment)
            for assignment in store.list_role_assignments(identity.tenant_id)
        ]

    @app.put("/v1/hr/admin/access/roles/{user_id}", response_model=AdminRoleAssignmentResponse)
    async def set_admin_role_assignment(
        user_id: str,
        body: AdminRoleAssignmentRequest,
        identity: Identity = Depends(get_identity),
        store: AdminControlStore = Depends(get_admin_store),
        authorizer: HrAdminAuthorizer = Depends(get_admin_authorizer),
    ) -> AdminRoleAssignmentResponse:
        authorize_hr_admin(identity, authorizer)
        assignment = store.set_role_assignment(
            identity=identity,
            user_id=user_id,
            roles=tuple(body.roles),
        )
        return AdminRoleAssignmentResponse.from_assignment(assignment)

    return app


app = create_app()
