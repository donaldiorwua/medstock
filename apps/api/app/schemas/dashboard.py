from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.core.enums import AlertLevel, AlertType, FacilityType
from app.core.schemas import ApiModel, Envelope
from app.schemas.common import ListEnvelope


class FacilityStatus(ApiModel):
    facility_id: UUID
    facility_name: str
    facility_type: FacilityType
    last_update_at: datetime | None = Field(description="Latest stock movement at the facility.")
    is_stale: bool = Field(description="No update for more than STALE_HOURS (72).")
    items_out_of_stock: int
    items_critical: int
    items_reorder: int
    batches_expiring_soon: int
    batches_expired_with_stock: int


class WorkflowCounts(ApiModel):
    requests_awaiting_review: int
    requests_awaiting_dispatch: int
    shipments_in_transit: int
    discrepancies_open: int


class InTransitItem(ApiModel):
    item_id: UUID
    item_code: str
    item_name: str
    base_unit: str
    quantity: int = Field(
        description="Dispatched but not yet received, plus missing stock in open discrepancies."
    )


class DashboardSummary(ApiModel):
    generated_at: datetime
    facilities: list[FacilityStatus]
    workflow: WorkflowCounts
    in_transit: list[InTransitItem]


class DashboardSummaryResponse(Envelope[DashboardSummary]):
    pass


class AlertRecord(ApiModel):
    key: str = Field(description="Stable identifier of the alert, usable as a list key.")
    type: AlertType
    level: AlertLevel | None = Field(description="Only for stock_level alerts.")
    facility_id: UUID
    facility_name: str
    item_id: UUID | None
    item_code: str | None
    item_name: str | None
    batch_id: UUID | None
    batch_number: str | None
    quantity: int | None
    threshold: int | None
    expiry_date: date | None
    message: str


class AlertListResponse(ListEnvelope[AlertRecord]):
    pass
