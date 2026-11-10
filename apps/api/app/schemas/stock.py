from datetime import date, datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator

from app.core.enums import (
    AdjustmentReason,
    AlertLevel,
    MovementAction,
    MovementType,
    StockBucket,
)
from app.core.schemas import ApiModel, Envelope
from app.schemas.common import ListEnvelope

MAX_QUANTITY = 1_000_000_000

# Strict: JSON 5 is accepted, but 5.0, "5" and true are not (quantities are whole numbers).
Quantity = Annotated[int, Field(strict=True, ge=1, le=MAX_QUANTITY)]
SignedQuantity = Annotated[int, Field(strict=True, ge=-MAX_QUANTITY, le=MAX_QUANTITY)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]

_OCCURRED_ON = (
    "The day the stock actually moved, in the facility's time zone. Defaults to today. "
    "It cannot be in the future or more than BACKDATE_DAYS (30) days in the past "
    "(BACKDATE_LIMIT_EXCEEDED)."
)


# ------------------------------------------------------------------ reading the register


class StockItemRow(ApiModel):
    """One item at one facility, with every figure the screen needs already worked out."""

    item_id: UUID
    item_code: str
    item_name: str
    base_unit: str
    qty_usable: int = Field(description="Available, not expired. What can be issued today.")
    qty_quarantined: int
    qty_expired: int = Field(description="Still on the shelf but past expiry. Not usable.")
    reorder_level: int | None
    critical_level: int | None
    alert_level: AlertLevel = Field(
        description="From qty_usable and the thresholds. Without thresholds: out_of_stock "
        "at zero, otherwise ok."
    )
    nearest_expiry_date: date | None = Field(
        description="Soonest expiry among non-expired batches that still have stock."
    )
    last_movement_at: datetime | None


class StockBatchRow(ApiModel):
    batch_id: UUID
    batch_number: str
    expiry_date: date
    days_to_expiry: int = Field(
        description="Negative once expired. Usable through the expiry date."
    )
    is_expired: bool
    expiring_soon: bool = Field(description="Within EXPIRY_WARNING_DAYS (90) and not expired.")
    qty_available: int
    qty_quarantined: int
    qty_usable: int = Field(description="qty_available, or 0 when the batch is expired.")


class StockItemDetail(StockItemRow):
    batches: list[StockBatchRow] = Field(
        description="Every batch with a balance, soonest expiry first."
    )


class StockListResponse(ListEnvelope[StockItemRow]):
    pass


class StockItemResponse(Envelope[StockItemDetail]):
    pass


# ------------------------------------------------------------------ the ledger


class MovementRecord(ApiModel):
    id: UUID
    posting_id: UUID = Field(
        description="Rows created by one action share it (both rows of a quarantine)."
    )
    facility_id: UUID
    item_id: UUID
    item_code: str
    item_name: str
    base_unit: str
    batch_id: UUID
    batch_number: str
    expiry_date: date
    movement_type: MovementType
    bucket: StockBucket
    quantity_delta: int = Field(description="Signed and never zero.")
    balance_after: int = Field(description="The bucket's balance after this row.")
    occurred_on: date
    reason: AdjustmentReason | None
    note: str | None
    reference: str | None
    source: str | None
    signed_off_by: str | None
    needs_review: bool = Field(
        description="True for an adjustment above 10 percent of the batch balance."
    )
    reverses_movement_id: UUID | None
    reversed_by_movement_id: UUID | None
    created_by_id: UUID
    created_by_name: str
    created_at: datetime
    allowed_actions: list[MovementAction]


class MovementListResponse(ListEnvelope[MovementRecord]):
    pass


class PostingResult(ApiModel):
    movements: list[MovementRecord] = Field(description="The rows this action appended.")
    item_stock: StockItemRow = Field(description="The item's figures after the action.")


class PostingResponse(Envelope[PostingResult]):
    pass


# ------------------------------------------------------------------ posting requests


class OpeningStockRequest(ApiModel):
    batch_id: UUID
    quantity: Quantity
    signed_off_by: ShortText = Field(description="Name of the person who verified the count.")
    occurred_on: date | None = Field(default=None, description=_OCCURRED_ON)
    note: Note | None = None


class ReceiptRequest(ApiModel):
    """Stock received from outside the system (a supplier or donor)."""

    batch_id: UUID
    quantity: Quantity
    source: ShortText | None = None
    reference: ShortText | None = Field(
        default=None, description="For example a delivery note number."
    )
    occurred_on: date | None = Field(default=None, description=_OCCURRED_ON)
    note: Note | None = None


class IssueRequest(ApiModel):
    batch_id: UUID
    quantity: Quantity
    occurred_on: date | None = Field(default=None, description=_OCCURRED_ON)
    note: Note | None = None


class AdjustmentRequest(ApiModel):
    batch_id: UUID
    quantity_delta: SignedQuantity = Field(
        description="Positive adds stock, negative removes it. Not zero."
    )
    reason: AdjustmentReason
    occurred_on: date | None = Field(default=None, description=_OCCURRED_ON)
    note: Note | None = Field(default=None, description="Required when reason is 'other'.")

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.quantity_delta == 0:
            raise ValueError("quantity_delta must not be zero.")
        if self.reason is AdjustmentReason.OTHER and self.note is None:
            raise ValueError("A note is required when the reason is 'other'.")
        return self


class QuarantineRequest(ApiModel):
    batch_id: UUID
    quantity: Quantity
    note: Note = Field(description="Why the stock is being quarantined.")
    occurred_on: date | None = Field(default=None, description=_OCCURRED_ON)


class ReleaseRequest(ApiModel):
    batch_id: UUID
    quantity: Quantity
    occurred_on: date | None = Field(default=None, description=_OCCURRED_ON)
    note: Note | None = None


class ExpiryWriteOffRequest(ApiModel):
    batch_id: UUID
    quantity: Quantity
    bucket: StockBucket = Field(
        default=StockBucket.AVAILABLE, description="Which balance the expired stock is taken from."
    )
    occurred_on: date | None = Field(default=None, description=_OCCURRED_ON)
    note: Note | None = None


class ReversalRequest(ApiModel):
    note: Note = Field(description="Why the movement is being reversed.")
