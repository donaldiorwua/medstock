from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import Field, model_validator

from app.core.enums import LineStatus, RequestAction, RequestStatus
from app.core.schemas import ApiModel, Envelope
from app.schemas.common import ListEnvelope, Version
from app.schemas.stock import MAX_QUANTITY, Note, Quantity

# Zero is allowed in a review: it rejects the line.
ApprovedQuantity = Annotated[int, Field(strict=True, ge=0, le=MAX_QUANTITY)]


class ResupplyLineIn(ApiModel):
    item_id: UUID
    qty_requested: Quantity


def _unique(values: list[UUID], what: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"Each {what} can appear only once.")


class CreateResupplyRequest(ApiModel):
    facility_id: UUID = Field(description="The PHC asking for stock.")
    note: Note | None = None
    lines: list[ResupplyLineIn] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def _one_line_per_item(self) -> Self:
        _unique([line.item_id for line in self.lines], "item")
        return self


class UpdateResupplyRequest(ApiModel):
    """Edit a draft. Only allowed while the request is a draft."""

    version: Version
    note: Note | None = None
    lines: list[ResupplyLineIn] | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="The complete set of lines. Omit to leave the lines as they are.",
    )

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.note is None and self.lines is None:
            raise ValueError("Provide at least one field to change.")
        if self.lines is not None:
            _unique([line.item_id for line in self.lines], "item")
        return self


class SubmitResupplyRequest(ApiModel):
    version: Version


class CancelResupplyRequest(ApiModel):
    version: Version
    note: Note | None = None


class ReviewLineIn(ApiModel):
    line_id: UUID
    qty_approved: ApprovedQuantity = Field(
        description="0 rejects the line; less than requested approves part of it."
    )
    note: Note | None = None


class ReviewResupplyRequest(ApiModel):
    """Every line must be decided. Approval moves no stock."""

    version: Version
    note: Note | None = None
    lines: list[ReviewLineIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _one_decision_per_line(self) -> Self:
        _unique([line.line_id for line in self.lines], "line")
        return self


class ResupplyLineRecord(ApiModel):
    id: UUID
    item_id: UUID
    item_code: str
    item_name: str
    base_unit: str
    qty_requested: int
    qty_approved: int | None
    qty_dispatched: int | None
    qty_received: int | None
    status: LineStatus
    review_note: str | None


class ResupplySummary(ApiModel):
    id: UUID
    facility_id: UUID
    facility_name: str
    supplier_facility_id: UUID
    supplier_facility_name: str
    status: RequestStatus
    version: int
    line_count: int
    created_at: datetime
    submitted_at: datetime | None
    allowed_actions: list[RequestAction]


class ResupplyRecord(ResupplySummary):
    note: str | None
    created_by_id: UUID
    created_by_name: str
    reviewed_at: datetime | None
    reviewed_by_name: str | None
    review_note: str | None
    shipment_id: UUID | None
    lines: list[ResupplyLineRecord]


class ResupplyResponse(Envelope[ResupplyRecord]):
    pass


class ResupplyListResponse(ListEnvelope[ResupplySummary]):
    pass
