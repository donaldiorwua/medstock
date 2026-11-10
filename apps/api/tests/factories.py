"""Builders for valid rows, used by the schema tests and by later milestones' tests.

Each function adds one row to the session and flushes it, so callers get its id. Override any
column with keyword arguments."""

import itertools
import uuid
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import (
    AdjustmentReason,
    DiscrepancyStatus,
    FacilityType,
    LineStatus,
    MovementType,
    RequestStatus,
    ShipmentStatus,
    StockBucket,
)
from app.core.types import utcnow
from app.models import (
    AuditRecord,
    Batch,
    Discrepancy,
    Facility,
    IdempotencyKey,
    Item,
    ReceiptLine,
    ResupplyRequest,
    ResupplyRequestLine,
    Shipment,
    ShipmentLine,
    StockBalance,
    StockMovement,
    StockThreshold,
    User,
    UserSession,
)

_numbers = itertools.count(1)


def _n() -> int:
    return next(_numbers)


def _add(session: Session, row: Any) -> Any:
    session.add(row)
    session.flush()
    return row


def make_user(session: Session, **over: Any) -> User:
    n = _n()
    values: dict[str, Any] = {
        "email": f"user{n}@example.org",
        "full_name": f"Test User {n}",
        "password_hash": "not-a-real-hash",
    }
    return _add(session, User(**{**values, **over}))


def make_facility(
    session: Session, facility_type: FacilityType = FacilityType.PHC, **over: Any
) -> Facility:
    n = _n()
    values: dict[str, Any] = {
        "code": f"fac-{n}",
        "name": f"Facility {n}",
        "facility_type": facility_type,
        "timezone": "Africa/Lagos",
    }
    return _add(session, Facility(**{**values, **over}))


def make_item(session: Session, **over: Any) -> Item:
    n = _n()
    values: dict[str, Any] = {"code": f"item-{n}", "name": f"Item {n}", "base_unit": "capsule"}
    return _add(session, Item(**{**values, **over}))


def make_batch(session: Session, item: Item, **over: Any) -> Batch:
    n = _n()
    values: dict[str, Any] = {
        "item_id": item.id,
        "batch_number": f"B-{n}",
        "batch_number_key": f"b-{n}",
        "expiry_date": date(2027, 1, 31),
    }
    return _add(session, Batch(**{**values, **over}))


def make_threshold(
    session: Session, facility: Facility, item: Item, user: User, **over: Any
) -> StockThreshold:
    values: dict[str, Any] = {
        "facility_id": facility.id,
        "item_id": item.id,
        "reorder_level": 100,
        "critical_level": 50,
        "updated_by_id": user.id,
    }
    return _add(session, StockThreshold(**{**values, **over}))


def make_balance(session: Session, facility: Facility, batch: Batch, **over: Any) -> StockBalance:
    values: dict[str, Any] = {"facility_id": facility.id, "batch_id": batch.id}
    return _add(session, StockBalance(**{**values, **over}))


def make_movement(
    session: Session, facility: Facility, batch: Batch, user: User, **over: Any
) -> StockMovement:
    values: dict[str, Any] = {
        "posting_id": uuid.uuid4(),
        "facility_id": facility.id,
        "batch_id": batch.id,
        "movement_type": MovementType.RECEIPT,
        "bucket": StockBucket.AVAILABLE,
        "quantity_delta": 10,
        "balance_after": 10,
        "occurred_on": date(2026, 11, 7),
        "created_by_id": user.id,
    }
    return _add(session, StockMovement(**{**values, **over}))


def adjustment_values() -> dict[str, Any]:
    return {"movement_type": MovementType.ADJUSTMENT, "reason": AdjustmentReason.DAMAGE}


def make_request(
    session: Session, phc: Facility, store: Facility, user: User, **over: Any
) -> ResupplyRequest:
    values: dict[str, Any] = {
        "facility_id": phc.id,
        "supplier_facility_id": store.id,
        "status": RequestStatus.DRAFT,
        "created_by_id": user.id,
    }
    return _add(session, ResupplyRequest(**{**values, **over}))


def make_line(
    session: Session, request: ResupplyRequest, item: Item, **over: Any
) -> ResupplyRequestLine:
    values: dict[str, Any] = {
        "request_id": request.id,
        "item_id": item.id,
        "qty_requested": 10,
        "status": LineStatus.PENDING,
    }
    return _add(session, ResupplyRequestLine(**{**values, **over}))


def make_shipment(
    session: Session,
    request: ResupplyRequest,
    store: Facility,
    phc: Facility,
    user: User,
    **over: Any,
) -> Shipment:
    values: dict[str, Any] = {
        "request_id": request.id,
        "from_facility_id": store.id,
        "to_facility_id": phc.id,
        "status": ShipmentStatus.IN_TRANSIT,
        "dispatched_by_id": user.id,
    }
    return _add(session, Shipment(**{**values, **over}))


def make_shipment_line(
    session: Session, shipment: Shipment, line: ResupplyRequestLine, batch: Batch, **over: Any
) -> ShipmentLine:
    values: dict[str, Any] = {
        "shipment_id": shipment.id,
        "request_line_id": line.id,
        "batch_id": batch.id,
        "qty_dispatched": 10,
    }
    return _add(session, ShipmentLine(**{**values, **over}))


def make_receipt_line(
    session: Session, shipment_line: ShipmentLine, user: User, **over: Any
) -> ReceiptLine:
    values: dict[str, Any] = {
        "shipment_line_id": shipment_line.id,
        "qty_dispatched": shipment_line.qty_dispatched,
        "qty_received": shipment_line.qty_dispatched,
        "received_by_id": user.id,
    }
    return _add(session, ReceiptLine(**{**values, **over}))


def make_discrepancy(session: Session, receipt_line: ReceiptLine, **over: Any) -> Discrepancy:
    values: dict[str, Any] = {
        "receipt_line_id": receipt_line.id,
        "qty_missing": 2,
        "status": DiscrepancyStatus.OPEN,
    }
    return _add(session, Discrepancy(**{**values, **over}))


def make_session(session: Session, user: User, **over: Any) -> UserSession:
    n = _n()
    values: dict[str, Any] = {
        "user_id": user.id,
        "token_hash": f"{n:064x}",
        "expires_at": utcnow(),
    }
    return _add(session, UserSession(**{**values, **over}))


def make_audit(session: Session, **over: Any) -> AuditRecord:
    values: dict[str, Any] = {
        "action": "test.thing.done",
        "entity_type": "thing",
        "summary": "Something happened.",
    }
    return _add(session, AuditRecord(**{**values, **over}))


def make_idempotency_key(session: Session, user: User, **over: Any) -> IdempotencyKey:
    n = _n()
    values: dict[str, Any] = {
        "user_id": user.id,
        "key": f"key-{n:016d}",
        "method": "POST",
        "path": "/api/v1/example",
        "request_hash": f"{n:064x}",
        "expires_at": utcnow(),
    }
    return _add(session, IdempotencyKey(**{**values, **over}))
