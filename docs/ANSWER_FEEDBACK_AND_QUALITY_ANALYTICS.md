# Answer feedback, unanswered questions, and quality analytics

Employees rate individual answers, negative ratings escalate to HR
automatically, uncovered topics are logged even when no one leaves
feedback, and HR gets an aggregate-only quality dashboard -- without any of
this exposing question/answer content beyond the two surfaces that are
explicitly authorized to see it.

## Correlating feedback to an answer

`POST /v1/questions` already returns `request_id` in `QuestionResponse` (the
same ID bound per-request by `glue.resilience.bind_request_id` and echoed in
the `X-Request-ID` response header). A client submits feedback against that
ID rather than a second, separately-minted identifier for the same
interaction:

```
POST /v1/questions/{request_id}/feedback
{"question": "...", "answer": "...", "helpful": false, "reason_code": "incomplete"}
```

`helpful` and `reason_code` are mutually exclusive in one direction: helpful
feedback must not carry a reason code, and not-helpful feedback must carry
one of `incorrect`, `incomplete`, `irrelevant`, `outdated`, `other`. This
endpoint requires only a signed identity -- an employee escalating their own
not-helpful rating is not an HR action and needs no HR authorization.

## Automatic escalation, explicit resolution

Not-helpful feedback is escalated (`escalated: true`) the moment it is
submitted -- no separate "escalate" step. An authorized HR reviewer resolves
it explicitly:

```
POST /v1/hr/feedback/{feedback_id}/resolve
{"note": "Added the missing policy doc to Onyx."}
```

Only escalated feedback can be resolved; resolving twice by the same
reviewer is idempotent, resolving already-resolved feedback by a different
reviewer is a conflict -- the same immutable-decision pattern
`docs/SUGGESTION_REVIEW_INBOX.md` uses for suggestions.

## Unanswered questions, logged automatically

`glue.pipeline.Pipeline` records an `UnansweredQuestion` itself, once, in the
same `finally` block that already emits the audit event and metrics --
whenever a question's `model_outcome` is not `"answered"` (`no_info`,
`blocked`, or `error`). No employee action is required; this is how HR sees
uncovered topics that nobody bothered to rate.

## Authorization and tenant isolation

`GET /v1/hr/feedback`, `GET /v1/hr/feedback/unanswered`,
`GET /v1/hr/feedback/quality-summary`, and the resolve endpoint all verify
the signed bearer token into `Identity(tenant_id, user_id)`, then authorize
that identity against a tenant-scoped static reviewer map -- the same shape
as the suggestion inbox's, kept as its own variable
(`HR_FEEDBACK_REVIEWERS_JSON`) so the two reviewer sets can differ:

```json
{"acme": ["hr-1", "hr-2"]}
```

## API

- `POST /v1/questions/{request_id}/feedback` -- submit feedback (self-service)
- `GET /v1/hr/feedback?helpful=false&escalated_only=true` -- list feedback
- `GET /v1/hr/feedback/unanswered` -- list unanswered questions
- `POST /v1/hr/feedback/{feedback_id}/resolve` -- resolve an escalation
- `GET /v1/hr/feedback/quality-summary` -- aggregate-only dashboard

The quality-summary response is deliberately counts/rates only
(`total_feedback`, `helpful_count`, `not_helpful_count`, `helpful_rate`,
`reason_code_counts`, `unresolved_escalation_count`, `unanswered_count`) --
no question or answer text, so it is safe to render on a dashboard without
exposing the sensitive content of individual interactions.

## Persistence

`FEEDBACK_STORE_PATH` controls the append-only JSONL state file and defaults
to `.tmp/feedback.jsonl`. `HR_FEEDBACK_REVIEWERS_JSON` controls the
tenant-scoped reviewer map and defaults to `{}`, which means no user can
access the feedback/quality surface until reviewers are explicitly
provisioned.

The feedback store is application state, not an audit log, same as the
suggestion store -- existing audit and observability surfaces continue to
avoid raw questions, document chunks, and user identifiers beyond the
established privacy-preserving fields.
