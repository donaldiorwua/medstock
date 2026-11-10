"""Throwaway tables used only by tests, on their own metadata, so they never enter the
migration history. They prove the shared types and conventions on both databases."""

import enum
from datetime import datetime

from sqlalchemy import Column, ForeignKey, MetaData, String, Table, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.types import JSONType, UTCDateTime, string_enum
from app.models.base import NAMING_CONVENTION, TYPE_ANNOTATION_MAP, UUIDPrimaryKeyMixin


class ProbeStatus(enum.StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class ProbeBase(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = TYPE_ANNOTATION_MAP


probe_parent = Table(
    "probe_parent",
    ProbeBase.metadata,
    Column("id", Uuid, primary_key=True),
    Column("created_at", UTCDateTime, nullable=False),
    Column("payload", JSONType, nullable=True),
    Column("status", string_enum(ProbeStatus, "probe_status"), nullable=False),
)

probe_child = Table(
    "probe_child",
    ProbeBase.metadata,
    Column("id", Uuid, primary_key=True),
    Column("parent_id", Uuid, ForeignKey("probe_parent.id"), nullable=False),
)


class Widget(UUIDPrimaryKeyMixin, ProbeBase):
    """Exercises the base-class conventions: UUID mixin and Mapped[datetime]."""

    __tablename__ = "probe_widget"

    name: Mapped[str] = mapped_column(String(50))
    seen_at: Mapped[datetime]
