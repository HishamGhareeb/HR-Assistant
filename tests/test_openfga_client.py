"""Unit tests for the OpenFGA authorization filter: tenant scoping,
batch-check usage (bounded fan-out), and fail-closed behavior on both
per-item and whole-batch failures.

No live OpenFGA instance is used -- `OpenFgaFilter._open_client` is
overridden with a fake async context manager wrapping a fake `batch_check`,
so these exercise the real filtering/scoping logic without a network call.
"""
from __future__ import annotations

import pytest

from glue.onyx_client import Document
from glue.domain import DocumentClassification
from glue.openfga_client import OpenFgaFilter, scoped_object_id, tenant_object_id


class FakeSingleResponse:
    def __init__(self, correlation_id: str, allowed: bool) -> None:
        self.correlation_id = correlation_id
        self.allowed = allowed


class FakeBatchResponse:
    def __init__(self, result) -> None:
        self.result = result


class FakeOpenFgaClient:
    """Records the batch_check call it received and returns a canned
    response; also usable as an async context manager like the real
    OpenFgaClient."""

    def __init__(self, response=None, exception: Exception | None = None) -> None:
        self._response = response if response is not None else FakeBatchResponse([])
        self._exception = exception
        self.calls: list[tuple] = []

    async def __aenter__(self) -> "FakeOpenFgaClient":
        return self

    async def __aexit__(self, *exc_info) -> None:
        return None

    async def batch_check(self, body, options=None):
        self.calls.append((body, options))
        if self._exception is not None:
            raise self._exception
        return self._response


def make_filter(fake_client: FakeOpenFgaClient) -> OpenFgaFilter:
    filter_ = OpenFgaFilter(api_url="https://fga.internal", store_id="store-1")
    filter_._open_client = lambda: fake_client  # type: ignore[method-assign]
    return filter_


def doc(object_id="sarah_leave", object_type="leave_record", tenant_id="acme") -> Document:
    return Document(object_type=object_type, object_id=object_id, chunk="chunk", tenant_id=tenant_id)


# --- scoped_object_id --------------------------------------------------


def test_scoped_object_id_namespaces_by_tenant():
    assert scoped_object_id("leave_record", "acme", "sarah_leave") == "leave_record:acme__sarah_leave"


def test_scoped_object_id_keeps_different_tenants_distinct():
    a = scoped_object_id("leave_record", "acme", "sarah_leave")
    b = scoped_object_id("leave_record", "globex", "sarah_leave")
    assert a != b


def test_tenant_object_id_is_tenant_scoped_role_object():
    assert tenant_object_id("acme") == "tenant:acme"


# --- tenant dropping (never reaches OpenFGA) ----------------------------


@pytest.mark.asyncio
async def test_document_without_tenant_id_is_dropped_before_check():
    fake = FakeOpenFgaClient(FakeBatchResponse([FakeSingleResponse("0", True)]))
    filter_ = make_filter(fake)

    tenantless = Document(object_type="leave_record", object_id="x", chunk="c", tenant_id=None)
    result = await filter_.filter_authorized("sarah", [tenantless])

    assert result == []
    assert fake.calls == []  # never even called OpenFGA


@pytest.mark.asyncio
async def test_document_from_a_different_tenant_is_dropped_before_check():
    fake = FakeOpenFgaClient(FakeBatchResponse([FakeSingleResponse("0", True)]))
    filter_ = make_filter(fake)

    foreign = doc(tenant_id="globex")
    result = await filter_.filter_authorized("sarah", [foreign], tenant_id="acme")

    assert result == []
    assert fake.calls == []


@pytest.mark.asyncio
async def test_no_documents_short_circuits_without_calling_openfga():
    fake = FakeOpenFgaClient()
    filter_ = make_filter(fake)

    result = await filter_.filter_authorized("sarah", [])

    assert result == []
    assert fake.calls == []


# --- batch_check usage (bounded fan-out) --------------------------------


@pytest.mark.asyncio
async def test_uses_batch_check_with_tenant_scoped_object_and_default_bounds():
    fake = FakeOpenFgaClient(FakeBatchResponse([FakeSingleResponse("0", True)]))
    filter_ = make_filter(fake)

    await filter_.filter_authorized("sarah", [doc()], tenant_id="acme")

    assert len(fake.calls) == 1
    body, options = fake.calls[0]
    assert len(body.checks) == 1
    check = body.checks[0]
    assert check.user == "user:sarah"
    assert check.relation == "viewer"
    assert check.object == "leave_record:acme__sarah_leave"
    assert options == {"max_parallel_requests": 10, "max_batch_size": 50}


@pytest.mark.asyncio
async def test_custom_bounds_are_passed_through_as_batch_options():
    fake = FakeOpenFgaClient(FakeBatchResponse([FakeSingleResponse("0", True)]))
    filter_ = OpenFgaFilter(
        api_url="https://fga.internal",
        store_id="store-1",
        max_parallel_requests=3,
        max_batch_size=10,
    )
    filter_._open_client = lambda: fake  # type: ignore[method-assign]

    await filter_.filter_authorized("sarah", [doc()], tenant_id="acme")

    _, options = fake.calls[0]
    assert options == {"max_parallel_requests": 3, "max_batch_size": 10}


@pytest.mark.asyncio
async def test_a_single_call_covers_many_documents():
    fake = FakeOpenFgaClient(
        FakeBatchResponse([FakeSingleResponse(str(i), True) for i in range(25)])
    )
    filter_ = make_filter(fake)
    documents = [doc(object_id=f"leave-{i}") for i in range(25)]

    result = await filter_.filter_authorized("sarah", documents, tenant_id="acme")

    assert len(fake.calls) == 1  # one batch_check call, not 25 individual checks
    assert len(result) == 25


# --- result mapping -------------------------------------------------------


@pytest.mark.asyncio
async def test_keeps_only_allowed_documents_in_original_order():
    documents = [doc(object_id="a"), doc(object_id="b"), doc(object_id="c")]
    fake = FakeOpenFgaClient(
        FakeBatchResponse(
            [
                FakeSingleResponse("0", True),
                FakeSingleResponse("1", False),
                FakeSingleResponse("2", True),
            ]
        )
    )
    filter_ = make_filter(fake)

    result = await filter_.filter_authorized("sarah", documents, tenant_id="acme")

    assert [d.object_id for d in result] == ["a", "c"]


# --- fail-closed ------------------------------------------------------------


@pytest.mark.asyncio
async def test_whole_batch_failure_denies_everything():
    fake = FakeOpenFgaClient(exception=ConnectionError("openfga unreachable"))
    filter_ = make_filter(fake)

    result = await filter_.filter_authorized("sarah", [doc(), doc(object_id="other")], tenant_id="acme")

    assert result == []


@pytest.mark.asyncio
async def test_item_not_present_in_response_is_treated_as_denied():
    # Simulates a per-item error the SDK already turned into allowed=False
    # by omitting it from an "allowed" set -- filter_authorized must not
    # default a missing correlation_id to allowed.
    fake = FakeOpenFgaClient(FakeBatchResponse([]))
    filter_ = make_filter(fake)

    result = await filter_.filter_authorized("sarah", [doc()], tenant_id="acme")

    assert result == []


# --- pre-retrieval classification mask ------------------------------------


@pytest.mark.asyncio
async def test_employee_role_gets_tenant_public_and_internal_classifications():
    fake = FakeOpenFgaClient(FakeBatchResponse([FakeSingleResponse("employee", True)]))
    filter_ = make_filter(fake)

    result = await filter_.allowed_classifications("sarah", "acme")

    assert result == (DocumentClassification.PUBLIC, DocumentClassification.INTERNAL)
    body, _options = fake.calls[0]
    assert {check.relation for check in body.checks} == {"employee", "manager", "hr_admin", "system_admin"}
    assert {check.object for check in body.checks} == {"tenant:acme"}


@pytest.mark.asyncio
async def test_manager_role_gets_manager_only_without_hr_only():
    fake = FakeOpenFgaClient(FakeBatchResponse([FakeSingleResponse("manager", True)]))
    filter_ = make_filter(fake)

    result = await filter_.allowed_classifications("manager-1", "acme")

    assert result == (
        DocumentClassification.PUBLIC,
        DocumentClassification.INTERNAL,
        DocumentClassification.MANAGER_ONLY,
    )


@pytest.mark.asyncio
async def test_hr_admin_role_gets_hr_only_and_manager_classes():
    fake = FakeOpenFgaClient(FakeBatchResponse([FakeSingleResponse("hr_admin", True)]))
    filter_ = make_filter(fake)

    result = await filter_.allowed_classifications("hr-1", "acme")

    assert result == (
        DocumentClassification.PUBLIC,
        DocumentClassification.INTERNAL,
        DocumentClassification.MANAGER_ONLY,
        DocumentClassification.HR_ONLY,
    )


@pytest.mark.asyncio
async def test_pre_retrieval_fga_failure_denies_all_classifications():
    fake = FakeOpenFgaClient(exception=ConnectionError("openfga down"))
    filter_ = make_filter(fake)

    result = await filter_.allowed_classifications("sarah", "acme")

    assert result == ()
