from datetime import datetime, timezone

import pytest

from glue.domain import Identity, Suggestion, SuggestionStatus
from glue.suggestions import (
    InMemorySuggestionStore,
    JsonlSuggestionStore,
    StaticHrReviewAuthorizer,
    SuggestionAuthorizationError,
    SuggestionNotFoundError,
    SuggestionTransitionError,
)
from glue.sqlite_suggestions import SqliteSuggestionStore

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_suggestion(tenant_id="acme", suggestion_id="sug-1") -> Suggestion:
    return Suggestion(
        suggestion_id=suggestion_id,
        tenant_id=tenant_id,
        category="leave_expiring",
        reasoning="Carried-over leave expires soon.",
        record_reference="LEAVE-1",
        created_at=NOW,
    )


def test_static_authorizer_is_tenant_scoped():
    authorizer = StaticHrReviewAuthorizer({"acme": ["hr-1"]})
    authorizer.authorize(Identity(tenant_id="acme", user_id="hr-1"))

    with pytest.raises(SuggestionAuthorizationError):
        authorizer.authorize(Identity(tenant_id="globex", user_id="hr-1"))


def test_store_lists_only_same_tenant_suggestions():
    store = InMemorySuggestionStore()
    store.create(make_suggestion("acme", "acme-sug"))
    store.create(make_suggestion("globex", "globex-sug"))

    visible = store.list(tenant_id="acme")

    assert [record.suggestion.suggestion_id for record in visible] == ["acme-sug"]


def test_foreign_suggestion_id_is_not_found_inside_tenant():
    store = InMemorySuggestionStore()
    store.create(make_suggestion("globex", "shared-looking-id"))

    with pytest.raises(SuggestionNotFoundError):
        store.get(tenant_id="acme", suggestion_id="shared-looking-id")


def test_same_suggestion_id_can_exist_in_multiple_tenants():
    store = InMemorySuggestionStore()
    store.create(make_suggestion("acme", "shared-id"))
    store.create(make_suggestion("globex", "shared-id"))

    acme = store.get(tenant_id="acme", suggestion_id="shared-id")
    globex = store.get(tenant_id="globex", suggestion_id="shared-id")

    assert acme.suggestion.tenant_id == "acme"
    assert globex.suggestion.tenant_id == "globex"


def test_decision_records_status_and_immutable_history():
    store = InMemorySuggestionStore()
    store.create(make_suggestion())
    identity = Identity(tenant_id="acme", user_id="hr-1")

    stored = store.decide(identity=identity, suggestion_id="sug-1", action=SuggestionStatus.APPROVED, note="Looks right.")

    assert stored.suggestion.status is SuggestionStatus.APPROVED
    assert stored.suggestion.decided_by == "hr-1"
    assert len(stored.decision_history) == 1
    assert stored.decision_history[0].action is SuggestionStatus.APPROVED
    assert stored.decision_history[0].note == "Looks right."


def test_duplicate_same_decision_is_idempotent():
    store = InMemorySuggestionStore()
    store.create(make_suggestion())
    identity = Identity(tenant_id="acme", user_id="hr-1")

    first = store.decide(identity=identity, suggestion_id="sug-1", action=SuggestionStatus.DISMISSED)
    second = store.decide(identity=identity, suggestion_id="sug-1", action=SuggestionStatus.DISMISSED)

    assert second.suggestion == first.suggestion
    assert len(second.decision_history) == 1


def test_different_second_decision_is_rejected():
    store = InMemorySuggestionStore()
    store.create(make_suggestion())
    identity = Identity(tenant_id="acme", user_id="hr-1")
    store.decide(identity=identity, suggestion_id="sug-1", action=SuggestionStatus.REJECTED)

    with pytest.raises(SuggestionTransitionError):
        store.decide(identity=identity, suggestion_id="sug-1", action=SuggestionStatus.APPROVED)


def test_jsonl_store_persists_suggestions_and_history(tmp_path):
    path = tmp_path / "suggestions.jsonl"
    store = JsonlSuggestionStore(path)
    store.create(make_suggestion())
    store.decide(
        identity=Identity(tenant_id="acme", user_id="hr-1"),
        suggestion_id="sug-1",
        action=SuggestionStatus.REJECTED,
        note="Not actionable.",
    )

    restored = JsonlSuggestionStore(path).get(tenant_id="acme", suggestion_id="sug-1")

    assert restored.suggestion.status is SuggestionStatus.REJECTED
    assert len(restored.decision_history) == 1
    assert restored.decision_history[0].note == "Not actionable."


def test_sqlite_store_persists_suggestions_and_history(tmp_path):
    path = tmp_path / "suggestions.sqlite3"
    store = SqliteSuggestionStore(path)
    store.create(make_suggestion())
    store.decide(
        identity=Identity(tenant_id="acme", user_id="hr-1"),
        suggestion_id="sug-1",
        action=SuggestionStatus.APPROVED,
        note="Approved for follow-up.",
    )

    restored = SqliteSuggestionStore(path).get(tenant_id="acme", suggestion_id="sug-1")

    assert restored.suggestion.status is SuggestionStatus.APPROVED
    assert restored.suggestion.decided_by == "hr-1"
    assert len(restored.decision_history) == 1
    assert restored.decision_history[0].note == "Approved for follow-up."


def test_sqlite_store_keeps_same_suggestion_id_tenant_isolated(tmp_path):
    store = SqliteSuggestionStore(tmp_path / "suggestions.sqlite3")
    store.create(make_suggestion("acme", "shared-id"))
    store.create(make_suggestion("globex", "shared-id"))

    store.decide(
        identity=Identity(tenant_id="acme", user_id="hr-1"),
        suggestion_id="shared-id",
        action=SuggestionStatus.DISMISSED,
    )

    acme = store.get(tenant_id="acme", suggestion_id="shared-id")
    globex = store.get(tenant_id="globex", suggestion_id="shared-id")

    assert acme.suggestion.status is SuggestionStatus.DISMISSED
    assert globex.suggestion.status is SuggestionStatus.PENDING


def test_sqlite_store_rejects_different_second_decision_after_restart(tmp_path):
    path = tmp_path / "suggestions.sqlite3"
    store = SqliteSuggestionStore(path)
    store.create(make_suggestion())
    store.decide(
        identity=Identity(tenant_id="acme", user_id="hr-1"),
        suggestion_id="sug-1",
        action=SuggestionStatus.REJECTED,
    )

    restored = SqliteSuggestionStore(path)

    with pytest.raises(SuggestionTransitionError):
        restored.decide(
            identity=Identity(tenant_id="acme", user_id="hr-1"),
            suggestion_id="sug-1",
            action=SuggestionStatus.APPROVED,
        )


def test_sqlite_store_lists_only_requested_status_inside_tenant(tmp_path):
    store = SqliteSuggestionStore(tmp_path / "suggestions.sqlite3")
    store.create(make_suggestion("acme", "pending"))
    store.create(make_suggestion("acme", "approved"))
    store.create(make_suggestion("globex", "approved"))
    store.decide(
        identity=Identity(tenant_id="acme", user_id="hr-1"),
        suggestion_id="approved",
        action=SuggestionStatus.APPROVED,
    )
    store.decide(
        identity=Identity(tenant_id="globex", user_id="hr-2"),
        suggestion_id="approved",
        action=SuggestionStatus.APPROVED,
    )

    visible = store.list(tenant_id="acme", status=SuggestionStatus.APPROVED)

    assert [record.suggestion.suggestion_id for record in visible] == ["approved"]
