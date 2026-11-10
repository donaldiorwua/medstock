from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from app.core.enums import FacilityType
from app.core.schemas import ApiModel, Envelope
from app.schemas.common import Code, ListEnvelope, PersonName, Timezone


class FacilityRecord(ApiModel):
    id: UUID
    code: str
    name: str
    facility_type: FacilityType
    timezone: str = Field(description="IANA time zone. Expiry is compared by date in this zone.")
    is_active: bool
    created_at: datetime


class CreateFacilityRequest(ApiModel):
    code: Code
    name: PersonName
    facility_type: FacilityType
    timezone: Timezone
    is_active: bool = True


class UpdateFacilityRequest(ApiModel):
    name: PersonName | None = None
    timezone: Timezone | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if all(value is None for value in (self.name, self.timezone, self.is_active)):
            raise ValueError("Provide at least one field to change.")
        return self


class FacilityResponse(Envelope[FacilityRecord]):
    pass


class FacilityListResponse(ListEnvelope[FacilityRecord]):
    pass


class ThresholdRecord(ApiModel):
    item_id: UUID
    item_code: str
    item_name: str
    base_unit: str
    reorder_level: int | None = Field(description="Null when no threshold is set for the item.")
    critical_level: int | None
    updated_at: datetime | None


class ThresholdIn(ApiModel):
    item_id: UUID
    reorder_level: int = Field(ge=0)
    critical_level: int = Field(ge=0)

    @model_validator(mode="after")
    def _reorder_not_below_critical(self) -> Self:
        if self.reorder_level < self.critical_level:
            raise ValueError("reorder_level must be greater than or equal to critical_level.")
        return self


class ReplaceThresholdsRequest(ApiModel):
    thresholds: list[ThresholdIn] = Field(
        description="The complete set for this facility. Items not listed have no thresholds."
    )

    @model_validator(mode="after")
    def _one_threshold_per_item(self) -> Self:
        item_ids = [t.item_id for t in self.thresholds]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Each item can appear only once.")
        return self


class ThresholdListResponse(ListEnvelope[ThresholdRecord]):
    pass


class ThresholdSetResponse(Envelope[list[ThresholdRecord]]):
    """The complete saved set, not paged."""
