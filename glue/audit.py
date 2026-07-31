"""Immutable audit events, recorded independently of Langfuse tracing.

`docs/ARCHITECTURE.md`'s "Gaps before production" lists "Add persistent
audit events and retention controls independent of model tracing" --
independent matters: Langfuse is a debugging/observability aid (optional,
see `glue/observability.py`'s `safe_call`), while an audit record is a
compliance artifact that must exist and be trustworthy whether or not
Langfuse is configured, reachable, or even installed correctly.

## What's in a record (and what deliberately isn't)

One `AuditEvent` per completed pipeline request, covering every stage in
`glue/pipeline.py`'s `handle_question` flow: identity, tenant, how many
candidates retrieval returned, how many survived authorization, what the
model/scanner outcome was, how many suggestions were raised, and the
*class* of any error -- never its message or a stack trace, and never the
question text, the answer text, or retrieved document content. That's the
redaction: sensitive text is minimized by never having a field for it in
the first place, not by scrubbing it after the fact. See
`test_audit.py::test_event_schema_has_no_free_text_fields` for a
structural check.

## Tamper-evidence

`HashChainedJsonlAuditSink` appends one JSON line per event, each carrying
`prev_hash` (the previous record's `hash`) and its own `hash` (a SHA-256
over the record's content + `prev_hash`). This makes any edit or deletion
of a past line detectable by recomputing the chain -- it is **tamper-
evident, not tamper-proof**: someone with write access to the file can
still rewrite the whole chain from the tampered point forward. True
tamper-*proofing* needs an external WORM store (S3 Object Lock, an
append-only database with revoked write grants, etc.) — see "Retention
and access policy" in `docs/AUDIT_AND_OBSERVABILITY.md` for what a real
deployment should layer on top of this.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

ModelOutcome = Literal["answered", "no_info", "blocked", "error"]
ScannerOutcome = Literal["passed", "blocked", "not_run"]

GENESIS_HASH = "0" * 64


class AuditEvent(BaseModel):
    """One record per completed (or failed) pipeline request. Every field
    is a bounded identifier, count, or enum -- there is no free-text field
    a question, answer, or document chunk could end up in."""

    model_config = {"frozen": True}

    event_id: str = Field(default_factory=lambda: uuid4().hex)
    # Generated request IDs are opaque UUID hex strings; accepting arbitrary
    # strings here would allow accidental input text to become audit data.
    request_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    tenant_id: str = Field(min_length=1)
    # A keyed, tenant-scoped pseudonym. Never store the source user ID.
    actor_ref: str = Field(pattern=r"^[0-9a-f]{64}$")
    timestamp: datetime

    retrieval_count: int = Field(ge=0)
    authorized_count: int = Field(ge=0)
    model_outcome: ModelOutcome
    scanner_outcome: ScannerOutcome
    suggestion_count: int = Field(ge=0)
    error_class: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,99}$")

    def canonical_json(self) -> str:
        """Deterministic serialization used for hashing -- sorted keys, no
        whitespace, so the same event always hashes the same way."""
        return json.dumps(
            self.model_dump(mode="json", by_alias=True, exclude_none=False),
            sort_keys=True,
            separators=(",", ":"),
        )


class AuditSink(Protocol):
    def append(self, event: AuditEvent) -> None: ...


class InMemoryAuditSink:
    """Process-local sink for tests and for composing with a real sink
    (e.g. record in memory for a request-scoped summary, and also persist
    to a `HashChainedJsonlAuditSink`)."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self.events.append(event)


@dataclass(frozen=True)
class ChainedRecord:
    event: AuditEvent
    prev_hash: str
    hash: str


def _record_hash(event: AuditEvent, prev_hash: str) -> str:
    payload = f"{prev_hash}|{event.canonical_json()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class HashChainedJsonlAuditSink:
    """Append-only JSONL file, each line hash-chained to the previous one.
    Safe to construct against an existing file -- it reads the last line's
    hash on init so a restarted process continues the same chain instead
    of starting a new, disconnected one."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._read_last_hash()

    def _read_last_hash(self) -> str:
        if not self._path.exists():
            return GENESIS_HASH
        last_hash = GENESIS_HASH
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                last_hash = json.loads(line)["hash"]
        return last_hash

    def append(self, event: AuditEvent) -> None:
        record_hash = _record_hash(event, self._last_hash)
        line = {
            "prev_hash": self._last_hash,
            "hash": record_hash,
            "event": json.loads(event.canonical_json()),
        }
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
        self._last_hash = record_hash

    def verify_chain(self) -> bool:
        """Recomputes every hash from the start of the file and confirms
        it matches what's stored -- returns False the moment any record
        has been edited, reordered, or removed."""
        if not self._path.exists():
            return True
        expected_prev = GENESIS_HASH
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record["prev_hash"] != expected_prev:
                    return False
                event = AuditEvent.model_validate(record["event"])
                if _record_hash(event, expected_prev) != record["hash"]:
                    return False
                expected_prev = record["hash"]
        return True


class AuditLogger:
    """Thin, typed wrapper over an `AuditSink` -- construct one
    `AuditEvent` per pipeline request and record it. Recording failures
    are the caller's decision to handle (this does not swallow them):
    unlike Langfuse tracing, a broken audit sink is not something that
    should be silently ignored."""

    def __init__(self, sink: AuditSink, *, privacy_key: bytes) -> None:
        if not privacy_key:
            raise ValueError("privacy_key must not be empty")
        self._sink = sink
        self._privacy_key = privacy_key

    def record(
        self,
        *,
        request_id: str,
        tenant_id: str,
        user_id: str,
        retrieval_count: int,
        authorized_count: int,
        model_outcome: ModelOutcome,
        scanner_outcome: ScannerOutcome,
        suggestion_count: int = 0,
        error_class: str | None = None,
        timestamp: datetime | None = None,
    ) -> AuditEvent:
        # HMAC is deliberately used instead of a plain hash: a small or
        # predictable employee-ID space must not make the record reversible.
        actor_ref = hmac.new(
            self._privacy_key,
            f"{tenant_id}:{user_id}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        event = AuditEvent(
            request_id=request_id,
            tenant_id=tenant_id,
            actor_ref=actor_ref,
            timestamp=timestamp or datetime.now(timezone.utc),
            retrieval_count=retrieval_count,
            authorized_count=authorized_count,
            model_outcome=model_outcome,
            scanner_outcome=scanner_outcome,
            suggestion_count=suggestion_count,
            error_class=error_class,
        )
        self._sink.append(event)
        return event
