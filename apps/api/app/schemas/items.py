from datetime import date, datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator

from app.core.schemas import ApiModel, Envelope
from app.schemas.common import Code, ListEnvelope, PersonName

BatchNumber = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
BaseUnit = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]


class ItemRecord(ApiModel):
    id: UUID
    code: str
    name: str
    base_unit: str = Field(description="The one unit every quantity of this item is counted in.")
    description: str | None
    is_active: bool
    created_at: datetime


class CreateItemRequest(ApiModel):
    code: Code
    name: PersonName
    base_unit: BaseUnit
    description: str | None = Field(default=None, max_length=500)


class UpdateItemRequest(ApiModel):
    """The code and base unit cannot be changed."""

    name: PersonName | None = None
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if all(value is None for value in (self.name, self.description, self.is_active)):
            raise ValueError("Provide at least one field to change.")
        return self


class ItemResponse(Envelope[ItemRecord]):
    pass


class ItemListResponse(ListEnvelope[ItemRecord]):
    pass


class BatchRecord(ApiModel):
    id: UUID
    item_id: UUID
    batch_number: str
    expiry_date: date
    created_at: datetime


class CreateBatchRequest(ApiModel):
    item_id: UUID
    batch_number: BatchNumber = Field(
        description="Unique per item, compared without regard to case."
    )
    expiry_date: date


class BatchResponse(Envelope[BatchRecord]):
    pass


class BatchListResponse(ListEnvelope[BatchRecord]):
    pass
