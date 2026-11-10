import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import JSONType, utcnow
from app.models.base import Base, UUIDPrimaryKeyMixin


class AuditRecord(UUIDPrimaryKeyMixin, Base):
    """Who did what and when. Append-only. Written in the same transaction as the change."""

    __tablename__ = "audit_records"

    occurred_at: Mapped[datetime] = mapped_column(default=utcnow)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[uuid.UUID | None]
    facility_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("facilities.id"))
    summary: Mapped[str] = mapped_column(String(500))
    request_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONType)

    __table_args__ = (
        Index("ix_audit_records_occurred_at", "occurred_at"),
        Index("ix_audit_records_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_records_facility_id_occurred_at", "facility_id", "occurred_at"),
        Index("ix_audit_records_actor_id", "actor_id"),
    )


class IdempotencyKey(UUIDPrimaryKeyMixin, Base):
    """Remembers the outcome of an action so a retry does nothing twice.

    The row is inserted first (reserving the key), filled in before the same transaction
    commits, so a committed row always has its response."""

    __tablename__ = "idempotency_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(String(64))
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(255))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int | None]
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_idempotency_keys_user_id_key"),
        CheckConstraint(
            "(response_status IS NULL AND response_body IS NULL) OR "
            "(response_status IS NOT NULL AND response_body IS NOT NULL)",
            name="response_complete_or_pending",
        ),
        Index("ix_idempotency_keys_expires_at", "expires_at"),
    )
