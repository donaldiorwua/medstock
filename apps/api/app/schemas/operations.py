from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enums import SeedProfile, StockBucket
from app.core.schemas import ApiModel, Envelope
from app.schemas.common import ListEnvelope


class AuditRecord(ApiModel):
    id: UUID
    occurred_at: datetime
    actor_id: UUID | None = Field(description="Null for actions taken by the system.")
    actor_name: str | None
    action: str = Field(description="area.entity.verb, for example stock.issue.posted.")
    entity_type: str
    entity_id: UUID | None
    facility_id: UUID | None
    summary: str
    request_id: str | None
    details: dict[str, Any] | None


class AuditListResponse(ListEnvelope[AuditRecord]):
    pass


class ReconciliationDifference(ApiModel):
    facility_id: UUID
    facility_name: str
    item_code: str
    batch_id: UUID
    batch_number: str
    bucket: StockBucket
    balance: int = Field(description="What the balance table says.")
    ledger_sum: int = Field(description="The sum of the ledger rows. The truth.")
    difference: int


class ReconciliationReport(ApiModel):
    checked_at: datetime
    rows_checked: int
    ok: bool = Field(description="True when every balance equals its ledger sum.")
    differences: list[ReconciliationDifference] = Field(description="At most 500 rows.")
    truncated: bool = Field(description="True when more than 500 differences exist.")


class ReconciliationResponse(Envelope[ReconciliationReport]):
    pass


class ResetData(ApiModel):
    reset: bool


class ResetResponse(Envelope[ResetData]):
    pass


class SeedRequest(ApiModel):
    profile: SeedProfile


class SeedData(ApiModel):
    profile: SeedProfile
    counts: dict[str, int] = Field(description="Rows created per table.")


class SeedResponse(Envelope[SeedData]):
    pass
