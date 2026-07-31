from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from glue.audit import AuditEvent, AuditLogger, HashChainedJsonlAuditSink, InMemoryAuditSink


def record(logger: AuditLogger):
    return logger.record(
        request_id="a" * 32,
        tenant_id="tenant-acme",
        user_id="employee-42@example.test",
        retrieval_count=4,
        authorized_count=2,
        model_outcome="answered",
        scanner_outcome="passed",
        suggestion_count=1,
        timestamp=datetime(2026, 7, 31, tzinfo=timezone.utc),
    )


def test_event_contains_pseudonymous_actor_not_raw_user_or_content() -> None:
    sink = InMemoryAuditSink()
    event = record(AuditLogger(sink, privacy_key=b"test-key"))

    serialized = event.model_dump_json()
    assert event.actor_ref != "employee-42@example.test"
    assert len(event.actor_ref) == 64
    assert "employee-42" not in serialized
    assert "question" not in AuditEvent.model_fields
    assert "answer" not in AuditEvent.model_fields
    assert "document" not in AuditEvent.model_fields
    assert sink.events == [event]


def test_pseudonym_is_stable_per_tenant_and_scoped_between_tenants() -> None:
    logger = AuditLogger(InMemoryAuditSink(), privacy_key=b"test-key")
    first = record(logger)
    second = record(logger)
    other_tenant = logger.record(
        request_id="b" * 32, tenant_id="tenant-other", user_id="employee-42@example.test",
        retrieval_count=0, authorized_count=0, model_outcome="no_info", scanner_outcome="not_run",
    )
    assert first.actor_ref == second.actor_ref
    assert first.actor_ref != other_tenant.actor_ref


def test_hash_chained_file_is_append_only_and_detects_tampering(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    sink = HashChainedJsonlAuditSink(path)
    logger = AuditLogger(sink, privacy_key=b"test-key")
    record(logger)
    record(logger)

    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(lines) == 2
    assert lines[1]["prev_hash"] == lines[0]["hash"]
    assert sink.verify_chain()

    # A restarted worker must continue the existing chain rather than create
    # a disconnected log.
    record(AuditLogger(HashChainedJsonlAuditSink(path), privacy_key=b"test-key"))
    continued = [json.loads(line) for line in path.read_text().splitlines()]
    assert continued[2]["prev_hash"] == continued[1]["hash"]

    continued[0]["event"]["retrieval_count"] = 999
    path.write_text("\n".join(json.dumps(line) for line in continued) + "\n")
    assert not HashChainedJsonlAuditSink(path).verify_chain()


def test_rejects_raw_or_invalid_actor_references() -> None:
    with pytest.raises(ValidationError):
        AuditEvent(
            request_id="a" * 32, tenant_id="t", actor_ref="a-person@example.test",
            timestamp=datetime.now(timezone.utc), retrieval_count=0, authorized_count=0,
            model_outcome="error", scanner_outcome="not_run", suggestion_count=0,
        )
