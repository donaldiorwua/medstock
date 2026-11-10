"""Column types that behave identically on SQLite and PostgreSQL (blueprint section 4.1)."""

import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Stores UTC, returns timezone-aware UTC, and refuses naive datetimes.

    SQLite has no real timestamp-with-timezone type, so we normalise to UTC on the way in
    and re-attach UTC on the way out. PostgreSQL gets timestamptz.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Naive datetime rejected: use a timezone-aware datetime.")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


# JSON on SQLite, JSONB on PostgreSQL. none_as_null: Python None is stored as SQL NULL,
# not as the JSON value null, so "IS NULL" checks and nullable columns behave as expected.
JSONType = JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql")


def string_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """A VARCHAR column plus a named CHECK constraint, never a native PostgreSQL enum.

    Native enums are painful to change in migrations and do not exist on SQLite.
    Values are stored as the enum's .value, not its member name.
    """
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=max(len(str(member.value)) for member in enum_cls),
        values_callable=lambda cls: [str(member.value) for member in cls],
    )
