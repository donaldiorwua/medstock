from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.enums import (
    DiscrepancyAction,
    DiscrepancyResolution,
    DiscrepancyStatus,
    RequestStatus,
)
from app.core.schemas import ApiModel, Envelope
from app.schemas.common import ListEnvelope, Version
from app.schemas.stock import MovementRecord, Note


class DiscrepancyRecord(ApiModel):
    id: UUID
    shipment_id: UUID
    shipment_line_id: UUID
    request_id: UUID
    facility_id: UUID = Field(description="The PHC that received the shipment.")
    facility_name: str
    item_id: UUID
    item_code: str
    item_name: str
    base_unit: str
    batch_id: UUID
    batch_number: str
    qty_dispatched: int
    qty_received: int
    qty_missing: int
    status: DiscrepancyStatus
    resolution: DiscrepancyResolution | None
    resolution_note: str | None
    resolved_at: datetime | None
    resolved_by_name: str | None
    created_at: datetime
    version: int
    allowed_actions: list[DiscrepancyAction]


class DiscrepancyResponse(Envelope[DiscrepancyRecord]):
    pass


class DiscrepancyListResponse(ListEnvelope[DiscrepancyRecord]):
    pass


class ResolveDiscrepancyRequest(ApiModel):
    version: Version
    resolution: DiscrepancyResolution
    note: Note | None = None


class ResolutionResult(ApiModel):
    discrepancy: DiscrepancyRecord
    movements: list[MovementRecord] = Field(
        description="Ledger rows created by the resolution (none for a plain write-off)."
    )
    request_status: RequestStatus = Field(
        description="'closed' once the last discrepancy of the request is resolved."
    )


class ResolveDiscrepancyResponse(Envelope[ResolutionResult]):
    pass
