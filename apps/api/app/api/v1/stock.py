from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.idempotency import IdempotencyKey
from app.api.security import READ_AUTH, WRITE_AUTH
from app.api.support import error_responses, not_implemented, posting_responses
from app.core.enums import AlertLevel, MovementType
from app.schemas.common import PageDep
from app.schemas.stock import (
    AdjustmentRequest,
    ExpiryWriteOffRequest,
    IssueRequest,
    MovementListResponse,
    OpeningStockRequest,
    PostingResponse,
    QuarantineRequest,
    ReceiptRequest,
    ReleaseRequest,
    ReversalRequest,
    StockItemResponse,
    StockListResponse,
)

router = APIRouter()

_READERS = "Members of the facility and admins."
_POSTERS = (
    "A phc_officer at their own PHC or a store_manager at the central store. "
    "Admins and viewers cannot change stock."
)
_POSTING = (
    " Requires the Idempotency-Key header: repeating the same key and body returns the "
    "original result (header Idempotent-Replay: true) without posting again."
)


# ------------------------------------------------------------------ reading


@router.get(
    "/facilities/{facility_id}/stock",
    tags=["stock"],
    response_model=StockListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 403, 404),
    summary="Stock register",
    description=(
        f"One row per item with usable, quarantined and expired quantities and the alert "
        f"level, all worked out by the API. {_READERS} meta.warnings may report batches "
        f"expiring soon and stale facility data."
    ),
)
def list_stock(
    facility_id: UUID,
    page: PageDep,
    q: Annotated[
        str | None, Query(max_length=100, description="Matches item name or code.")
    ] = None,
    alert_level: Annotated[AlertLevel | None, Query(description="Only this level.")] = None,
) -> StockListResponse:
    not_implemented()


@router.get(
    "/facilities/{facility_id}/stock/items/{item_id}",
    tags=["stock"],
    response_model=StockItemResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 403, 404),
    summary="Stock of one item",
    description=f"The item's figures plus every batch with a balance. {_READERS}",
)
def get_stock_item(facility_id: UUID, item_id: UUID) -> StockItemResponse:
    not_implemented()


@router.get(
    "/facilities/{facility_id}/movements",
    tags=["movements"],
    response_model=MovementListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 403, 404),
    summary="Movement history",
    description=f"The ledger for this facility, newest first. {_READERS}",
)
def list_movements(
    facility_id: UUID,
    page: PageDep,
    item_id: UUID | None = None,
    batch_id: UUID | None = None,
    movement_type: MovementType | None = None,
    date_from: Annotated[date | None, Query(description="occurred_on on or after.")] = None,
    date_to: Annotated[date | None, Query(description="occurred_on on or before.")] = None,
    needs_review: bool | None = None,
) -> MovementListResponse:
    not_implemented()


# ------------------------------------------------------------------ posting


@router.post(
    "/facilities/{facility_id}/stock/opening",
    tags=["stock"],
    status_code=201,
    response_model=PostingResponse,
    dependencies=WRITE_AUTH,
    responses=posting_responses(),
    summary="Record opening stock",
    description=(
        "Starting balance for one batch, once per facility and batch "
        "(OPENING_STOCK_EXISTS otherwise). signed_off_by names the person who verified "
        f"the count. {_POSTERS}{_POSTING}"
    ),
)
def post_opening_stock(
    facility_id: UUID, body: OpeningStockRequest, idempotency_key: IdempotencyKey
) -> PostingResponse:
    not_implemented()


@router.post(
    "/facilities/{facility_id}/stock/receipts",
    tags=["stock"],
    status_code=201,
    response_model=PostingResponse,
    dependencies=WRITE_AUTH,
    responses=posting_responses(),
    summary="Receive stock from outside the system",
    description=f"Adds to the available balance of a batch. {_POSTERS}{_POSTING}",
)
def post_receipt(
    facility_id: UUID, body: ReceiptRequest, idempotency_key: IdempotencyKey
) -> PostingResponse:
    not_implemented()


@router.post(
    "/facilities/{facility_id}/stock/issues",
    tags=["stock"],
    status_code=201,
    response_model=PostingResponse,
    dependencies=WRITE_AUTH,
    responses=posting_responses(),
    summary="Issue stock",
    description=(
        "Removes usable stock. INSUFFICIENT_STOCK if the batch does not have enough "
        "(nothing changes); BATCH_EXPIRED if it is past its expiry date. "
        f"{_POSTERS}{_POSTING}"
    ),
)
def post_issue(
    facility_id: UUID, body: IssueRequest, idempotency_key: IdempotencyKey
) -> PostingResponse:
    not_implemented()


@router.post(
    "/facilities/{facility_id}/stock/adjustments",
    tags=["stock"],
    status_code=201,
    response_model=PostingResponse,
    dependencies=WRITE_AUTH,
    responses=posting_responses(),
    summary="Adjust stock",
    description=(
        "A signed correction with a mandatory reason code. A change larger than 10 percent "
        f"of the batch balance is flagged needs_review. {_POSTERS}{_POSTING}"
    ),
)
def post_adjustment(
    facility_id: UUID, body: AdjustmentRequest, idempotency_key: IdempotencyKey
) -> PostingResponse:
    not_implemented()


@router.post(
    "/facilities/{facility_id}/stock/quarantine",
    tags=["stock"],
    status_code=201,
    response_model=PostingResponse,
    dependencies=WRITE_AUTH,
    responses=posting_responses(),
    summary="Quarantine stock",
    description=(
        "Moves available stock to quarantined. Appends two rows (one per balance) that "
        f"share a posting_id. {_POSTERS}{_POSTING}"
    ),
)
def post_quarantine(
    facility_id: UUID, body: QuarantineRequest, idempotency_key: IdempotencyKey
) -> PostingResponse:
    not_implemented()


@router.post(
    "/facilities/{facility_id}/stock/release",
    tags=["stock"],
    status_code=201,
    response_model=PostingResponse,
    dependencies=WRITE_AUTH,
    responses=posting_responses(),
    summary="Release quarantined stock",
    description=f"Moves quarantined stock back to available. {_POSTERS}{_POSTING}",
)
def post_release(
    facility_id: UUID, body: ReleaseRequest, idempotency_key: IdempotencyKey
) -> PostingResponse:
    not_implemented()


@router.post(
    "/facilities/{facility_id}/stock/expiry-writeoffs",
    tags=["stock"],
    status_code=201,
    response_model=PostingResponse,
    dependencies=WRITE_AUTH,
    responses=posting_responses(),
    summary="Write off expired stock",
    description=(
        "Removes stock of a batch that is past its expiry date (CONFLICT if the batch has "
        f"not expired). {_POSTERS}{_POSTING}"
    ),
)
def post_expiry_writeoff(
    facility_id: UUID, body: ExpiryWriteOffRequest, idempotency_key: IdempotencyKey
) -> PostingResponse:
    not_implemented()


@router.post(
    "/movements/{movement_id}/reversal",
    tags=["movements"],
    status_code=201,
    response_model=PostingResponse,
    dependencies=WRITE_AUTH,
    responses=posting_responses(),
    summary="Reverse a movement",
    description=(
        "Appends opposite rows for every row of the movement's posting. Allowed for "
        "opening, receipt, issue, adjustment, quarantine, release and expiry write-off "
        "rows only; not for dispatch, shipment receipt or discrepancy rows, rows that "
        "are already reversed, or reversal rows (REVERSAL_NOT_ALLOWED). "
        "INSUFFICIENT_STOCK if reversing would make a balance negative. "
        f"{_POSTERS}{_POSTING}"
    ),
)
def reverse_movement(
    movement_id: UUID, body: ReversalRequest, idempotency_key: IdempotencyKey
) -> PostingResponse:
    not_implemented()
