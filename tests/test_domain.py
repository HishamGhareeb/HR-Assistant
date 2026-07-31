from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from glue.domain import (
    Citation,
    CrossTenantError,
    Document,
    DocumentType,
    Identity,
    Suggestion,
    SuggestionStatus,
    require_same_tenant,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_citation(tenant_id: str = "acme") -> Citation:
    return Citation(
        source="onyx",
        object_type=DocumentType.LEAVE_RECORD,
        object_id="sarah_leave",
        tenant_id=tenant_id,
        retrieved_at=NOW,
    )


def make_document(tenant_id: str = "acme") -> Document:
    return Document(citation=make_citation(tenant_id), chunk="Sarah has 5 days of leave remaining.")


def make_suggestion(tenant_id: str = "acme", **overrides) -> Suggestion:
    fields = {
        "tenant_id": tenant_id,
        "category": "leave_expiring",
        "reasoning": "Sarah's carried-over leave expires in 7 days.",
        "record_reference": "sarah_leave",
        "created_at": NOW,
        **overrides,
    }
    return Suggestion(**fields)


# --- Identity -----------------------------------------------------------


def test_identity_requires_tenant_id():
    with pytest.raises(ValidationError):
        Identity(tenant_id="", user_id="sarah")


def test_identity_requires_user_id():
    with pytest.raises(ValidationError):
        Identity(tenant_id="acme", user_id="   ")


def test_identity_strips_whitespace():
    identity = Identity(tenant_id=" acme ", user_id=" sarah ")
    assert identity.tenant_id == "acme"
    assert identity.user_id == "sarah"


def test_identity_is_frozen():
    identity = Identity(tenant_id="acme", user_id="sarah")
    with pytest.raises(ValidationError):
        identity.user_id = "david"


# --- Citation / Document -------------------------------------------------


def test_citation_rejects_blank_tenant_id():
    with pytest.raises(ValidationError):
        Citation(
            source="onyx",
            object_type=DocumentType.LEAVE_RECORD,
            object_id="sarah_leave",
            tenant_id="",
            retrieved_at=NOW,
        )


def test_citation_rejects_naive_datetime():
    with pytest.raises(ValidationError):
        Citation(
            source="onyx",
            object_type=DocumentType.LEAVE_RECORD,
            object_id="sarah_leave",
            tenant_id="acme",
            retrieved_at=datetime(2026, 1, 1),
        )


def test_citation_rejects_unknown_document_type():
    with pytest.raises(ValidationError):
        Citation(
            source="onyx",
            object_type="not_a_real_type",
            object_id="sarah_leave",
            tenant_id="acme",
            retrieved_at=NOW,
        )


def test_document_exposes_citation_fields():
    document = make_document()
    assert document.tenant_id == "acme"
    assert document.object_type == DocumentType.LEAVE_RECORD
    assert document.object_id == "sarah_leave"


def test_document_round_trips_through_json():
    document = make_document()
    restored = Document.model_validate_json(document.model_dump_json())
    assert restored == document


# --- Suggestion lifecycle -------------------------------------------------


def test_suggestion_defaults_to_pending_with_no_decision():
    suggestion = make_suggestion()
    assert suggestion.status is SuggestionStatus.PENDING
    assert suggestion.decided_at is None
    assert suggestion.decided_by is None


def test_suggestion_approved_requires_decision_fields():
    with pytest.raises(ValidationError):
        make_suggestion(status=SuggestionStatus.APPROVED)


def test_suggestion_approved_with_decision_fields_is_valid():
    suggestion = make_suggestion(
        status=SuggestionStatus.APPROVED,
        decided_at=NOW,
        decided_by="hr_admin_1",
    )
    assert suggestion.status is SuggestionStatus.APPROVED


def test_suggestion_pending_rejects_stray_decision_fields():
    with pytest.raises(ValidationError):
        make_suggestion(decided_by="hr_admin_1")


def test_suggestion_round_trips_through_json():
    suggestion = make_suggestion(
        status=SuggestionStatus.REJECTED,
        decided_at=NOW,
        decided_by="hr_admin_1",
    )
    restored = Suggestion.model_validate_json(suggestion.model_dump_json())
    assert restored == suggestion


# --- Cross-tenant enforcement ---------------------------------------------


def test_require_same_tenant_passes_for_matching_tenant():
    require_same_tenant(
        Identity(tenant_id="acme", user_id="sarah"),
        make_document("acme"),
        make_suggestion("acme"),
        tenant_id="acme",
    )


def test_require_same_tenant_rejects_foreign_document():
    with pytest.raises(CrossTenantError):
        require_same_tenant(make_document("globex"), tenant_id="acme")


def test_require_same_tenant_rejects_foreign_identity():
    with pytest.raises(CrossTenantError):
        require_same_tenant(Identity(tenant_id="globex", user_id="sarah"), tenant_id="acme")


def test_require_same_tenant_rejects_foreign_suggestion():
    with pytest.raises(CrossTenantError):
        require_same_tenant(make_suggestion("globex"), tenant_id="acme")


def test_require_same_tenant_rejects_foreign_citation():
    with pytest.raises(CrossTenantError):
        require_same_tenant(make_citation("globex"), tenant_id="acme")
