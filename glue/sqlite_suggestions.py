"""SQLite-backed durable suggestion store.

This is a protocol-compatible persistence step between the current local JSONL
store and the future production PostgreSQL/RLS implementation. It keeps the
SuggestionStore contract stable while proving that suggestion state and review
history can survive process restarts without changing API handlers.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from .domain import Identity, Suggestion, SuggestionStatus, require_same_tenant
from .suggestions import (
    SuggestionDecision,
    SuggestionNotFoundError,
    SuggestionTransitionError,
    StoredSuggestion,
    _DECISION_STATUSES,
)


class SqliteSuggestionStore:
    """Durable suggestion review store using the stdlib SQLite driver."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def create(self, suggestion: Suggestion) -> Suggestion:
        require_same_tenant(suggestion, tenant_id=suggestion.tenant_id)
        payload = _dump_json(suggestion)

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO suggestions (
                    tenant_id,
                    suggestion_id,
                    status,
                    created_at,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    suggestion.tenant_id,
                    suggestion.suggestion_id,
                    suggestion.status.value,
                    suggestion.created_at.isoformat(),
                    payload,
                ),
            )
            conn.commit()

        return self.get(tenant_id=suggestion.tenant_id, suggestion_id=suggestion.suggestion_id).suggestion

    def list(self, *, tenant_id: str, status: SuggestionStatus | None = None) -> list[StoredSuggestion]:
        query = """
            SELECT tenant_id, suggestion_id
            FROM suggestions
            WHERE tenant_id = ?
        """
        params: list[str] = [tenant_id]
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY created_at DESC, suggestion_id ASC"

        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            self.get(tenant_id=row["tenant_id"], suggestion_id=row["suggestion_id"])
            for row in rows
        ]

    def get(self, *, tenant_id: str, suggestion_id: str) -> StoredSuggestion:
        with self._lock, self._connect() as conn:
            return self._get_locked(conn, tenant_id=tenant_id, suggestion_id=suggestion_id)

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

        with self._lock, self._connect() as conn:
            record = self._get_locked(conn, tenant_id=identity.tenant_id, suggestion_id=suggestion_id)
            require_same_tenant(identity, record.suggestion, tenant_id=identity.tenant_id)

            current = record.suggestion
            if current.status is not SuggestionStatus.PENDING:
                if current.status == action and current.decided_by == identity.user_id:
                    return record
                raise SuggestionTransitionError(
                    f"suggestion {suggestion_id!r} is already {current.status.value}; decisions are immutable"
                )

            timestamp = decided_at or datetime.now(timezone.utc)
            normalized_note = note.strip() if note and note.strip() else None
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
            conn.execute(
                """
                UPDATE suggestions
                SET status = ?, decided_at = ?, decided_by = ?, payload_json = ?
                WHERE tenant_id = ? AND suggestion_id = ?
                """,
                (
                    action.value,
                    timestamp.isoformat(),
                    identity.user_id,
                    _dump_json(updated),
                    identity.tenant_id,
                    suggestion_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO suggestion_decisions (
                    tenant_id,
                    suggestion_id,
                    decision_id,
                    action,
                    decided_by,
                    decided_at,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.tenant_id,
                    decision.suggestion_id,
                    decision.decision_id,
                    decision.action.value,
                    decision.decided_by,
                    decision.decided_at.isoformat(),
                    _dump_json(decision),
                ),
            )
            conn.commit()

            return self._get_locked(conn, tenant_id=identity.tenant_id, suggestion_id=suggestion_id)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS suggestions (
                    tenant_id TEXT NOT NULL,
                    suggestion_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    decided_at TEXT,
                    decided_by TEXT,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, suggestion_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS suggestion_decisions (
                    tenant_id TEXT NOT NULL,
                    suggestion_id TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    decided_by TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, decision_id),
                    FOREIGN KEY (tenant_id, suggestion_id)
                        REFERENCES suggestions (tenant_id, suggestion_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_suggestions_tenant_status_created
                ON suggestions (tenant_id, status, created_at)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decisions_tenant_suggestion_decided
                ON suggestion_decisions (tenant_id, suggestion_id, decided_at)
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _get_locked(
        conn: sqlite3.Connection,
        *,
        tenant_id: str,
        suggestion_id: str,
    ) -> StoredSuggestion:
        row = conn.execute(
            """
            SELECT payload_json
            FROM suggestions
            WHERE tenant_id = ? AND suggestion_id = ?
            """,
            (tenant_id, suggestion_id),
        ).fetchone()
        if row is None:
            raise SuggestionNotFoundError(suggestion_id)

        decision_rows = conn.execute(
            """
            SELECT payload_json
            FROM suggestion_decisions
            WHERE tenant_id = ? AND suggestion_id = ?
            ORDER BY decided_at ASC, decision_id ASC
            """,
            (tenant_id, suggestion_id),
        ).fetchall()

        return StoredSuggestion(
            suggestion=Suggestion.model_validate(json.loads(row["payload_json"])),
            decision_history=tuple(
                SuggestionDecision.model_validate(json.loads(decision_row["payload_json"]))
                for decision_row in decision_rows
            ),
        )


def _dump_json(model: Suggestion | SuggestionDecision) -> str:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
