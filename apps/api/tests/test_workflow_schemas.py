"""Rules written into the request, shipment, discrepancy and operations schemas, plus the
test-only endpoints' environment rule."""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.schemas.discrepancies import ResolveDiscrepancyRequest
from app.schemas.requests import (
    CancelResupplyRequest,
    CreateResupplyRequest,
    ResupplyLineIn,
    ReviewLineIn,
    ReviewResupplyRequest,
    SubmitResupplyRequest,
    UpdateResupplyRequest,
)
from app.schemas.shipments import (
    AllocationIn,
    ConfirmReceiptRequest,
    DispatchLineIn,
    DispatchRequest,
    ReceiptLineIn,
)

PHC = uuid4()
ITEM_A, ITEM_B = uuid4(), uuid4()
LINE_A, LINE_B = uuid4(), uuid4()
BATCH_A, BATCH_B = uuid4(), uuid4()
KEY = "6f1d2c3b-4a59-4e8f-9b7a-0c1d2e3f4a5b"


# ------------------------------------------------------------------ requests


def test_a_new_request_needs_lines_with_distinct_items_and_whole_quantities() -> None:
    CreateResupplyRequest(facility_id=PHC, lines=[ResupplyLineIn(item_id=ITEM_A, qty_requested=50)])
    with pytest.raises(ValidationError):
        CreateResupplyRequest(facility_id=PHC, lines=[])
    twice = [ResupplyLineIn(item_id=ITEM_A, qty_requested=1)] * 2
    with pytest.raises(ValidationError, match="only once"):
        CreateResupplyRequest(facility_id=PHC, lines=twice)
    for bad in (0, -1, 2.5, "10"):
        with pytest.raises(ValidationError):
            ResupplyLineIn(item_id=ITEM_A, qty_requested=bad)


def test_editing_a_draft_needs_a_version_and_a_change() -> None:
    lines = [ResupplyLineIn(item_id=ITEM_A, qty_requested=5)]
    assert UpdateResupplyRequest(version=1, lines=lines).lines == lines
    assert UpdateResupplyRequest(version=1, note="Urgent").note == "Urgent"
    with pytest.raises(ValidationError, match="at least one field"):
        UpdateResupplyRequest(version=1)
    with pytest.raises(ValidationError):
        UpdateResupplyRequest(note="Urgent")  # type: ignore[call-arg]


@pytest.mark.parametrize("bad", [0, -1, "3", 2.0, True, None])
def test_versions_are_strict_positive_integers(bad: object) -> None:
    with pytest.raises(ValidationError):
        SubmitResupplyRequest(version=bad)
    with pytest.raises(ValidationError):
        CancelResupplyRequest(version=bad)


def test_review_decides_every_line_once_and_zero_means_reject() -> None:
    decided = [
        ReviewLineIn(line_id=LINE_A, qty_approved=40),
        ReviewLineIn(line_id=LINE_B, qty_approved=0),
    ]
    assert ReviewResupplyRequest(version=3, lines=decided).lines == decided
    with pytest.raises(ValidationError):
        ReviewResupplyRequest(version=3, lines=[])
    with pytest.raises(ValidationError, match="only once"):
        ReviewResupplyRequest(version=3, lines=[decided[0], decided[0]])
    with pytest.raises(ValidationError):
        ReviewLineIn(line_id=LINE_A, qty_approved=-1)


# ------------------------------------------------------------------ shipments


def test_dispatch_lists_each_line_and_each_batch_once() -> None:
    line = DispatchLineIn(
        line_id=LINE_A,
        allocations=[
            AllocationIn(batch_id=BATCH_A, quantity=15),
            AllocationIn(batch_id=BATCH_B, quantity=25),
        ],
    )
    assert DispatchRequest(version=4, lines=[line]).lines == [line]
    with pytest.raises(ValidationError):
        DispatchLineIn(line_id=LINE_A, allocations=[])
    with pytest.raises(ValidationError, match="only once"):
        DispatchLineIn(
            line_id=LINE_A,
            allocations=[
                AllocationIn(batch_id=BATCH_A, quantity=1),
                AllocationIn(batch_id=BATCH_A, quantity=2),
            ],
        )
    with pytest.raises(ValidationError, match="only once"):
        DispatchRequest(version=4, lines=[line, line])
    with pytest.raises(ValidationError):
        AllocationIn(batch_id=BATCH_A, quantity=0)


def test_receipt_counts_every_line_once_and_allows_zero() -> None:
    counted = [
        ReceiptLineIn(shipment_line_id=LINE_A, qty_received=15),
        ReceiptLineIn(shipment_line_id=LINE_B, qty_received=0),
    ]
    assert ConfirmReceiptRequest(version=1, lines=counted).lines == counted
    with pytest.raises(ValidationError):
        ConfirmReceiptRequest(version=1, lines=[])
    with pytest.raises(ValidationError, match="only once"):
        ConfirmReceiptRequest(version=1, lines=[counted[0], counted[0]])
    with pytest.raises(ValidationError):
        ReceiptLineIn(shipment_line_id=LINE_A, qty_received=-1)
    with pytest.raises(ValidationError):
        ReceiptLineIn(shipment_line_id=LINE_A, qty_received=1.5)


# ------------------------------------------------------------------ discrepancies


def test_a_discrepancy_is_resolved_one_of_three_ways() -> None:
    for resolution in ("written_off", "recovered_to_phc", "recovered_to_store"):
        assert ResolveDiscrepancyRequest(version=1, resolution=resolution).resolution == resolution
    with pytest.raises(ValidationError):
        ResolveDiscrepancyRequest(version=1, resolution="ignored")
    with pytest.raises(ValidationError):
        ResolveDiscrepancyRequest(version=1)  # type: ignore[call-arg]


# ------------------------------------------------------------------ over HTTP


def test_actions_without_a_key_are_rejected(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/requests/{uuid4()}/dispatch",
        json={
            "version": 4,
            "lines": [
                {"line_id": str(LINE_A), "allocations": [{"batch_id": str(BATCH_A), "quantity": 5}]}
            ],
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_a_stale_looking_version_is_validated_before_the_handler(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/requests/{uuid4()}/submit",
        json={"version": "3"},
        headers={"Idempotency-Key": KEY},
    )
    assert response.status_code == 422
    assert [d["path"] for d in response.json()["error"]["details"]] == ["version"]


def test_unknown_export_resources_and_alert_types_are_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/exports/people.csv").status_code == 422
    assert client.get("/api/v1/exports/stock.csv").status_code == 501
    assert client.get("/api/v1/dashboard/alerts?type=volcano").status_code == 422
    assert client.get("/api/v1/dashboard/alerts?type=expiring_soon").status_code == 501


# ------------------------------------------------------------------ test-only endpoints


def _client(tmp_path: Path, app_env: str) -> TestClient:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None, app_env=app_env, database_url=f"sqlite:///{tmp_path / 'x.db'}"
    )
    return TestClient(create_app(settings), raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("app_env", "expected"), [("development", 404), ("test", 501), ("e2e", 501)]
)
def test_the_test_endpoints_exist_only_in_test_and_e2e(
    tmp_path: Path, app_env: str, expected: int
) -> None:
    with _client(tmp_path, app_env) as client:
        assert client.post("/api/v1/test/reset").status_code == expected
        assert client.post("/api/v1/test/seed", json={"profile": "e2e"}).status_code == expected


def test_seed_profile_must_be_known(client: TestClient) -> None:
    assert client.post("/api/v1/test/seed", json={"profile": "production"}).status_code == 422
