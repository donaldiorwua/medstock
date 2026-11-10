import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import AdjustmentReason, MovementType, StockBucket
from app.core.types import string_enum, utcnow
from app.models.base import Base, UUIDPrimaryKeyMixin


class StockBalance(Base):
    """What is on hand for one batch at one facility. A projection of the ledger, updated in
    the same transaction as every movement, so it always equals the sum of its movements."""

    __tablename__ = "stock_balances"

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), primary_key=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id"), primary_key=True)
    qty_available: Mapped[int] = mapped_column(default=0)
    qty_quarantined: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint("qty_available >= 0", name="qty_available_nonneg"),
        CheckConstraint("qty_quarantined >= 0", name="qty_quarantined_nonneg"),
        Index("ix_stock_balances_batch_id", "batch_id"),
    )


class StockMovement(UUIDPrimaryKeyMixin, Base):
    """The ledger. Append-only: rows are never updated or deleted. Each row changes one
    bucket of one balance by a signed, non-zero amount."""

    __tablename__ = "stock_movements"

    posting_id: Mapped[uuid.UUID]
    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"))
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id"))
    movement_type: Mapped[MovementType] = mapped_column(string_enum(MovementType, "movement_type"))
    bucket: Mapped[StockBucket] = mapped_column(string_enum(StockBucket, "bucket"))
    quantity_delta: Mapped[int]
    balance_after: Mapped[int]
    occurred_on: Mapped[date]
    reason: Mapped[AdjustmentReason | None] = mapped_column(string_enum(AdjustmentReason, "reason"))
    note: Mapped[str | None] = mapped_column(String(500))
    reference: Mapped[str | None] = mapped_column(String(120))
    source: Mapped[str | None] = mapped_column(String(120))
    signed_off_by: Mapped[str | None] = mapped_column(String(120))
    needs_review: Mapped[bool] = mapped_column(default=False)
    reverses_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_movements.id"), unique=True
    )
    shipment_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shipment_lines.id"))
    discrepancy_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("discrepancies.id"))
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        CheckConstraint("quantity_delta <> 0", name="delta_nonzero"),
        CheckConstraint("balance_after >= 0", name="balance_after_nonneg"),
        CheckConstraint(
            "movement_type <> 'adjustment' OR reason IS NOT NULL", name="adjustment_has_reason"
        ),
        CheckConstraint(
            "movement_type <> 'opening' OR signed_off_by IS NOT NULL", name="opening_signed_off"
        ),
        CheckConstraint(
            "movement_type <> 'reversal' OR reverses_movement_id IS NOT NULL",
            name="reversal_has_target",
        ),
        CheckConstraint(
            "movement_type = 'reversal' OR reverses_movement_id IS NULL",
            name="only_reversals_have_target",
        ),
        Index("ix_stock_movements_facility_id_created_at", "facility_id", "created_at"),
        Index("ix_stock_movements_batch_id", "batch_id"),
        Index("ix_stock_movements_posting_id", "posting_id"),
        # Opening stock is recorded once per facility and batch. (Partial index: supported by
        # both SQLite and PostgreSQL.)
        Index(
            "uq_stock_movements_opening",
            "facility_id",
            "batch_id",
            unique=True,
            sqlite_where=text("movement_type = 'opening'"),
            postgresql_where=text("movement_type = 'opening'"),
        ),
    )
