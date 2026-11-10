from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.security import READ_AUTH, WRITE_AUTH
from app.api.support import error_responses, not_implemented
from app.core.enums import Role
from app.schemas.common import PageDep
from app.schemas.users import (
    CreateUserRequest,
    ReplaceRolesRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=UserListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 403),
    summary="List users",
    description="Admin only. Newest first.",
)
def list_users(
    page: PageDep,
    q: Annotated[str | None, Query(max_length=100, description="Matches name or email.")] = None,
    facility_id: Annotated[UUID | None, Query(description="Users with a role here.")] = None,
    role: Annotated[Role | None, Query(description="Users holding this role.")] = None,
    is_active: bool | None = None,
) -> UserListResponse:
    not_implemented()


@router.post(
    "",
    status_code=201,
    response_model=UserResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 409),
    summary="Create a user",
    description=(
        "Admin only. The user starts with a temporary password and must change it at "
        "first login. An email already in use returns CONFLICT."
    ),
)
def create_user(body: CreateUserRequest) -> UserResponse:
    not_implemented()


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 404),
    summary="Update a user",
    description=(
        "Admin only. Change the name, deactivate or reactivate, reset the password "
        "(forces a change at next login), or clear a lockout. Send only what changes."
    ),
)
def update_user(user_id: UUID, body: UpdateUserRequest) -> UserResponse:
    not_implemented()


@router.put(
    "/{user_id}/roles",
    response_model=UserResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 404),
    summary="Replace a user's roles",
    description=(
        "Admin only. Sets the complete list of facility roles. Facilities not listed "
        "are removed from the user."
    ),
)
def replace_user_roles(user_id: UUID, body: ReplaceRolesRequest) -> UserResponse:
    not_implemented()
