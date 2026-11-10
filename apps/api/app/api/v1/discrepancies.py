from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.idempotency import IdempotencyKey
from app.api.security import READ_AUTH, WRITE_AUTH
from app.api.support import action_responses, error_responses, not_implemented
from app.core.enums import DiscrepancyStatus
from app.schemas.common import PageDep
from app.schemas.discrepancies import (
    DiscrepancyListResponse,
    DiscrepancyResponse,
    ResolveDiscrepancyRequest,
    ResolveDiscrepancyResponse,
)

router = APIRouter(prefix="/discrepancies", tags=["discrepancies"])


@router.get(
    "",
    response_model=DiscrepancyListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401),
    summary="List discrepancies",
    description="PHC users see their own PHC's. Store managers and admins see all.",
)
def list_discrepancies(
    page: PageDep,
    status: Annotated[DiscrepancyStatus | None, Query(description="Only this status.")] = None,
    facility_id: Annotated[UUID | None, Query(description="Only this PHC.")] = None,
) -> DiscrepancyListResponse:
    not_implemented()


@router.get(
    "/{discrepancy_id}",
    response_model=DiscrepancyResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 404),
    summary="Get a discrepancy",
    description="With allowed_actions.",
)
def get_discrepancy(discrepancy_id: UUID) -> DiscrepancyResponse:
    not_implemented()


@router.post(
    "/{discrepancy_id}/resolve",
    response_model=ResolveDiscrepancyResponse,
    dependencies=WRITE_AUTH,
    responses=action_responses(),
    summary="Resolve a discrepancy",
    description=(
        "A store_manager resolves the whole shortfall in one of three ways. written_off: "
        "the stock is recorded as lost and leaves the in-transit total. recovered_to_phc: "
        "the PHC's stock increases by the missing quantity. recovered_to_store: the store's "
        "stock increases by it. When the last discrepancy of a request is resolved, the "
        "request closes. Send the discrepancy's current version; INVALID_TRANSITION if it "
        "is already resolved. Requires the Idempotency-Key header: repeating the same key "
        "and body returns the original result (header Idempotent-Replay: true)."
    ),
)
def resolve_discrepancy(
    discrepancy_id: UUID, body: ResolveDiscrepancyRequest, idempotency_key: IdempotencyKey
) -> ResolveDiscrepancyResponse:
    not_implemented()
