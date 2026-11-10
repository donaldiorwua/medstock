"""Rules written into the stock request schemas, and the Idempotency-Key behaviour."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.stock import (
    AdjustmentRequest,
    ExpiryWriteOffRequest,
    IssueRequest,
    OpeningStockRequest,
    QuarantineRequest,
    ReceiptRequest,
    ReleaseRequest,
    ReversalRequest,
)

BATCH = uuid4()
FACILITY = uuid4()
KEY = "6f1d2c3b-4a59-4e8f-9b7a-0c1d2e3f4a5b"


@pytest.mark.parametrize("request_class", [ReceiptRequest, IssueRequest, ReleaseRequest])
@pytest.mark.parametrize("bad", [0, -5, 1_000_000_001, 5.0, "5", True, None])
def test_quantities_must_be_whole_positive_numbers(request_class: type, bad: object) -> None:
    with pytest.raises(ValidationError):
        request_class(batch_id=BATCH, quantity=bad)


def test_a_normal_quantity_is_accepted() -> None:
    assert IssueRequest(batch_id=BATCH, quantity=60).quantity == 60


def test_dates_default_to_none_and_must_be_real_dates() -> None:
    assert IssueRequest(batch_id=BATCH, quantity=1).occurred_on is None
    assert IssueRequest(batch_id=BATCH, quantity=1, occurred_on="2026-11-07").occurred_on
    with pytest.raises(ValidationError):
        IssueRequest(batch_id=BATCH, quantity=1, occurred_on="07/11/2026")


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="surprise"):
        IssueRequest(batch_id=BATCH, quantity=1, surprise=1)  # type: ignore[call-arg]


def test_opening_stock_needs_a_sign_off_name() -> None:
    OpeningStockRequest(batch_id=BATCH, quantity=10, signed_off_by="Ngozi Okafor")
    with pytest.raises(ValidationError):
        OpeningStockRequest(batch_id=BATCH, quantity=10)
    with pytest.raises(ValidationError):
        OpeningStockRequest(batch_id=BATCH, quantity=10, signed_off_by="  ")


def test_adjustments_are_signed_nonzero_and_need_a_reason() -> None:
    removed = AdjustmentRequest(batch_id=BATCH, quantity_delta=-5, reason="damage")
    assert removed.quantity_delta == -5
    assert AdjustmentRequest(batch_id=BATCH, quantity_delta=5, reason="found").quantity_delta == 5
    with pytest.raises(ValidationError, match="must not be zero"):
        AdjustmentRequest(batch_id=BATCH, quantity_delta=0, reason="damage")
    with pytest.raises(ValidationError):
        AdjustmentRequest(batch_id=BATCH, quantity_delta=-5)
    with pytest.raises(ValidationError):
        AdjustmentRequest(batch_id=BATCH, quantity_delta=-5, reason="because")


def test_reason_other_requires_a_note() -> None:
    with pytest.raises(ValidationError, match="note is required"):
        AdjustmentRequest(batch_id=BATCH, quantity_delta=-5, reason="other")
    ok = AdjustmentRequest(batch_id=BATCH, quantity_delta=-5, reason="other", note="Spilled")
    assert ok.note == "Spilled"


def test_quarantine_and_reversal_need_a_reason_in_words() -> None:
    QuarantineRequest(batch_id=BATCH, quantity=5, note="Recall")
    with pytest.raises(ValidationError):
        QuarantineRequest(batch_id=BATCH, quantity=5)
    ReversalRequest(note="Wrong batch")
    with pytest.raises(ValidationError):
        ReversalRequest()
    with pytest.raises(ValidationError):
        ReversalRequest(note="   ")


def test_expiry_writeoff_defaults_to_the_available_balance() -> None:
    assert ExpiryWriteOffRequest(batch_id=BATCH, quantity=3).bucket == "available"
    assert ExpiryWriteOffRequest(batch_id=BATCH, quantity=3, bucket="quarantined").bucket == (
        "quarantined"
    )
    with pytest.raises(ValidationError):
        ExpiryWriteOffRequest(batch_id=BATCH, quantity=3, bucket="elsewhere")


def test_note_is_trimmed_and_length_limited() -> None:
    assert IssueRequest(batch_id=BATCH, quantity=1, note="  hello ").note == "hello"
    with pytest.raises(ValidationError):
        IssueRequest(batch_id=BATCH, quantity=1, note="x" * 501)


# ------------------------------------------------ over HTTP (stubs answer after validation)

URL = f"/api/v1/facilities/{FACILITY}/stock/issues"
BODY = {"batch_id": str(BATCH), "quantity": 5}


def test_posting_without_a_key_is_rejected_with_its_own_error_code(client: TestClient) -> None:
    response = client.post(URL, json=BODY)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_posting_with_a_key_passes_validation(client: TestClient) -> None:
    response = client.post(URL, json=BODY, headers={"Idempotency-Key": KEY})
    assert response.status_code == 501  # stub: the request was accepted


def test_a_bad_body_is_reported_by_path(client: TestClient) -> None:
    response = client.post(
        URL, json={"batch_id": str(BATCH), "quantity": 5.5}, headers={"Idempotency-Key": KEY}
    )
    assert response.status_code == 422
    paths = [d["path"] for d in response.json()["error"]["details"]]
    assert paths == ["quantity"]


def test_reads_do_not_need_a_key(client: TestClient) -> None:
    assert client.get(f"/api/v1/facilities/{FACILITY}/stock").status_code == 501
