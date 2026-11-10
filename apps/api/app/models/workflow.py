import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    DiscrepancyResolution,
    DiscrepancyStatus,
    LineStatus,
    RequestStatus,
    ShipmentStatus,
)
from app.core.types import string_enum, utcnow
from app.models.base import Base, UUIDPrimaryKeyMixin


class ResupplyRequest(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "resupply_requests"

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"))
    supplier_facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"))
    status: Mapped[RequestStatus] = mapped_column(string_enum(RequestStatus, "status"))
    version: Mapped[int] = mapped_column(default=1)
    note: Mapped[str | None] = mapped_column(String(500))
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    submitted_at: Mapped[datetime | None]
    reviewed_at: Mapped[datetime | None]
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint("facility_id <> supplier_facility_id", name="requester_not_supplier"),
        CheckConstraint("version >= 1", name="version_positive"),
        Index("ix_resupply_requests_facility_id_status", "facility_id", "status"),
        Index("ix_resupply_requests_status_created_at", "status", "created_at"),
    )


class ResupplyRequestLine(UUIDPrimaryKeyMixin, Base):
    """One item on a request. Dispatched and received quantities live on the shipment and
    receipt tables and are derived, not copied here."""

    __tablename__ = "resupply_request_lines"

    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resupply_requests.id"))
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("items.id"))
    qty_requested: Mapped[int]
    qty_approved: Mapped[int | None]
    status: Mapped[LineStatus] = mapped_column(string_enum(LineStatus, "status"))
    review_note: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("request_id", "item_id", name="uq_resupply_request_lines_request_item"),
        CheckConstraint("qty_requested >= 1", name="qty_requested_positive"),
        CheckConstraint("qty_approved IS NULL OR qty_approved >= 0", name="qty_approved_nonneg"),
        CheckConstraint(
            "qty_approved IS NULL OR qty_approved <= qty_requested",
            name="approved_within_requested",
        ),
        Index("ix_resupply_request_lines_request_id", "request_id"),
    )


class Shipment(UUIDPrimaryKeyMixin, Base):
    """What the store sent for one request. A request has at most one shipment."""

    __tablename__ = "shipments"

    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resupply_requests.id"), unique=True)
    from_facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"))
    to_facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"))
    status: Mapped[ShipmentStatus] = mapped_column(string_enum(ShipmentStatus, "status"))
    version: Mapped[int] = mapped_column(default=1)
    dispatched_at: Mapped[datetime] = mapped_column(default=utcnow)
    dispatched_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    received_at: Mapped[datetime | None]
    received_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint("from_facility_id <> to_facility_id", name="distinct_facilities"),
        CheckConstraint("version >= 1", name="version_positive"),
        Index("ix_shipments_to_facility_id_status", "to_facility_id", "status"),
    )


class ShipmentLine(UUIDPrimaryKeyMixin, Base):
    """Stock sent from one batch for one request line."""

    __tablename__ = "shipment_lines"

    shipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shipments.id"))
    request_line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resupply_request_lines.id"))
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id"))
    qty_dispatched: Mapped[int]

    __table_args__ = (
        UniqueConstraint(
            "shipment_id", "request_line_id", "batch_id", name="uq_shipment_lines_line_batch"
        ),
        # Target of the composite foreign key on receipt_lines (see there).
        UniqueConstraint("id", "qty_dispatched", name="uq_shipment_lines_id_qty_dispatched"),
        CheckConstraint("qty_dispatched >= 1", name="qty_dispatched_positive"),
        Index("ix_shipment_lines_shipment_id", "shipment_id"),
    )


class ReceiptLine(UUIDPrimaryKeyMixin, Base):
    """What the PHC counted for one shipment line.

    qty_dispatched is a copy, and the composite foreign key forces it to equal the shipment
    line's value. That lets a plain CHECK enforce qty_received <= qty_dispatched.
    """

    __tablename__ = "receipt_lines"

    shipment_line_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    qty_dispatched: Mapped[int]
    qty_received: Mapped[int]
    received_at: Mapped[datetime] = mapped_column(default=utcnow)
    received_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    __table_args__ = (
        ForeignKeyConstraint(
            ["shipment_line_id", "qty_dispatched"],
            ["shipment_lines.id", "shipment_lines.qty_dispatched"],
            name="fk_receipt_lines_shipment_line_qty",
        ),
        CheckConstraint("qty_received >= 0", name="qty_received_nonneg"),
        CheckConstraint("qty_received <= qty_dispatched", name="received_within_dispatched"),
    )


class Discrepancy(UUIDPrimaryKeyMixin, Base):
    """A shortfall found at receipt: one per short receipt line."""

    __tablename__ = "discrepancies"

    receipt_line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("receipt_lines.id"), unique=True)
    qty_missing: Mapped[int]
    status: Mapped[DiscrepancyStatus] = mapped_column(string_enum(DiscrepancyStatus, "status"))
    resolution: Mapped[DiscrepancyResolution | None] = mapped_column(
        string_enum(DiscrepancyResolution, "resolution")
    )
    resolution_note: Mapped[str | None] = mapped_column(String(500))
    resolved_at: Mapped[datetime | None]
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint("qty_missing >= 1", name="qty_missing_positive"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint(
            "(status = 'open' AND resolution IS NULL AND resolved_at IS NULL "
            "AND resolved_by_id IS NULL) OR "
            "(status = 'resolved' AND resolution IS NOT NULL AND resolved_at IS NOT NULL "
            "AND resolved_by_id IS NOT NULL)",
            name="state_consistent",
        ),
        Index("ix_discrepancies_status", "status"),
    )
