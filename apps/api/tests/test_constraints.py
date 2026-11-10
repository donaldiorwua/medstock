"""Every rule the database enforces by itself, broken on purpose (blueprint scenario 6).

Each case builds rows that should be impossible and expects the database to refuse them.
The error text is checked for the constraint's name (or the engine's wording for it) so a
case cannot pass because of some other, unrelated error."""

import uuid
from collections.abc import Callable
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.db import Database
from app.core.enums import (
    DiscrepancyResolution,
    DiscrepancyStatus,
    MovementType,
    Role,
)
from app.core.types import utcnow
from app.models import AuditRecord, UserFacilityRole
from tests import factories as f_

Builder = Callable[..., None]
CASES: list[tuple[str, Builder, tuple[str, ...]]] = []


def case(case_id: str, *needles: str) -> Callable[[Builder], Builder]:
    """Register a builder taking (session, world, flow) that must be rejected."""

    def register(builder: Builder) -> Builder:
        CASES.append((case_id, builder, needles))
        return builder

    return register


FK = ("FOREIGN KEY", "foreign key constraint")


# ------------------------------------------------------------------ identity


@case("user-email-upper-case", "ck_users_email_lowercase")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_user(s, email="Mixed@Example.org")


@case("user-duplicate-email", "uq_users_email", "users.email")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_user(s, email=w.user.email)


@case("user-negative-failed-logins", "ck_users_failed_login_count_nonneg")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_user(s, failed_login_count=-1)


@case("facility-code-upper-case", "ck_facilities_code_lowercase")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_facility(s, code="PHC-UPPER")


@case("facility-duplicate-code", "uq_facilities_code", "facilities.code")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_facility(s, code=w.phc.code)


@case("role-second-role-at-same-facility", "pk_user_facility_roles", "user_facility_roles.user_id")
def _(s, w, f):  # type: ignore[no-untyped-def]
    s.add(UserFacilityRole(user_id=w.user.id, facility_id=w.phc.id, role=Role.VIEWER))


@case("role-unknown-user", *FK)
def _(s, w, f):  # type: ignore[no-untyped-def]
    s.add(UserFacilityRole(user_id=uuid.uuid4(), facility_id=w.phc.id, role=Role.VIEWER))


@case("session-duplicate-token", "uq_sessions_token_hash", "sessions.token_hash")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_session(s, w.user, token_hash="a" * 64)
    f_.make_session(s, w.user, token_hash="a" * 64)


# ------------------------------------------------------------------ catalogue


@case("item-code-upper-case", "ck_items_code_lowercase")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_item(s, code="AMOX-250")


@case("batch-duplicate-number-for-item", "uq_batches_item_batch_number", "batches.item_id")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_batch(s, w.item, batch_number="X-1", batch_number_key="x-1")
    f_.make_batch(s, w.item, batch_number="x-1", batch_number_key="x-1")


@case("batch-key-does-not-match-number", "ck_batches_batch_key_matches")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_batch(s, w.item, batch_number="ABC", batch_number_key="xyz")


@case("batch-unknown-item", *FK)
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_batch(s, SimpleNamespace(id=uuid.uuid4()))


@case("threshold-reorder-below-critical", "ck_stock_thresholds_reorder_not_below_critical")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_threshold(s, w.phc, w.item, w.user, reorder_level=10, critical_level=20)


@case("threshold-negative-critical", "ck_stock_thresholds_critical_nonneg")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_threshold(s, w.phc, w.item, w.user, reorder_level=5, critical_level=-1)


# ------------------------------------------------------------------ stock


@case("balance-negative-available", "ck_stock_balances_qty_available_nonneg")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_balance(s, w.phc, w.batch, qty_available=-1)


@case("balance-negative-quarantined", "ck_stock_balances_qty_quarantined_nonneg")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_balance(s, w.phc, w.batch, qty_quarantined=-1)


@case("movement-zero-delta", "ck_stock_movements_delta_nonzero")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_movement(s, w.phc, w.batch, w.user, quantity_delta=0)


@case("movement-negative-balance-after", "ck_stock_movements_balance_after_nonneg")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_movement(s, w.phc, w.batch, w.user, balance_after=-1)


@case("adjustment-without-reason", "ck_stock_movements_adjustment_has_reason")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_movement(s, w.phc, w.batch, w.user, movement_type=MovementType.ADJUSTMENT)


@case("opening-without-sign-off", "ck_stock_movements_opening_signed_off")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_movement(s, w.phc, w.batch, w.user, movement_type=MovementType.OPENING)


@case("reversal-without-target", "ck_stock_movements_reversal_has_target")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_movement(s, w.phc, w.batch, w.user, movement_type=MovementType.REVERSAL)


@case("non-reversal-with-target", "ck_stock_movements_only_reversals_have_target")
def _(s, w, f):  # type: ignore[no-untyped-def]
    original = f_.make_movement(s, w.phc, w.batch, w.user)
    f_.make_movement(s, w.phc, w.batch, w.user, reverses_movement_id=original.id)


@case(
    "movement-reversed-twice",
    "uq_stock_movements_reverses_movement_id",
    "stock_movements.reverses_movement_id",
)
def _(s, w, f):  # type: ignore[no-untyped-def]
    original = f_.make_movement(s, w.phc, w.batch, w.user)
    reversal = {
        "movement_type": MovementType.REVERSAL,
        "reverses_movement_id": original.id,
        "quantity_delta": -10,
        "balance_after": 0,
    }
    f_.make_movement(s, w.phc, w.batch, w.user, **reversal)
    f_.make_movement(s, w.phc, w.batch, w.user, **reversal)


@case("opening-recorded-twice", "uq_stock_movements_opening", "stock_movements.facility_id")
def _(s, w, f):  # type: ignore[no-untyped-def]
    opening = {"movement_type": MovementType.OPENING, "signed_off_by": "Ngozi Okafor"}
    f_.make_movement(s, w.phc, w.batch, w.user, **opening)
    f_.make_movement(s, w.phc, w.batch, w.user, **opening)


@case("movement-unknown-batch", *FK)
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_movement(s, w.phc, SimpleNamespace(id=uuid.uuid4()), w.user)


@case("movement-unknown-shipment-line", *FK)
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_movement(s, w.phc, w.batch, w.user, shipment_line_id=uuid.uuid4())


# ------------------------------------------------------------------ requests and shipments


@case("request-from-its-own-supplier", "ck_resupply_requests_requester_not_supplier")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_request(s, w.phc, w.phc, w.user)


@case("request-version-zero", "ck_resupply_requests_version_positive")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_request(s, w.phc, w.store, w.user, version=0)


@case("line-approved-above-requested", "ck_resupply_request_lines_approved_within_requested")
def _(s, w, f):  # type: ignore[no-untyped-def]
    request = f_.make_request(s, w.phc, w.store, w.user)
    f_.make_line(s, request, w.item, qty_requested=5, qty_approved=6)


@case("line-zero-requested", "ck_resupply_request_lines_qty_requested_positive")
def _(s, w, f):  # type: ignore[no-untyped-def]
    request = f_.make_request(s, w.phc, w.store, w.user)
    f_.make_line(s, request, w.item, qty_requested=0)


@case("line-negative-approved", "ck_resupply_request_lines_qty_approved_nonneg")
def _(s, w, f):  # type: ignore[no-untyped-def]
    request = f_.make_request(s, w.phc, w.store, w.user)
    f_.make_line(s, request, w.item, qty_requested=5, qty_approved=-1)


@case(
    "line-same-item-twice",
    "uq_resupply_request_lines_request_item",
    "resupply_request_lines.request_id",
)
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_line(s, f.request, w.item)


@case("second-shipment-for-a-request", "uq_shipments_request_id", "shipments.request_id")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_shipment(s, f.request, w.store, w.phc, w.user)


@case("shipment-to-its-own-origin", "ck_shipments_distinct_facilities")
def _(s, w, f):  # type: ignore[no-untyped-def]
    request = f_.make_request(s, w.phc, w.store, w.user)
    f_.make_shipment(s, request, w.phc, w.phc, w.user)


@case("shipment-line-zero-quantity", "ck_shipment_lines_qty_dispatched_positive")
def _(s, w, f):  # type: ignore[no-untyped-def]
    other_batch = f_.make_batch(s, w.item)
    f_.make_shipment_line(s, f.shipment, f.line, other_batch, qty_dispatched=0)


@case(
    "shipment-line-same-batch-twice", "uq_shipment_lines_line_batch", "shipment_lines.shipment_id"
)
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_shipment_line(s, f.shipment, f.line, w.batch)


@case("receipt-more-than-dispatched", "ck_receipt_lines_received_within_dispatched")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_receipt_line(s, f.shipment_line, w.user, qty_received=11)


@case("receipt-negative", "ck_receipt_lines_qty_received_nonneg")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_receipt_line(s, f.shipment_line, w.user, qty_received=-1)


@case("receipt-with-a-wrong-dispatched-copy", "fk_receipt_lines_shipment_line_qty", *FK)
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_receipt_line(s, f.shipment_line, w.user, qty_dispatched=9, qty_received=5)


@case(
    "receipt-counted-twice", "uq_receipt_lines_shipment_line_id", "receipt_lines.shipment_line_id"
)
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_receipt_line(s, f.shipment_line, w.user)
    f_.make_receipt_line(s, f.shipment_line, w.user)


# ------------------------------------------------------------------ discrepancies


@case("discrepancy-open-but-has-a-resolution", "ck_discrepancies_state_consistent")
def _(s, w, f):  # type: ignore[no-untyped-def]
    receipt = f_.make_receipt_line(s, f.shipment_line, w.user, qty_received=8)
    f_.make_discrepancy(s, receipt, resolution=DiscrepancyResolution.WRITTEN_OFF)


@case("discrepancy-resolved-without-resolver", "ck_discrepancies_state_consistent")
def _(s, w, f):  # type: ignore[no-untyped-def]
    receipt = f_.make_receipt_line(s, f.shipment_line, w.user, qty_received=8)
    f_.make_discrepancy(
        s,
        receipt,
        status=DiscrepancyStatus.RESOLVED,
        resolution=DiscrepancyResolution.WRITTEN_OFF,
        resolved_at=utcnow(),
    )


@case("discrepancy-nothing-missing", "ck_discrepancies_qty_missing_positive")
def _(s, w, f):  # type: ignore[no-untyped-def]
    receipt = f_.make_receipt_line(s, f.shipment_line, w.user, qty_received=8)
    f_.make_discrepancy(s, receipt, qty_missing=0)


@case(
    "discrepancy-twice-for-one-receipt",
    "uq_discrepancies_receipt_line_id",
    "discrepancies.receipt_line_id",
)
def _(s, w, f):  # type: ignore[no-untyped-def]
    receipt = f_.make_receipt_line(s, f.shipment_line, w.user, qty_received=8)
    f_.make_discrepancy(s, receipt)
    f_.make_discrepancy(s, receipt)


# ------------------------------------------------------------------ audit and idempotency


@case(
    "idempotency-key-reused-by-the-same-user",
    "uq_idempotency_keys_user_id_key",
    "idempotency_keys.user_id",
)
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_idempotency_key(s, w.user, key="same-key-0000000001")
    f_.make_idempotency_key(s, w.user, key="same-key-0000000001")


@case("idempotency-status-without-body", "ck_idempotency_keys_response_complete_or_pending")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_idempotency_key(s, w.user, response_status=201)


@case("idempotency-body-without-status", "ck_idempotency_keys_response_complete_or_pending")
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_idempotency_key(s, w.user, response_body={"data": {}})


@case("audit-unknown-actor", *FK)
def _(s, w, f):  # type: ignore[no-untyped-def]
    f_.make_audit(s, actor_id=uuid.uuid4())


@pytest.mark.parametrize(
    ("build", "needles"),
    [(build, needles) for _, build, needles in CASES],
    ids=[case_id for case_id, _, _ in CASES],
)
def test_the_database_refuses(
    migrated: Database,
    world: SimpleNamespace,
    flow: SimpleNamespace,
    build: Builder,
    needles: tuple[str, ...],
) -> None:
    with pytest.raises(IntegrityError) as caught, migrated.unit_of_work(write=True) as session:
        build(session, world, flow)
        session.flush()
    message = str(caught.value)
    assert any(needle in message for needle in needles), message


# ----------------- the rules still allow valid data


def test_valid_rows_are_accepted(
    migrated: Database, world: SimpleNamespace, flow: SimpleNamespace
) -> None:
    with migrated.unit_of_work(write=True) as s:
        # Receipts are not limited to one per batch; only openings are.
        f_.make_movement(s, world.phc, world.batch, world.user)
        f_.make_movement(s, world.phc, world.batch, world.user, balance_after=20)
        f_.make_movement(
            s,
            world.phc,
            world.batch,
            world.user,
            movement_type=MovementType.OPENING,
            signed_off_by="Ngozi Okafor",
        )
        # The same batch number may exist on another item.
        other_item = f_.make_item(s)
        f_.make_batch(s, other_item, batch_number="B-SAME", batch_number_key="b-same")
        f_.make_batch(s, world.item, batch_number="B-SAME", batch_number_key="b-same")
        # A short receipt with a resolved discrepancy.
        receipt = f_.make_receipt_line(s, flow.shipment_line, world.user, qty_received=8)
        f_.make_discrepancy(
            s,
            receipt,
            status=DiscrepancyStatus.RESOLVED,
            resolution=DiscrepancyResolution.RECOVERED_TO_PHC,
            resolved_at=utcnow(),
            resolved_by_id=world.user.id,
        )
        f_.make_idempotency_key(
            s, world.user, response_status=201, response_body={"data": {"ok": True}}
        )
        f_.make_balance(s, world.phc, world.batch, qty_available=5, qty_quarantined=0)
    with migrated.unit_of_work() as s:
        assert s.execute(text("SELECT count(*) FROM stock_movements")).scalar_one() == 3


def test_unknown_enum_values_are_refused_by_the_database_itself(migrated: Database) -> None:
    sql = (
        "INSERT INTO facilities (id, code, name, facility_type, timezone, is_active, "
        "created_at, updated_at) VALUES ('{id}', '{code}', 'Raw', '{kind}', 'UTC', TRUE, "
        "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
    )
    with migrated.unit_of_work(write=True) as s:  # control: a valid value goes through
        s.execute(text(sql.format(id=uuid.uuid4().hex, code="raw-1", kind="phc")))
    with pytest.raises(IntegrityError) as caught, migrated.unit_of_work(write=True) as s:
        s.execute(text(sql.format(id=uuid.uuid4().hex, code="raw-2", kind="warehouse")))
    assert "ck_facilities_facility_type" in str(caught.value) or "CHECK" in str(caught.value)


def test_json_none_is_stored_as_sql_null(migrated: Database) -> None:
    with migrated.unit_of_work(write=True) as s:
        f_.make_audit(s, details=None)
        f_.make_audit(s, details={"quantity": 5, "batch": "AMX-1"})
    with migrated.unit_of_work() as s:
        nulls = s.execute(text("SELECT count(*) FROM audit_records WHERE details IS NULL"))
        stored = list(
            s.scalars(select(AuditRecord.details).where(AuditRecord.details.is_not(None)))
        )
    assert nulls.scalar_one() == 1
    assert stored == [{"quantity": 5, "batch": "AMX-1"}]


def test_dates_survive_a_round_trip(migrated: Database, world: SimpleNamespace) -> None:
    with migrated.unit_of_work() as s:
        expiry = s.execute(text("SELECT expiry_date FROM batches")).scalar_one()
    assert str(expiry)[:10] == "2027-01-31"
    assert date(2027, 1, 31).isoformat() == "2027-01-31"
