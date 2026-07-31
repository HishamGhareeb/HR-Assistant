"""Deterministic sync from Frappe HR records into Onyx retrieval documents
and OpenFGA authorization tuples.

## Shape

`FrappeRecord` is the generic, synthetic stand-in for "one row Frappe's
REST API returned for one doctype" -- this ticket is scoped to *synthetic*
data (see docs/FRAPPE_SYNC.md); a real Frappe polling/webhook source is a
later concern and would just need to produce the same `FrappeRecord`
shape.

`map_record` is a pure function: one `FrappeRecord` in, one `MappingResult`
out (an optional retrieval document + the OpenFGA tuples that record
contributes). It never talks to Onyx, OpenFGA, or a checkpoint store --
that keeps the "what does this Frappe record mean" logic trivially unit
testable, separate from "how do we apply that idempotently."

`SyncEngine.sync_all` is what actually applies mapping results: it diffs
each record's current mapping against the last-known-synced state in a
`CheckpointStore`, upserts/deletes only what changed, and produces a
`ReconciliationReport`. Both `.upsert()`/`.delete()` failures are caught
per-record so one bad record can't abort the run, and a failed record's
checkpoint is left untouched (not marked synced) so the *next* run retries
exactly that record -- the "retryable checkpoint" behavior.

## Tenant scoping

Every `FrappeRecord.tenant_id` flows straight into the document metadata
(`glue.onyx_client` requires it) and the OpenFGA object ID
(`glue.openfga_client.scoped_object_id`) -- there is no code path that
builds either without it, matching `glue.domain`'s "no tenant-less
document identity."
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from .domain import DocumentType
from .openfga_client import scoped_object_id

logger = logging.getLogger(__name__)


# --- Frappe input shape -----------------------------------------------------


@dataclass(frozen=True)
class FrappeRecord:
    """One doctype row as Frappe's REST API would return it. `deleted=True`
    represents a row that no longer exists (or was soft-deleted/revoked) --
    `fields` may be empty in that case, only `doctype`/`name`/`tenant_id`
    are required to process a deletion."""

    doctype: str
    name: str
    tenant_id: str
    fields: dict = field(default_factory=dict)
    deleted: bool = False

    def __post_init__(self) -> None:
        if not self.doctype.strip():
            raise ValueError("doctype must not be blank")
        if not self.name.strip():
            raise ValueError("name must not be blank")
        if not self.tenant_id.strip():
            raise ValueError("tenant_id must not be blank")


class FrappeMappingError(ValueError):
    """A FrappeRecord's `doctype` is unsupported, or a required field for
    its doctype is missing -- raised rather than guessing, so a malformed
    synthetic (or eventually real) Frappe row surfaces as a sync failure
    for that one record, not silently-wrong tuples."""


# --- mapping output ----------------------------------------------------


@dataclass(frozen=True)
class IndexedDocumentRef:
    object_type: DocumentType
    semantic_identifier: str
    text: str


@dataclass(frozen=True)
class FgaTupleRef:
    """One `(user, relation, object)` contribution, with `object_type` /
    `object_local_id` left un-namespaced -- SyncEngine applies
    `scoped_object_id` with the record's tenant_id when it's time to talk
    to OpenFGA, so mapping stays tenant-agnostic and easy to unit test."""

    user: str
    relation: str
    object_type: str
    object_local_id: str


@dataclass(frozen=True)
class MappingResult:
    document: IndexedDocumentRef | None
    tuples: tuple[FgaTupleRef, ...] = ()


@dataclass
class SyncConfig:
    """Sync-run-wide policy that isn't itself a Frappe field: which users
    hold the hr_admin role. Frappe doesn't tag this per-record, and
    treating it as sync configuration (rather than inventing a synthetic
    Frappe field for it) keeps `map_record` honest about what actually
    comes from Frappe."""

    hr_admin_user_ids: tuple[str, ...] = ()


# --- per-doctype mapping -------------------------------------------------


def _require(fields: dict, key: str, doctype: str) -> str:
    value = fields.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FrappeMappingError(f"{doctype} record is missing required field {key!r}")
    return value.strip()


def _map_employee(record: FrappeRecord) -> MappingResult:
    fields = record.fields
    user_id = _require(fields, "user_id", record.doctype)
    department = _require(fields, "department", record.doctype)
    employee_name = fields.get("employee_name", record.name)
    reports_to = fields.get("reports_to")

    document = IndexedDocumentRef(
        object_type=DocumentType.EMPLOYEE_RECORD,
        semantic_identifier=f"Employee: {employee_name}",
        text=f"{employee_name} is a member of the {department} department.",
    )
    tuples = [FgaTupleRef(user=f"user:{user_id}", relation="member", object_type="department", object_local_id=department)]
    if reports_to:
        tuples.append(
            FgaTupleRef(user=f"user:{reports_to}", relation="manager", object_type="department", object_local_id=department)
        )
    return MappingResult(document=document, tuples=tuple(tuples))


def _map_department(record: FrappeRecord) -> MappingResult:
    # Departments are referenced (as FGA objects) by other doctypes but
    # don't themselves own a retrieval document or contribute tuples --
    # membership/management tuples come from the Employee records that
    # point at this department.
    return MappingResult(document=None, tuples=())


def _record_relation_tuples(
    record: FrappeRecord,
    config: SyncConfig,
    object_type: str,
    owner_user_id: str,
    department: str | None,
) -> tuple[FgaTupleRef, ...]:
    tuples = [FgaTupleRef(user=f"user:{owner_user_id}", relation="owner", object_type=object_type, object_local_id=record.name)]
    if department is not None:
        tuples.append(
            FgaTupleRef(
                user=f"{object_type}:{record.name}",
                relation="department",
                object_type="department",
                object_local_id=department,
            )
        )
    tuples.extend(
        FgaTupleRef(user=f"user:{admin_id}", relation="hr_admin", object_type=object_type, object_local_id=record.name)
        for admin_id in config.hr_admin_user_ids
    )
    return tuple(tuples)


def _map_leave_application(record: FrappeRecord, config: SyncConfig) -> MappingResult:
    fields = record.fields
    employee_user_id = _require(fields, "employee_user_id", record.doctype)
    department = _require(fields, "department", record.doctype)
    leave_type = fields.get("leave_type", "leave")
    status = fields.get("status", "unknown")

    document = IndexedDocumentRef(
        object_type=DocumentType.LEAVE_RECORD,
        semantic_identifier=f"Leave application: {record.name}",
        text=f"{leave_type} application ({record.name}) status: {status}.",
    )
    tuples = _record_relation_tuples(record, config, "leave_record", employee_user_id, department)
    return MappingResult(document=document, tuples=tuples)


def _map_appraisal(record: FrappeRecord, config: SyncConfig) -> MappingResult:
    fields = record.fields
    employee_user_id = _require(fields, "employee_user_id", record.doctype)
    department = _require(fields, "department", record.doctype)
    summary = fields.get("summary", "Performance review on file.")

    document = IndexedDocumentRef(
        object_type=DocumentType.PERFORMANCE_RECORD,
        semantic_identifier=f"Performance review: {record.name}",
        text=summary,
    )
    tuples = _record_relation_tuples(record, config, "performance_record", employee_user_id, department)
    return MappingResult(document=document, tuples=tuples)


def _map_salary_slip(record: FrappeRecord, config: SyncConfig) -> MappingResult:
    fields = record.fields
    employee_user_id = _require(fields, "employee_user_id", record.doctype)
    period = fields.get("period", record.name)

    document = IndexedDocumentRef(
        object_type=DocumentType.SALARY_RECORD,
        semantic_identifier=f"Salary slip: {record.name}",
        text=f"Salary slip for {period}.",
    )
    # No department tuple: salary_record has no "manager from department"
    # relation in openfga/model.fga, by design -- managers must never see
    # a report's compensation.
    tuples = _record_relation_tuples(record, config, "salary_record", employee_user_id, department=None)
    return MappingResult(document=document, tuples=tuples)


def _map_hr_policy(record: FrappeRecord) -> MappingResult:
    fields = record.fields
    title = fields.get("title", record.name)
    body = _require(fields, "body", record.doctype)

    document = IndexedDocumentRef(
        object_type=DocumentType.POLICY_DOCUMENT,
        semantic_identifier=f"Policy: {title}",
        text=body,
    )
    tuples = (FgaTupleRef(user="user:*", relation="viewer", object_type="policy_document", object_local_id=record.name),)
    return MappingResult(document=document, tuples=tuples)


_MAPPERS = {
    "Employee": lambda record, config: _map_employee(record),
    "Department": lambda record, config: _map_department(record),
    "Leave Application": _map_leave_application,
    "Appraisal": _map_appraisal,
    "Salary Slip": _map_salary_slip,
    "HR Policy": lambda record, config: _map_hr_policy(record),
}


def map_record(record: FrappeRecord, config: SyncConfig) -> MappingResult:
    mapper = _MAPPERS.get(record.doctype)
    if mapper is None:
        raise FrappeMappingError(f"unsupported Frappe doctype: {record.doctype!r}")
    return mapper(record, config)


def document_object_id(record: FrappeRecord, document: IndexedDocumentRef) -> str:
    """Stable Onyx document ID for a record's indexed document. Includes
    the tenant so the same convention as OpenFGA object IDs holds even
    though Onyx document IDs aren't otherwise namespaced by this codebase."""
    return f"frappe:{record.tenant_id}:{document.object_type.value}:{record.name}"


# --- ports (Onyx / OpenFGA / checkpoint storage) ----------------------------


class DocumentIndexPort(Protocol):
    async def upsert(self, *, document_id: str, semantic_identifier: str, text: str, metadata: dict[str, str]) -> bool: ...
    async def delete(self, document_id: str) -> None: ...


class TupleWriterPort(Protocol):
    async def write_tuples(self, tuples: list[tuple[str, str, str]]) -> None: ...
    async def delete_tuples(self, tuples: list[tuple[str, str, str]]) -> None: ...


@dataclass(frozen=True)
class SyncCheckpoint:
    content_hash: str
    document_id: str | None
    tuples: tuple[tuple[str, str, str], ...]


class CheckpointStore(Protocol):
    async def get(self, tenant_id: str, doctype: str, name: str) -> SyncCheckpoint | None: ...
    async def put(self, tenant_id: str, doctype: str, name: str, checkpoint: SyncCheckpoint) -> None: ...
    async def delete(self, tenant_id: str, doctype: str, name: str) -> None: ...


class InMemoryCheckpointStore:
    """Default, process-local checkpoint store. Fine for a single sync
    process; a real deployment with concurrent/distributed sync runs would
    swap this for a persisted implementation behind the same protocol."""

    def __init__(self) -> None:
        self._data: dict[tuple[str, str, str], SyncCheckpoint] = {}

    async def get(self, tenant_id: str, doctype: str, name: str) -> SyncCheckpoint | None:
        return self._data.get((tenant_id, doctype, name))

    async def put(self, tenant_id: str, doctype: str, name: str, checkpoint: SyncCheckpoint) -> None:
        self._data[(tenant_id, doctype, name)] = checkpoint

    async def delete(self, tenant_id: str, doctype: str, name: str) -> None:
        self._data.pop((tenant_id, doctype, name), None)


def _content_hash(document: IndexedDocumentRef | None, tuples: tuple[FgaTupleRef, ...]) -> str:
    payload = {
        "document": None if document is None else [document.object_type.value, document.semantic_identifier, document.text],
        "tuples": sorted([t.user, t.relation, t.object_type, t.object_local_id] for t in tuples),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


# --- reconciliation report ---------------------------------------------


@dataclass
class RecordFailure:
    doctype: str
    name: str
    reason: str


@dataclass
class ReconciliationReport:
    tenant_id: str
    started_at: datetime
    finished_at: datetime | None = None
    created: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0
    failed: list[RecordFailure] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return self.created + self.updated + self.deleted + self.unchanged + len(self.failed)


# --- sync engine ---------------------------------------------------------


class SyncEngine:
    def __init__(
        self,
        document_index: DocumentIndexPort,
        tuple_writer: TupleWriterPort,
        checkpoints: CheckpointStore | None = None,
        config: SyncConfig | None = None,
    ) -> None:
        self._document_index = document_index
        self._tuple_writer = tuple_writer
        self._checkpoints = checkpoints or InMemoryCheckpointStore()
        self._config = config or SyncConfig()

    def _scoped(self, tenant_id: str, tuples: tuple[FgaTupleRef, ...]) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            (t.user, t.relation, scoped_object_id(t.object_type, tenant_id, t.object_local_id)) for t in tuples
        )

    async def sync_record(self, record: FrappeRecord, report: ReconciliationReport) -> None:
        existing = await self._checkpoints.get(record.tenant_id, record.doctype, record.name)

        if record.deleted:
            if existing is None:
                report.unchanged += 1
                return
            try:
                if existing.document_id is not None:
                    await self._document_index.delete(existing.document_id)
                if existing.tuples:
                    await self._tuple_writer.delete_tuples(list(existing.tuples))
            except Exception as exc:
                report.failed.append(RecordFailure(record.doctype, record.name, str(exc)))
                return
            await self._checkpoints.delete(record.tenant_id, record.doctype, record.name)
            report.deleted += 1
            return

        try:
            mapping = map_record(record, self._config)
        except FrappeMappingError as exc:
            report.failed.append(RecordFailure(record.doctype, record.name, str(exc)))
            return

        new_hash = _content_hash(mapping.document, mapping.tuples)
        if existing is not None and existing.content_hash == new_hash:
            report.unchanged += 1
            return

        new_scoped_tuples = self._scoped(record.tenant_id, mapping.tuples)
        document_id = None

        try:
            if mapping.document is not None:
                document_id = document_object_id(record, mapping.document)
                await self._document_index.upsert(
                    document_id=document_id,
                    semantic_identifier=mapping.document.semantic_identifier,
                    text=mapping.document.text,
                    metadata={"tenant_id": record.tenant_id, "record_type": mapping.document.object_type.value},
                )
            elif existing is not None and existing.document_id is not None:
                await self._document_index.delete(existing.document_id)

            stale_tuples = set(existing.tuples) - set(new_scoped_tuples) if existing else set()
            fresh_tuples = set(new_scoped_tuples) - (set(existing.tuples) if existing else set())
            if stale_tuples:
                await self._tuple_writer.delete_tuples(list(stale_tuples))
            if fresh_tuples:
                await self._tuple_writer.write_tuples(list(fresh_tuples))
        except Exception as exc:
            # Checkpoint is intentionally left untouched (or absent) so the
            # next sync_all() run retries this exact record instead of
            # treating a half-applied change as done.
            report.failed.append(RecordFailure(record.doctype, record.name, str(exc)))
            return

        await self._checkpoints.put(
            record.tenant_id,
            record.doctype,
            record.name,
            SyncCheckpoint(content_hash=new_hash, document_id=document_id, tuples=new_scoped_tuples),
        )
        if existing is None:
            report.created += 1
        else:
            report.updated += 1

    async def sync_all(self, tenant_id: str, records: list[FrappeRecord]) -> ReconciliationReport:
        report = ReconciliationReport(tenant_id=tenant_id, started_at=datetime.now(timezone.utc))
        for record in records:
            if record.tenant_id != tenant_id:
                report.failed.append(
                    RecordFailure(record.doctype, record.name, f"record tenant_id {record.tenant_id!r} != sync tenant_id {tenant_id!r}")
                )
                continue
            await self.sync_record(record, report)
        report.finished_at = datetime.now(timezone.utc)
        return report
