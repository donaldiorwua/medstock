from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.security import READ_AUTH, WRITE_AUTH
from app.api.support import error_responses, not_implemented
from app.schemas.common import PageDep
from app.schemas.items import (
    BatchListResponse,
    BatchResponse,
    CreateBatchRequest,
    CreateItemRequest,
    ItemListResponse,
    ItemResponse,
    UpdateItemRequest,
)

router = APIRouter()


@router.get(
    "/items",
    tags=["items"],
    response_model=ItemListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401),
    summary="List items",
    description="The item catalogue, ordered by name.",
)
def list_items(
    page: PageDep,
    q: Annotated[str | None, Query(max_length=100, description="Matches name or code.")] = None,
    is_active: bool | None = None,
) -> ItemListResponse:
    not_implemented()


@router.post(
    "/items",
    tags=["items"],
    status_code=201,
    response_model=ItemResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 409),
    summary="Create an item",
    description="Admin and store manager only. The code must be unique.",
)
def create_item(body: CreateItemRequest) -> ItemResponse:
    not_implemented()


@router.patch(
    "/items/{item_id}",
    tags=["items"],
    response_model=ItemResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 404),
    summary="Update an item",
    description="Admin and store manager only. The code and base unit cannot be changed.",
)
def update_item(item_id: UUID, body: UpdateItemRequest) -> ItemResponse:
    not_implemented()


@router.get(
    "/items/{item_id}/batches",
    tags=["batches"],
    response_model=BatchListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 404),
    summary="List batches of an item",
    description="Ordered by expiry date, soonest first.",
)
def list_item_batches(item_id: UUID, page: PageDep) -> BatchListResponse:
    not_implemented()


@router.post(
    "/batches",
    tags=["batches"],
    status_code=201,
    response_model=BatchResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 404, 409),
    summary="Create a batch",
    description=("Admin and store manager only. The batch number must be unique for the item."),
)
def create_batch(body: CreateBatchRequest) -> BatchResponse:
    not_implemented()
