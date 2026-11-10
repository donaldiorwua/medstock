import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import MetaData, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.types import UTCDateTime

# Every constraint gets a predictable name. Alembic batch mode on SQLite cannot drop or alter
# an unnamed constraint, and PostgreSQL would invent different names than SQLite.
# Rules for model authors: CHECK constraints need an explicit name=...; multi-column unique
# constraints and indexes need an explicit name too (the convention only sees column 0).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Mapped[datetime] always means "timezone-aware UTC"; Mapped[uuid.UUID] is a native UUID
# on PostgreSQL and a 32-character string on SQLite.
TYPE_ANNOTATION_MAP: dict[Any, Any] = {datetime: UTCDateTime, uuid.UUID: Uuid}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = TYPE_ANNOTATION_MAP


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
