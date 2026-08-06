"""Persistent suggestion review inbox and lifecycle decisions.

Suggestions are review records only. A human approval/rejection/dismissal
records an immutable decision in this store; it deliberately has no RAL HRMS
client and no HR-system write path.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from .domain import Identity, Suggestion, SuggestionStatus, require_same_tenant

DecisionAction = Literal[SuggestionStatus.APPROVED, SuggestionStatus.REJECTED, SuggestionStatus.DISMISSED]
_DECISION_STATUSES = {SuggestionStatus.APPROVED, SuggestionStatus.REJECTED, SuggestionStatus.DISMISSED}


class SuggestionNotFoundError(KeyError):
    pass


class SuggestionTransitionError(ValueError):
    pass


class SuggestionAuthorizationError(PermissionError):
    pass


class HrReviewAuthorizer(Protocol):
    def authorize(self, identity: Identity) -> None: ...


class StaticHrReviewAuthorizer:
    """Tenant-scoped static reviewer map for the API boundary.

    User IDs are only meaningful inside an authenticated tenant. The map is
    therefore keyed by tenant first, avoiding a global "hr admin" identity
    that could accidentally cross tenants.
    """

    def __init__(self, reviewers_by_tenant: dict[str, set[str] | list[str] | tuple[str, ...]]) -> None:
        self._reviewers_by_tenant = {
            tenant.strip(): {user.strip() for user in users if user.strip()}
            for tenant, users in reviewers_by_tenant.items()
            if tenant.strip()
        }

    def authorize(self, identity: Identity) -> None:
        if identity.user_id not in self._reviewers_by_tenant.get(identity.tenant_id, set()):
            raise SuggestionAuthorizationError("caller is not authorized to review HR suggestions")


class SuggestionDecision(BaseModel):
    model_config = {"frozen": True}

    decision_id: str = Field(default_factory=lambda: uuid4().hex, min_length=1)
    suggestion_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    action: SuggestionStatus
    decided_by: str = Field(min_length=1)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    note: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def _validated(self) -> "SuggestionDecision":
        if self.action not in _DECISION_STATUSES:
            raise ValueError("decision action must be approved, rejected, or dismissed")
        if self.decided_at.tzinfo is None:
            raise ValueError("decided_at must be timezone-aware")
        return self


class StoredSuggestion(BaseModel):
    model_config = {"frozen": True}

    suggestion: Suggestion
    decision_history: tuple[SuggestionDecision, ...] = ()


class SuggestionStore(Protocol):
    def create(self, suggestion: Suggestion) -> Suggestion: ...
    def list(self, *, tenant_id: str, status: SuggestionStatus | None = None) -> list[StoredSuggestion]: ...
    def get(self, *, tenant_id: str, suggestion_id: str) -> StoredSuggestion: ...
    def decide(
        self,
        *,
        identity: Identity,
        suggestion_id: str,
        action: SuggestionStatus,
        note: str | None = None,
        decided_at: datetime | None = None,
    ) -> StoredSuggestion: ...


class InMemorySuggestionStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], StoredSuggestion] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(tenant_id: str, suggestion_id: str) -> tuple[str, str]:
        return (tenant_id, suggestion_id)

    def create(self, suggestion: Suggestion) -> Suggestion:
        require_same_tenant(suggestion, tenant_id=suggestion.tenant_id)
        key = self._key(suggestion.tenant_id, suggestion.suggestion_id)
        with self._lock:
            if key not in self._records:
                self._records[key] = StoredSuggestion(suggestion=suggestion)
            return self._records[key].suggestion

    def list(self, *, tenant_id: str, status: SuggestionStatus | None = None) -> list[StoredSuggestion]:
        with self._lock:
            records = [
                record
                for record in self._records.values()
                if record.suggestion.tenant_id == tenant_id and (status is None or record.suggestion.status == status)
            ]
        return sorted(records, key=lambda record: record.suggestion.created_at, reverse=True)

    def get(self, *, tenant_id: str, suggestion_id: str) -> StoredSuggestion:
        with self._lock:
            record = self._records.get(self._key(tenant_id, suggestion_id))
        if record is None or record.suggestion.tenant_id != tenant_id:
            raise SuggestionNotFoundError(suggestion_id)
        return record

    def decide(
        self,
        *,
        identity: Identity,
        suggestion_id: str,
        action: SuggestionStatus,
        note: str | None = None,
        decided_at: datetime | None = None,
    ) -> StoredSuggestion:
        if action not in _DECISION_STATUSES:
            raise SuggestionTransitionError("suggestions can only be approved, rejected, or dismissed")

        with self._lock:
            key = self._key(identity.tenant_id, suggestion_id)
            record = self._records.get(key)
            if record is None or record.suggestion.tenant_id != identity.tenant_id:
                raise SuggestionNotFoundError(suggestion_id)
            require_same_tenant(identity, record.suggestion, tenant_id=identity.tenant_id)

            current = record.suggestion
            normalized_note = note.strip() if note and note.strip() else None
            if current.status is not SuggestionStatus.PENDING:
                if current.status == action and current.decided_by == identity.user_id:
                    return record
                raise SuggestionTransitionError(
                    f"suggestion {suggestion_id!r} is already {current.status.value}; decisions are immutable"
                )

            timestamp = decided_at or datetime.now(timezone.utc)
            decision = SuggestionDecision(
                suggestion_id=suggestion_id,
                tenant_id=identity.tenant_id,
                action=action,
                decided_by=identity.user_id,
                decided_at=timestamp,
                note=normalized_note,
            )
            updated = current.model_copy(
                update={"status": action, "decided_at": timestamp, "decided_by": identity.user_id}
            )
            updated_record = StoredSuggestion(
                suggestion=updated,
                decision_history=record.decision_history + (decision,),
            )
            self._records[key] = updated_record
            return updated_record


class JsonlSuggestionStore(InMemorySuggestionStore):
    """Append-only JSONL-backed store.

    The in-memory index is rebuilt from append-only events on startup. The
    file is not a tamper-evident audit log; it is durable application state
    for the inbox. Audit/observability surfaces remain separate.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__()
        self._load()

    def create(self, suggestion: Suggestion) -> Suggestion:
        is_new = self._key(suggestion.tenant_id, suggestion.suggestion_id) not in self._records
        created = super().create(suggestion)
        if is_new:
            self._append({"type": "created", "suggestion": suggestion.model_dump(mode="json")})
        return created

    def decide(
        self,
        *,
        identity: Identity,
        suggestion_id: str,
        action: SuggestionStatus,
        note: str | None = None,
        decided_at: datetime | None = None,
    ) -> StoredSuggestion:
        before = self.get(tenant_id=identity.tenant_id, suggestion_id=suggestion_id)
        decided = super().decide(
            identity=identity,
            suggestion_id=suggestion_id,
            action=action,
            note=note,
            decided_at=decided_at,
        )
        if len(decided.decision_history) > len(before.decision_history):
            self._append({"type": "decided", "decision": decided.decision_history[-1].model_dump(mode="json")})
        return decided

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
                if event["type"] == "created":
                    InMemorySuggestionStore.create(self, Suggestion.model_validate(event["suggestion"]))
                elif event["type"] == "decided":
                    decision = SuggestionDecision.model_validate(event["decision"])
                    identity = Identity(tenant_id=decision.tenant_id, user_id=decision.decided_by)
                    InMemorySuggestionStore.decide(
                        self,
                        identity=identity,
                        suggestion_id=decision.suggestion_id,
                        action=decision.action,
                        note=decision.note,
                        decided_at=decision.decided_at,
                    )
