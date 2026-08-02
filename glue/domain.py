"""Typed domain contracts shared across the API, retrieval, authorization,
audit, and UI boundaries.

Every contract that can cross one of those boundaries carries an explicit
``tenant_id``. There is no tenant-less state: the authorization model in
``openfga/model.fga`` scopes every relation by data ownership, and a request
or document that can't say which tenant it belongs to can't be safely
authorized, cited, or audited. `require_same_tenant` is the enforcement
point every boundary should call before mixing caller identity with
retrieved or stored data.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _clean(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


class Identity(BaseModel):
    """An authenticated caller, scoped to exactly one tenant.

    This is the contract the API's identity dependency must produce before
    any downstream stage (retrieval, authorization, the model call, audit)
    runs -- see the trust-boundary notes in ``docs/ARCHITECTURE.md``.
    """

    model_config = {"frozen": True}

    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _normalized(self) -> "Identity":
        object.__setattr__(self, "tenant_id", _clean(self.tenant_id))
        object.__setattr__(self, "user_id", _clean(self.user_id))
        return self


class DocumentType(str, Enum):
    """Record types recognized by the OpenFGA model in ``openfga/model.fga``.
    Keep this enum and that file in sync -- an object type that exists in
    one but not the other is a silent authorization gap."""

    EMPLOYEE_RECORD = "employee_record"
    LEAVE_RECORD = "leave_record"
    PERFORMANCE_RECORD = "performance_record"
    SALARY_RECORD = "salary_record"
    POLICY_DOCUMENT = "policy_document"


class DocumentClassification(str, Enum):
    """Tenant-scoped retrieval clearance used before vector search.

    `PUBLIC` means public inside the authenticated tenant only. It never
    means visible across customer tenants.
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    MANAGER_ONLY = "manager_only"
    HR_ONLY = "hr_only"
    SYSTEM_CONFIDENTIAL = "system_confidential"


class Citation(BaseModel):
    """Stable pointer back to the exact source a piece of retrieved text
    came from: enough to show an employee where an answer originated, to
    re-fetch the record later, and to authorize and audit the access."""

    model_config = {"frozen": True}

    source: str = Field(min_length=1, description="Origin system, e.g. 'frappe_hr' or 'onyx'")
    object_type: DocumentType
    object_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    retrieved_at: datetime

    @model_validator(mode="after")
    def _validated(self) -> "Citation":
        object.__setattr__(self, "source", _clean(self.source))
        object.__setattr__(self, "object_id", _clean(self.object_id))
        object.__setattr__(self, "tenant_id", _clean(self.tenant_id))
        if self.retrieved_at.tzinfo is None:
            raise ValueError("retrieved_at must be timezone-aware")
        return self


class Document(BaseModel):
    """A retrieved chunk plus the stable metadata needed to authorize,
    cite, and audit it. Every retrieval adapter (Onyx today, anything
    else later) must normalize into this shape before the pipeline sees
    it -- nothing downstream should have to know adapter-specific fields."""

    model_config = {"frozen": True}

    citation: Citation
    chunk: str = Field(min_length=1)
    classification: DocumentClassification = DocumentClassification.INTERNAL

    @property
    def tenant_id(self) -> str:
        return self.citation.tenant_id

    @property
    def object_type(self) -> DocumentType:
        return self.citation.object_type

    @property
    def object_id(self) -> str:
        return self.citation.object_id


class SuggestionStatus(str, Enum):
    """Explicit review lifecycle. A suggestion is never auto-applied -- per
    the read-only trust boundary in ``docs/ARCHITECTURE.md`` it always
    waits for a human HR decision before it can be treated as approved or
    rejected."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISMISSED = "dismissed"


_DECIDED_STATUSES = {SuggestionStatus.APPROVED, SuggestionStatus.REJECTED, SuggestionStatus.DISMISSED}


class Suggestion(BaseModel):
    """A reviewable HR action raised by the assistant. It never mutates
    Frappe directly; a status transition only happens through the human
    review workflow, and that transition must record who decided and
    when."""

    suggestion_id: str = Field(default_factory=lambda: uuid4().hex, min_length=1)
    tenant_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)
    record_reference: str | None = None
    status: SuggestionStatus = SuggestionStatus.PENDING
    created_at: datetime
    decided_at: datetime | None = None
    decided_by: str | None = None

    @model_validator(mode="after")
    def _validated(self) -> "Suggestion":
        object.__setattr__(self, "suggestion_id", _clean(self.suggestion_id))
        object.__setattr__(self, "tenant_id", _clean(self.tenant_id))
        object.__setattr__(self, "category", _clean(self.category))
        object.__setattr__(self, "reasoning", _clean(self.reasoning))
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.decided_at is not None and self.decided_at.tzinfo is None:
            raise ValueError("decided_at must be timezone-aware")

        decided = self.status in _DECIDED_STATUSES
        has_decision = self.decided_at is not None or self.decided_by is not None
        if decided and not (self.decided_at is not None and self.decided_by):
            raise ValueError(f"status {self.status.value!r} requires decided_at and decided_by")
        if not decided and has_decision:
            raise ValueError(f"status {self.status.value!r} must not have a recorded decision")
        return self


class CrossTenantError(ValueError):
    """Raised when data or an identity from one tenant would cross into
    another tenant's request/response boundary."""


def require_same_tenant(*items: Identity | Document | Citation | Suggestion, tenant_id: str) -> None:
    """Raise ``CrossTenantError`` if any item's ``tenant_id`` does not match
    the expected tenant. Call this at every boundary that mixes caller
    identity with retrieved or stored data (retrieval results, suggestions
    pulled for review, audit records) so a bug can never leak one tenant's
    data into another tenant's request."""
    expected = _clean(tenant_id)
    for item in items:
        if item.tenant_id != expected:
            raise CrossTenantError(
                f"expected tenant {expected!r}, got {item.tenant_id!r} from {type(item).__name__}"
            )
