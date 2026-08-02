from datetime import datetime, timezone

import pytest

from glue.domain import Identity
from glue.feedback import (
    AnswerFeedback,
    FeedbackAuthorizationError,
    FeedbackNotFoundError,
    FeedbackReasonCode,
    FeedbackTransitionError,
    InMemoryFeedbackStore,
    JsonlFeedbackStore,
    StaticHrFeedbackAuthorizer,
    UnansweredQuestion,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_helpful_feedback(tenant_id="acme", feedback_id="fb-1") -> AnswerFeedback:
    return AnswerFeedback(
        feedback_id=feedback_id,
        tenant_id=tenant_id,
        user_id="sarah",
        request_id="req-1",
        question="What is my leave balance?",
        answer="You have 5 days left.",
        helpful=True,
        created_at=NOW,
    )


def make_not_helpful_feedback(tenant_id="acme", feedback_id="fb-2") -> AnswerFeedback:
    return AnswerFeedback(
        feedback_id=feedback_id,
        tenant_id=tenant_id,
        user_id="sarah",
        request_id="req-2",
        question="What is the maternity leave policy?",
        answer="I don't have information on that.",
        helpful=False,
        reason_code=FeedbackReasonCode.INCOMPLETE,
        escalated=True,
        created_at=NOW,
    )


# --- model validation --------------------------------------------------------


def test_helpful_feedback_cannot_carry_a_reason_code():
    with pytest.raises(ValueError, match="reason_code only applies to not-helpful"):
        AnswerFeedback(
            tenant_id="acme", user_id="sarah", request_id="req-1",
            question="q", answer="a", helpful=True, reason_code=FeedbackReasonCode.OTHER, created_at=NOW,
        )


def test_not_helpful_feedback_requires_a_reason_code():
    with pytest.raises(ValueError, match="requires a reason_code"):
        AnswerFeedback(
            tenant_id="acme", user_id="sarah", request_id="req-1",
            question="q", answer="a", helpful=False, created_at=NOW,
        )


def test_not_helpful_feedback_must_be_escalated():
    with pytest.raises(ValueError, match="must be escalated"):
        AnswerFeedback(
            tenant_id="acme", user_id="sarah", request_id="req-1",
            question="q", answer="a", helpful=False, reason_code=FeedbackReasonCode.OTHER,
            escalated=False, created_at=NOW,
        )


def test_submit_helper_sets_escalated_for_not_helpful_only():
    identity = Identity(tenant_id="acme", user_id="sarah")

    helpful = AnswerFeedback.submit(
        identity=identity, request_id="req-1", question="q", answer="a", helpful=True, created_at=NOW,
    )
    not_helpful = AnswerFeedback.submit(
        identity=identity, request_id="req-2", question="q", answer="a", helpful=False,
        reason_code=FeedbackReasonCode.INCORRECT, created_at=NOW,
    )

    assert helpful.escalated is False
    assert not_helpful.escalated is True


# --- authorizer ---------------------------------------------------------------


def test_static_authorizer_is_tenant_scoped():
    authorizer = StaticHrFeedbackAuthorizer({"acme": ["hr-1"]})
    authorizer.authorize(Identity(tenant_id="acme", user_id="hr-1"))

    with pytest.raises(FeedbackAuthorizationError):
        authorizer.authorize(Identity(tenant_id="globex", user_id="hr-1"))


# --- store: feedback ------------------------------------------------------


def test_store_lists_only_same_tenant_feedback():
    store = InMemoryFeedbackStore()
    store.record_feedback(make_helpful_feedback("acme", "acme-fb"))
    store.record_feedback(make_helpful_feedback("globex", "globex-fb"))

    visible = store.list_feedback(tenant_id="acme")

    assert [f.feedback_id for f in visible] == ["acme-fb"]


def test_list_feedback_filters_by_helpful_and_escalated():
    store = InMemoryFeedbackStore()
    store.record_feedback(make_helpful_feedback("acme", "helpful-1"))
    store.record_feedback(make_not_helpful_feedback("acme", "not-helpful-1"))

    only_not_helpful = store.list_feedback(tenant_id="acme", helpful=False)
    only_escalated = store.list_feedback(tenant_id="acme", escalated_only=True)

    assert [f.feedback_id for f in only_not_helpful] == ["not-helpful-1"]
    assert [f.feedback_id for f in only_escalated] == ["not-helpful-1"]


def test_foreign_feedback_id_is_not_found_inside_tenant():
    store = InMemoryFeedbackStore()
    store.record_feedback(make_helpful_feedback("globex", "shared-looking-id"))

    with pytest.raises(FeedbackNotFoundError):
        store.get_feedback(tenant_id="acme", feedback_id="shared-looking-id")


# --- store: resolution ------------------------------------------------------


def test_resolve_requires_escalated_feedback():
    store = InMemoryFeedbackStore()
    store.record_feedback(make_helpful_feedback())
    identity = Identity(tenant_id="acme", user_id="hr-1")

    with pytest.raises(FeedbackTransitionError, match="only escalated feedback"):
        store.resolve(identity=identity, feedback_id="fb-1")


def test_resolve_records_resolution():
    store = InMemoryFeedbackStore()
    store.record_feedback(make_not_helpful_feedback())
    identity = Identity(tenant_id="acme", user_id="hr-1")

    resolved = store.resolve(identity=identity, feedback_id="fb-2", note="Added policy doc to Onyx.")

    assert resolved.resolved is True
    assert resolved.resolution.resolved_by == "hr-1"
    assert resolved.resolution.note == "Added policy doc to Onyx."


def test_resolve_twice_by_same_reviewer_is_idempotent():
    store = InMemoryFeedbackStore()
    store.record_feedback(make_not_helpful_feedback())
    identity = Identity(tenant_id="acme", user_id="hr-1")

    first = store.resolve(identity=identity, feedback_id="fb-2")
    second = store.resolve(identity=identity, feedback_id="fb-2")

    assert first == second


def test_resolve_twice_by_different_reviewer_is_rejected():
    store = InMemoryFeedbackStore()
    store.record_feedback(make_not_helpful_feedback())
    store.resolve(identity=Identity(tenant_id="acme", user_id="hr-1"), feedback_id="fb-2")

    with pytest.raises(FeedbackTransitionError, match="already resolved"):
        store.resolve(identity=Identity(tenant_id="acme", user_id="hr-2"), feedback_id="fb-2")


# --- store: unanswered questions ---------------------------------------------


def test_list_unanswered_is_tenant_scoped():
    store = InMemoryFeedbackStore()
    store.record_unanswered(
        UnansweredQuestion(
            tenant_id="acme", user_id="sarah", request_id="req-3",
            question="Do we offer sabbaticals?", model_outcome="no_info", created_at=NOW,
        )
    )
    store.record_unanswered(
        UnansweredQuestion(
            tenant_id="globex", user_id="alex", request_id="req-4",
            question="What's our WFH policy?", model_outcome="blocked", created_at=NOW,
        )
    )

    visible = store.list_unanswered(tenant_id="acme")

    assert [entry.request_id for entry in visible] == ["req-3"]


# --- store: quality summary ---------------------------------------------------


def test_quality_summary_is_aggregate_only_and_accurate():
    store = InMemoryFeedbackStore()
    store.record_feedback(make_helpful_feedback("acme", "helpful-1"))
    store.record_feedback(make_not_helpful_feedback("acme", "not-helpful-1"))
    store.record_unanswered(
        UnansweredQuestion(
            tenant_id="acme", user_id="sarah", request_id="req-5",
            question="Do we offer sabbaticals?", model_outcome="no_info", created_at=NOW,
        )
    )

    summary = store.quality_summary(tenant_id="acme")

    assert summary.total_feedback == 2
    assert summary.helpful_count == 1
    assert summary.not_helpful_count == 1
    assert summary.helpful_rate == 0.5
    assert summary.reason_code_counts == {"incomplete": 1}
    assert summary.unresolved_escalation_count == 1
    assert summary.unanswered_count == 1
    # aggregate-only: no question/answer text anywhere in the payload
    assert "question" not in summary.model_dump()
    assert "answer" not in summary.model_dump()


def test_quality_summary_with_no_feedback_has_null_helpful_rate():
    store = InMemoryFeedbackStore()

    summary = store.quality_summary(tenant_id="acme")

    assert summary.total_feedback == 0
    assert summary.helpful_rate is None


# --- JSONL persistence --------------------------------------------------------


def test_jsonl_store_persists_feedback_and_resolution(tmp_path):
    path = tmp_path / "feedback.jsonl"
    store = JsonlFeedbackStore(path)
    store.record_feedback(make_not_helpful_feedback())
    store.record_unanswered(
        UnansweredQuestion(
            tenant_id="acme", user_id="sarah", request_id="req-6",
            question="Do we offer sabbaticals?", model_outcome="no_info", created_at=NOW,
        )
    )
    store.resolve(
        identity=Identity(tenant_id="acme", user_id="hr-1"),
        feedback_id="fb-2",
        note="Added policy doc to Onyx.",
    )

    restored = JsonlFeedbackStore(path)

    feedback = restored.get_feedback(tenant_id="acme", feedback_id="fb-2")
    assert feedback.resolved is True
    assert feedback.resolution.note == "Added policy doc to Onyx."
    assert len(restored.list_unanswered(tenant_id="acme")) == 1
