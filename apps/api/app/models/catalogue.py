import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import utcnow
from app.models.base import Base, UUIDPrimaryKeyMixin


class Item(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "items"

    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    base_unit: Mapped[str] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    __table_args__ = (CheckConstraint("code = lower(code)", name="code_lowercase"),)


class Batch(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "batches"

    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("items.id"))
    batch_number: Mapped[str] = mapped_column(String(64))
    # batch_number in lower case: what uniqueness is checked on.
    batch_number_key: Mapped[str] = mapped_column(String(64))
    expiry_date: Mapped[date]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        UniqueConstraint("item_id", "batch_number_key", name="uq_batches_item_batch_number"),
        CheckConstraint("batch_number_key = lower(batch_number)", name="batch_key_matches"),
        Index("ix_batches_item_id_expiry_date", "item_id", "expiry_date"),
    )


class StockThreshold(Base):
    """Reorder and critical levels for one item at one facility."""

    __tablename__ = "stock_thresholds"

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"), primary_key=True)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("items.id"), primary_key=True)
    reorder_level: Mapped[int]
    critical_level: Mapped[int]
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    updated_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    __table_args__ = (
        CheckConstraint("critical_level >= 0", name="critical_nonneg"),
        CheckConstraint("reorder_level >= critical_level", name="reorder_not_below_critical"),
        Index("ix_stock_thresholds_item_id", "item_id"),
    )
