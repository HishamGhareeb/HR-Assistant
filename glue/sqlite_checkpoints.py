"""SQLite-backed durable Frappe sync checkpoint store.

This is the local/single-node durable bridge for SyncEngine checkpoints. The
production target remains PostgreSQL/RLS, but this store proves the checkpoint
protocol can survive process restarts without changing SyncEngine itself.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from .frappe_sync import SyncCheckpoint


class SqliteCheckpointStore:
    """Durable implementation of the Frappe sync CheckpointStore protocol."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    async def get(self, tenant_id: str, doctype: str, name: str) -> SyncCheckpoint | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM sync_checkpoints
                WHERE tenant_id = ? AND doctype = ? AND name = ?
                """,
                (tenant_id, doctype, name),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        return SyncCheckpoint(
            content_hash=payload["content_hash"],
            document_id=payload["document_id"],
            tuples=tuple(tuple(item) for item in payload["tuples"]),
        )

    async def put(self, tenant_id: str, doctype: str, name: str, checkpoint: SyncCheckpoint) -> None:
        payload = json.dumps(
            {
                "content_hash": checkpoint.content_hash,
                "document_id": checkpoint.document_id,
                "tuples": [list(tuple_) for tuple_ in checkpoint.tuples],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_checkpoints (
                    tenant_id,
                    doctype,
                    name,
                    content_hash,
                    document_id,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, doctype, name)
                DO UPDATE SET
                    content_hash = excluded.content_hash,
                    document_id = excluded.document_id,
                    payload_json = excluded.payload_json
                """,
                (
                    tenant_id,
                    doctype,
                    name,
                    checkpoint.content_hash,
                    checkpoint.document_id,
                    payload,
                ),
            )
            conn.commit()

    async def delete(self, tenant_id: str, doctype: str, name: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                DELETE FROM sync_checkpoints
                WHERE tenant_id = ? AND doctype = ? AND name = ?
                """,
                (tenant_id, doctype, name),
            )
            conn.commit()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_checkpoints (
                    tenant_id TEXT NOT NULL,
                    doctype TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    document_id TEXT,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, doctype, name)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sync_checkpoints_tenant_doctype
                ON sync_checkpoints (tenant_id, doctype)
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn
