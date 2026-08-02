"""Answer feedback, unanswered-question tracking, HR escalation, and
tenant-scoped quality analytics (HIS-23).

Mirrors ``glue.suggestions``'s store shape (Protocol + in-memory +
append-only JSONL implementations, tenant-scoped static authorizer) rather
than inventing a new persistence pattern. Two kinds of record live here:

- ``AnswerFeedback``: an employee's helpful/not-helpful rating of one
  answer, correlated to that answer via the pipeline's own
  ``request_id`` (already generated and echoed per-request by
  ``glue.resilience.bind_request_id`` -- reused here rather than minting a
  second identifier for the same interaction). Not-helpful feedback is
  escalated to HR automatically on submission; HR can resolve it.
- ``UnansweredQuestion``: recorded automatically by ``glue.pipeline.Pipeline``
  whenever a question does not reach ``model_outcome == "answered"``
  (no_info / blocked / error), so HR sees uncovered topics even when no
  employee bothers to leave feedback.

The quality-analytics summary is deliberately aggregate-only (counts and
rates, no question/answer text) so it can be shown on an HR dashboard
without exposing the sensitive content of individual interactions -- the
list endpoints, which do carry that text, are analogous to the review
inbox and are gated by the same kind of tenant-scoped HR authorization.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from .domain import CrossTenantError, Identity


class FeedbackReasonCode(str, Enum):
    """Reason codes for not-helpful feedback. Required exactly when
    ``helpful`` is False -- see ``AnswerFeedback``'s validator."""

    INCORRECT = "incorrect"
    INCOMPLETE = "incomplete"
    IRRELEVANT = "irrelevant"
    OUTDATED = "outdated"
    OTHER = "other"


class FeedbackNotFoundError(KeyError):
    pass


class FeedbackTransitionError(ValueError):
    pass


class FeedbackAuthorizationError(PermissionError):
    pass


class HrFeedbackAuthorizer(Protocol):
    def authorize(self, identity: Identity) -> None: ...


class StaticHrFeedbackAuthorizer:
    """Tenant-scoped static reviewer map, same shape as
    ``glue.suggestions.StaticHrReviewAuthorizer`` -- kept as a separate
    class (rather than reusing that one directly) so the feedback/quality
    surface can be granted to a different reviewer set than the suggestion
    inbox without coupling the two authorization decisions."""

    def __init__(self, reviewers_by_tenant: dict[str, set[str] | list[str] | tuple[str, ...]]) -> None:
        self._reviewers_by_tenant = {
            tenant.strip(): {user.strip() for user in users if user.strip()}
            for tenant, users in reviewers_by_tenant.items()
            if tenant.strip()
        }

    def authorize(self, identity: Identity) -> None:
        if identity.user_id not in self._reviewers_by_tenant.get(identity.tenant_id, set()):
            raise FeedbackAuthorizationError("caller is not authorized to review answer feedback")


def _clean(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


class FeedbackResolution(BaseModel):
    model_config = {"frozen": True}

    resolved_by: str = Field(min_length=1)
    resolved_at: datetime
    note: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def _validated(self) -> "FeedbackResolution":
        if self.resolved_at.tzinfo is None:
            raise ValueError("resolved_at must be timezone-aware")
        return self


class AnswerFeedback(BaseModel):
    """One employee's rating of one answer.

    ``request_id`` correlates this record back to the pipeline call that
    produced the answer -- the same ID already bound per-request by
    ``glue.resilience.bind_request_id`` and echoed in the
    ``X-Request-ID`` response header / ``QuestionResponse.request_id``.
    """

    model_config = {"frozen": True}

    feedback_id: str = Field(default_factory=lambda: uuid4().hex, min_length=1)
    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    helpful: bool
    reason_code: FeedbackReasonCode | None = None
    note: str | None = Field(default=None, max_length=2_000)
    escalated: bool = False
    resolved: bool = False
    resolution: FeedbackResolution | None = None
    created_at: datetime

    @model_validator(mode="after")
    def _validated(self) -> "AnswerFeedback":
        object.__setattr__(self, "tenant_id", _clean(self.tenant_id))
        object.__setattr__(self, "user_id", _clean(self.user_id))
        object.__setattr__(self, "request_id", _clean(self.request_id))
        object.__setattr__(self, "question", _clean(self.question))
        object.__setattr__(self, "answer", _clean(self.answer))
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.helpful and self.reason_code is not None:
            raise ValueError("reason_code only applies to not-helpful feedback")
        if not self.helpful and self.reason_code is None:
            raise ValueError("not-helpful feedback requires a reason_code")
        if not self.helpful and not self.escalated:
            raise ValueError("not-helpful feedback must be escalated on creation")
        if self.helpful and self.escalated:
            raise ValueError("helpful feedback must not be escalated")
        if self.resolved and self.resolution is None:
            raise ValueError("resolved feedback requires a resolution record")
        if not self.resolved and self.resolution is not None:
            raise ValueError("unresolved feedback must not have a resolution record")
        if self.resolved and not self.escalated:
            raise ValueError("only escalated feedback can be resolved")
        return self

    @classmethod
    def submit(
        cls,
        *,
        identity: Identity,
        request_id: str,
        question: str,
        answer: str,
        helpful: bool,
        reason_code: FeedbackReasonCode | None = None,
        note: str | None = None,
        created_at: datetime | None = None,
    ) -> "AnswerFeedback":
        return cls(
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            request_id=request_id,
            question=question,
            answer=answer,
            helpful=helpful,
            reason_code=reason_code,
            note=note.strip() if note and note.strip() else None,
            escalated=not helpful,
            created_at=created_at or datetime.now(timezone.utc),
        )


class UnansweredQuestion(BaseModel):
    """Recorded automatically by the pipeline whenever a question does not
    reach ``model_outcome == "answered"``. No employee action required --
    this is how HR sees uncovered topics that nobody bothered to rate."""

    model_config = {"frozen": True}

    record_id: str = Field(default_factory=lambda: uuid4().hex, min_length=1)
    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    model_outcome: str = Field(min_length=1)
    created_at: datetime

    @model_validator(mode="after")
    def _validated(self) -> "UnansweredQuestion":
        object.__setattr__(self, "tenant_id", _clean(self.tenant_id))
        object.__setattr__(self, "user_id", _clean(self.user_id))
        object.__setattr__(self, "request_id", _clean(self.request_id))
        object.__setattr__(self, "question", _clean(self.question))
        object.__setattr__(self, "model_outcome", _clean(self.model_outcome))
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self


class QualityAnalyticsSummary(BaseModel):
    """Aggregate-only dashboard payload -- no question/answer text, so this
    is safe to show without the HR-reviewer authorization the list
    endpoints require."""

    model_config = {"frozen": True}

    tenant_id: str
    total_feedback: int
    helpful_count: int
    not_helpful_count: int
    helpful_rate: float | None
    reason_code_counts: dict[str, int]
    unresolved_escalation_count: int
    unanswered_count: int


def _require_same_tenant(*, tenant_id: str, item_tenant_id: str, item_type: str) -> None:
    if item_tenant_id != tenant_id:
        raise CrossTenantError(f"expected tenant {tenant_id!r}, got {item_tenant_id!r} from {item_type}")


class FeedbackStore(Protocol):
    def record_feedback(self, feedback: AnswerFeedback) -> AnswerFeedback: ...

    def record_unanswered(self, entry: UnansweredQuestion) -> UnansweredQuestion: ...

    def list_feedback(
        self, *, tenant_id: str, helpful: bool | None = None, escalated_only: bool = False
    ) -> list[AnswerFeedback]: ...

    def list_unanswered(self, *, tenant_id: str) -> list[UnansweredQuestion]: ...

    def get_feedback(self, *, tenant_id: str, feedback_id: str) -> AnswerFeedback: ...

    def resolve(
        self,
        *,
        identity: Identity,
        feedback_id: str,
        note: str | None = None,
        resolved_at: datetime | None = None,
    ) -> AnswerFeedback: ...

    def quality_summary(self, *, tenant_id: str) -> QualityAnalyticsSummary: ...


class InMemoryFeedbackStore:
    def __init__(self) -> None:
        self._feedback: dict[tuple[str, str], AnswerFeedback] = {}
        self._unanswered: list[UnansweredQuestion] = []
        self._lock = threading.Lock()

    @staticmethod
    def _key(tenant_id: str, feedback_id: str) -> tuple[str, str]:
        return (tenant_id, feedback_id)

    def record_feedback(self, feedback: AnswerFeedback) -> AnswerFeedback:
        key = self._key(feedback.tenant_id, feedback.feedback_id)
        with self._lock:
            if key not in self._feedback:
                self._feedback[key] = feedback
            return self._feedback[key]

    def record_unanswered(self, entry: UnansweredQuestion) -> UnansweredQuestion:
        with self._lock:
            self._unanswered.append(entry)
        return entry

    def list_feedback(
        self, *, tenant_id: str, helpful: bool | None = None, escalated_only: bool = False
    ) -> list[AnswerFeedback]:
        with self._lock:
            records = [
                record
                for record in self._feedback.values()
                if record.tenant_id == tenant_id
                and (helpful is None or record.helpful == helpful)
                and (not escalated_only or record.escalated)
            ]
        return sorted(records, key=lambda record: record.created_at, reverse=True)

    def list_unanswered(self, *, tenant_id: str) -> list[UnansweredQuestion]:
        with self._lock:
            records = [entry for entry in self._unanswered if entry.tenant_id == tenant_id]
        return sorted(records, key=lambda entry: entry.created_at, reverse=True)

    def get_feedback(self, *, tenant_id: str, feedback_id: str) -> AnswerFeedback:
        with self._lock:
            record = self._feedback.get(self._key(tenant_id, feedback_id))
        if record is None or record.tenant_id != tenant_id:
            raise FeedbackNotFoundError(feedback_id)
        return record

    def resolve(
        self,
        *,
        identity: Identity,
        feedback_id: str,
        note: str | None = None,
        resolved_at: datetime | None = None,
    ) -> AnswerFeedback:
        with self._lock:
            key = self._key(identity.tenant_id, feedback_id)
            record = self._feedback.get(key)
            if record is None or record.tenant_id != identity.tenant_id:
                raise FeedbackNotFoundError(feedback_id)
            _require_same_tenant(
                tenant_id=identity.tenant_id, item_tenant_id=record.tenant_id, item_type="AnswerFeedback"
            )
            if not record.escalated:
                raise FeedbackTransitionError(
                    f"feedback {feedback_id!r} was not escalated; only escalated feedback can be resolved"
                )
            if record.resolved:
                if record.resolution is not None and record.resolution.resolved_by == identity.user_id:
                    return record
                raise FeedbackTransitionError(f"feedback {feedback_id!r} is already resolved")

            timestamp = resolved_at or datetime.now(timezone.utc)
            resolution = FeedbackResolution(
                resolved_by=identity.user_id,
                resolved_at=timestamp,
                note=note.strip() if note and note.strip() else None,
            )
            updated = record.model_copy(update={"resolved": True, "resolution": resolution})
            self._feedback[key] = updated
            return updated

    def quality_summary(self, *, tenant_id: str) -> QualityAnalyticsSummary:
        feedback = self.list_feedback(tenant_id=tenant_id)
        unanswered = self.list_unanswered(tenant_id=tenant_id)

        helpful_count = sum(1 for record in feedback if record.helpful)
        not_helpful_count = len(feedback) - helpful_count
        reason_code_counts: dict[str, int] = {}
        for record in feedback:
            if record.reason_code is not None:
                reason_code_counts[record.reason_code.value] = (
                    reason_code_counts.get(record.reason_code.value, 0) + 1
                )
        unresolved_escalations = sum(1 for record in feedback if record.escalated and not record.resolved)

        return QualityAnalyticsSummary(
            tenant_id=tenant_id,
            total_feedback=len(feedback),
            helpful_count=helpful_count,
            not_helpful_count=not_helpful_count,
            helpful_rate=(helpful_count / len(feedback)) if feedback else None,
            reason_code_counts=reason_code_counts,
            unresolved_escalation_count=unresolved_escalations,
            unanswered_count=len(unanswered),
        )


class JsonlFeedbackStore(InMemoryFeedbackStore):
    """Append-only JSONL-backed store, same durability model as
    ``glue.suggestions.JsonlSuggestionStore``: the in-memory index is
    rebuilt from append-only events on startup."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__()
        self._load()

    def record_feedback(self, feedback: AnswerFeedback) -> AnswerFeedback:
        is_new = self._key(feedback.tenant_id, feedback.feedback_id) not in self._feedback
        created = super().record_feedback(feedback)
        if is_new:
            self._append({"type": "feedback_created", "feedback": feedback.model_dump(mode="json")})
        return created

    def record_unanswered(self, entry: UnansweredQuestion) -> UnansweredQuestion:
        recorded = super().record_unanswered(entry)
        self._append({"type": "unanswered_recorded", "entry": entry.model_dump(mode="json")})
        return recorded

    def resolve(
        self,
        *,
        identity: Identity,
        feedback_id: str,
        note: str | None = None,
        resolved_at: datetime | None = None,
    ) -> AnswerFeedback:
        before = self.get_feedback(tenant_id=identity.tenant_id, feedback_id=feedback_id)
        resolved = super().resolve(
            identity=identity, feedback_id=feedback_id, note=note, resolved_at=resolved_at
        )
        if not before.resolved and resolved.resolved:
            self._append({"type": "feedback_resolved", "feedback": resolved.model_dump(mode="json")})
        return resolved

    def _append(self, event: dict) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

    def _load(self) -> None:
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                event = json.loads(line)
                if event["type"] == "feedback_created":
                    InMemoryFeedbackStore.record_feedback(
                        self, AnswerFeedback.model_validate(event["feedback"])
                    )
                elif event["type"] == "unanswered_recorded":
                    InMemoryFeedbackStore.record_unanswered(
                        self, UnansweredQuestion.model_validate(event["entry"])
                    )
                elif event["type"] == "feedback_resolved":
                    resolved = AnswerFeedback.model_validate(event["feedback"])
                    identity = Identity(tenant_id=resolved.tenant_id, user_id=resolved.resolution.resolved_by)
                    InMemoryFeedbackStore.resolve(
                        self,
                        identity=identity,
                        feedback_id=resolved.feedback_id,
                        note=resolved.resolution.note,
                        resolved_at=resolved.resolution.resolved_at,
                    )
