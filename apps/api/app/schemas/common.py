"""Building blocks shared by every API area."""

from typing import Annotated

from fastapi import Depends, Query
from pydantic import Field, StringConstraints

from app.core.enums import WarningCode
from app.core.schemas import ApiModel

# Strings the server normalises. Patterns accept upper case because the lower-casing is
# applied after the pattern check; the stored value is always lower case (blueprint 4.1).
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]
Code = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=2,
        max_length=40,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]
# IANA time zone name such as Africa/Lagos. Existence is checked when the endpoint is built.
Timezone = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=64,
        pattern=r"^(UTC|[A-Za-z]+(/[A-Za-z0-9_+-]+)+)$",
    ),
]
Password = Annotated[str, StringConstraints(min_length=10, max_length=128)]
# Optimistic-concurrency counter of a workflow record. Send back the value you read;
# a mismatch returns VERSION_CONFLICT.
Version = Annotated[int, Field(strict=True, ge=1)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class PageMeta(ApiModel):
    total: int = Field(ge=0, description="Number of records matching the filters.")
    limit: int = Field(ge=1, description="Page size used.")
    offset: int = Field(ge=0, description="Number of records skipped.")


class ResponseWarning(ApiModel):
    code: WarningCode
    message: str


class ListMeta(ApiModel):
    page: PageMeta
    warnings: list[ResponseWarning] = Field(default_factory=list)


class ListEnvelope[T](ApiModel):
    """List envelope. Every list endpoint defines a NAMED subclass, as with Envelope."""

    data: list[T]
    meta: ListMeta


class PageParams:
    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=200, description="Page size (1 to 200).")] = 50,
        offset: Annotated[int, Query(ge=0, description="Records to skip.")] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


PageDep = Annotated[PageParams, Depends()]
