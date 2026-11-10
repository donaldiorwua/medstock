from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from app.core.enums import ShipmentAction, ShipmentStatus
from app.core.schemas import ApiModel, Envelope
from app.schemas.common import ListEnvelope, Version
from app.schemas.requests import ApprovedQuantity
from app.schemas.stock import Note, Quantity


def _unique(values: list[UUID], what: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"Each {what} can appear only once.")


# ------------------------------------------------------------------ allocation suggestion


class AllocationBatch(ApiModel):
    batch_id: UUID
    batch_number: str
    expiry_date: date
    quantity: int = Field(description="How much to take from this batch.")
    batch_qty_usable: int = Field(description="Usable stock in this batch at the store now.")


class AllocationLine(ApiModel):
    line_id: UUID
    item_id: UUID
    item_code: str
    item_name: str
    base_unit: str
    qty_approved: int
    qty_allocated: int
    shortfall: int = Field(description="qty_approved minus qty_allocated. Above 0 blocks dispatch.")
    allocations: list[AllocationBatch] = Field(
        description="First-expiry-first-out: soonest usable expiry first."
    )


class AllocationSuggestion(ApiModel):
    request_id: UUID
    request_version: int
    can_dispatch: bool = Field(description="True when every approved line is fully covered.")
    lines: list[AllocationLine]


class AllocationSuggestionResponse(Envelope[AllocationSuggestion]):
    pass


# ------------------------------------------------------------------ dispatch


class AllocationIn(ApiModel):
    batch_id: UUID
    quantity: Quantity


class DispatchLineIn(ApiModel):
    line_id: UUID
    allocations: list[AllocationIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _one_entry_per_batch(self) -> Self:
        _unique([a.batch_id for a in self.allocations], "batch")
        return self


class DispatchRequest(ApiModel):
    """The quantities per line must add up to exactly qty_approved. All or nothing: if any
    line fails, no stock moves and no shipment is created."""

    version: Version
    note: Note | None = None
    lines: list[DispatchLineIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _one_entry_per_line(self) -> Self:
        _unique([line.line_id for line in self.lines], "line")
        return self


# ------------------------------------------------------------------ shipments


class ShipmentLineRecord(ApiModel):
    id: UUID
    request_line_id: UUID
    item_id: UUID
    item_code: str
    item_name: str
    base_unit: str
    batch_id: UUID
    batch_number: str
    expiry_date: date
    qty_dispatched: int
    qty_received: int | None


class ShipmentRecord(ApiModel):
    id: UUID
    request_id: UUID
    from_facility_id: UUID
    from_facility_name: str
    to_facility_id: UUID
    to_facility_name: str
    status: ShipmentStatus
    version: int
    dispatched_at: datetime
    dispatched_by_name: str
    received_at: datetime | None
    received_by_name: str | None
    note: str | None
    open_discrepancy_count: int
    lines: list[ShipmentLineRecord]
    allowed_actions: list[ShipmentAction]


class ShipmentResponse(Envelope[ShipmentRecord]):
    pass


class ShipmentListResponse(ListEnvelope[ShipmentRecord]):
    pass


class ReceiptLineIn(ApiModel):
    shipment_line_id: UUID
    qty_received: ApprovedQuantity = Field(
        description="What actually arrived. Between 0 and qty_dispatched."
    )


class ConfirmReceiptRequest(ApiModel):
    """Every shipment line must be counted. A shortfall opens a discrepancy."""

    version: Version
    note: Note | None = None
    lines: list[ReceiptLineIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _one_count_per_line(self) -> Self:
        _unique([line.shipment_line_id for line in self.lines], "shipment line")
        return self
