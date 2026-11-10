from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.idempotency import IdempotencyKey
from app.api.security import READ_AUTH, WRITE_AUTH
from app.api.support import action_responses, error_responses, not_implemented, posting_responses
from app.core.enums import ShipmentStatus
from app.schemas.common import PageDep
from app.schemas.shipments import (
    AllocationSuggestionResponse,
    ConfirmReceiptRequest,
    DispatchRequest,
    ShipmentListResponse,
    ShipmentResponse,
)

router = APIRouter(tags=["shipments"])

_KEY = (
    " Requires the Idempotency-Key header: repeating the same key and body returns the "
    "original result (header Idempotent-Replay: true)."
)


@router.get(
    "/requests/{request_id}/allocation-suggestion",
    response_model=AllocationSuggestionResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 403, 404),
    summary="Suggest which batches to dispatch",
    description=(
        "A store_manager. For an approved or partially approved request: the batches to "
        "take from, soonest usable expiry first. Expired and quarantined stock is never "
        "suggested. can_dispatch is false when the store cannot cover a line."
    ),
)
def get_allocation_suggestion(request_id: UUID) -> AllocationSuggestionResponse:
    not_implemented()


@router.post(
    "/requests/{request_id}/dispatch",
    status_code=201,
    response_model=ShipmentResponse,
    dependencies=WRITE_AUTH,
    responses=posting_responses(),
    summary="Dispatch a request",
    description=(
        "A store_manager. Creates a shipment and reduces the store's stock once, in one "
        "transaction. If any line fails (INSUFFICIENT_STOCK, BATCH_EXPIRED, wrong total) "
        "nothing changes. Send the request's current version; VERSION_CONFLICT if it "
        "changed, INVALID_TRANSITION if dispatch is not in allowed_actions." + _KEY
    ),
)
def dispatch_request(
    request_id: UUID, body: DispatchRequest, idempotency_key: IdempotencyKey
) -> ShipmentResponse:
    not_implemented()


@router.get(
    "/shipments",
    response_model=ShipmentListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401),
    summary="List shipments",
    description="PHC users see shipments to their PHC. Store managers and admins see all.",
)
def list_shipments(
    page: PageDep,
    status: Annotated[ShipmentStatus | None, Query(description="Only this status.")] = None,
    facility_id: Annotated[UUID | None, Query(description="Only to this PHC.")] = None,
    request_id: UUID | None = None,
) -> ShipmentListResponse:
    not_implemented()


@router.get(
    "/shipments/{shipment_id}",
    response_model=ShipmentResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 404),
    summary="Get a shipment",
    description="With its lines per batch and allowed_actions.",
)
def get_shipment(shipment_id: UUID) -> ShipmentResponse:
    not_implemented()


@router.post(
    "/shipments/{shipment_id}/receipt",
    response_model=ShipmentResponse,
    dependencies=WRITE_AUTH,
    responses=action_responses(),
    summary="Confirm receipt of a shipment",
    description=(
        "A phc_officer of the receiving PHC counts every line. The PHC's stock increases "
        "once by what arrived. Any shortfall opens a discrepancy; the missing quantity "
        "stays accounted for as in transit until it is resolved. Send the shipment's "
        "current version; INVALID_TRANSITION if confirm_receipt is not in allowed_actions." + _KEY
    ),
)
def confirm_shipment_receipt(
    shipment_id: UUID, body: ConfirmReceiptRequest, idempotency_key: IdempotencyKey
) -> ShipmentResponse:
    not_implemented()
