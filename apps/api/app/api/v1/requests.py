from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.idempotency import IdempotencyKey
from app.api.security import READ_AUTH, WRITE_AUTH
from app.api.support import action_responses, error_responses, not_implemented
from app.core.enums import RequestStatus
from app.schemas.common import PageDep
from app.schemas.requests import (
    CancelResupplyRequest,
    CreateResupplyRequest,
    ResupplyListResponse,
    ResupplyResponse,
    ReviewResupplyRequest,
    SubmitResupplyRequest,
    UpdateResupplyRequest,
)

router = APIRouter(prefix="/requests", tags=["requests"])

_KEY = (
    " Requires the Idempotency-Key header: repeating the same key and body returns the "
    "original result (header Idempotent-Replay: true)."
)
_STATE = (
    " Send the record's current version; VERSION_CONFLICT if it changed, "
    "INVALID_TRANSITION if the action is not in allowed_actions."
)


@router.post(
    "",
    status_code=201,
    response_model=ResupplyResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 404),
    summary="Create a draft request",
    description=(
        "A phc_officer of the requesting PHC. The request starts as a draft; nothing is "
        "sent to the store until it is submitted. One line per item."
    ),
)
def create_request(body: CreateResupplyRequest) -> ResupplyResponse:
    not_implemented()


@router.get(
    "",
    response_model=ResupplyListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401),
    summary="List requests",
    description=(
        "PHC users see their own PHC's requests. Store managers and admins see all. Newest first."
    ),
)
def list_requests(
    page: PageDep,
    status: Annotated[RequestStatus | None, Query(description="Only this status.")] = None,
    facility_id: Annotated[UUID | None, Query(description="Only this requesting PHC.")] = None,
    date_from: Annotated[date | None, Query(description="Created on or after.")] = None,
    date_to: Annotated[date | None, Query(description="Created on or before.")] = None,
) -> ResupplyListResponse:
    not_implemented()


@router.get(
    "/{request_id}",
    response_model=ResupplyResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 404),
    summary="Get a request",
    description="With its lines and allowed_actions. A request of another PHC returns 404.",
)
def get_request(request_id: UUID) -> ResupplyResponse:
    not_implemented()


@router.patch(
    "/{request_id}",
    response_model=ResupplyResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 404, 409),
    summary="Edit a draft request",
    description=("A phc_officer of the requesting PHC, while the request is a draft." + _STATE),
)
def update_request(request_id: UUID, body: UpdateResupplyRequest) -> ResupplyResponse:
    not_implemented()


@router.post(
    "/{request_id}/submit",
    response_model=ResupplyResponse,
    dependencies=WRITE_AUTH,
    responses=action_responses(),
    summary="Submit a request",
    description="Sends a draft to the store for review. A phc_officer of the PHC." + _STATE + _KEY,
)
def submit_request(
    request_id: UUID, body: SubmitResupplyRequest, idempotency_key: IdempotencyKey
) -> ResupplyResponse:
    not_implemented()


@router.post(
    "/{request_id}/cancel",
    response_model=ResupplyResponse,
    dependencies=WRITE_AUTH,
    responses=action_responses(),
    summary="Cancel a request",
    description=(
        "A draft or submitted request can be cancelled by a phc_officer of the PHC." + _STATE + _KEY
    ),
)
def cancel_request(
    request_id: UUID, body: CancelResupplyRequest, idempotency_key: IdempotencyKey
) -> ResupplyResponse:
    not_implemented()


@router.post(
    "/{request_id}/review",
    response_model=ResupplyResponse,
    dependencies=WRITE_AUTH,
    responses=action_responses(),
    summary="Review a request, line by line",
    description=(
        "A store_manager decides every line: qty_approved of 0 rejects it, less than "
        "requested approves part. The request becomes approved, partially_approved or "
        "rejected. Approval moves no stock." + _STATE + _KEY
    ),
)
def review_request(
    request_id: UUID, body: ReviewResupplyRequest, idempotency_key: IdempotencyKey
) -> ResupplyResponse:
    not_implemented()
