from uuid import UUID

from fastapi import APIRouter

from app.api.security import READ_AUTH, WRITE_AUTH
from app.api.support import error_responses, not_implemented
from app.core.enums import FacilityType
from app.schemas.common import PageDep
from app.schemas.facilities import (
    CreateFacilityRequest,
    FacilityListResponse,
    FacilityResponse,
    ReplaceThresholdsRequest,
    ThresholdListResponse,
    ThresholdSetResponse,
    UpdateFacilityRequest,
)

router = APIRouter(prefix="/facilities")


@router.get(
    "",
    tags=["facilities"],
    response_model=FacilityListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401),
    summary="List facilities",
    description="Admins see every facility. Everyone else sees only the facilities they belong to.",
)
def list_facilities(
    page: PageDep,
    facility_type: FacilityType | None = None,
    is_active: bool | None = None,
) -> FacilityListResponse:
    not_implemented()


@router.post(
    "",
    tags=["facilities"],
    status_code=201,
    response_model=FacilityResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 409),
    summary="Create a facility",
    description="Admin only. The code must be unique (compared without regard to case).",
)
def create_facility(body: CreateFacilityRequest) -> FacilityResponse:
    not_implemented()


@router.patch(
    "/{facility_id}",
    tags=["facilities"],
    response_model=FacilityResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 404),
    summary="Update a facility",
    description="Admin only. The code and facility type cannot be changed.",
)
def update_facility(facility_id: UUID, body: UpdateFacilityRequest) -> FacilityResponse:
    not_implemented()


@router.get(
    "/{facility_id}/thresholds",
    tags=["thresholds"],
    response_model=ThresholdListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 403, 404),
    summary="List stock thresholds",
    description=(
        "One row per active item. Items without thresholds have null levels. "
        "Visible to members of the facility and admins."
    ),
)
def get_thresholds(facility_id: UUID, page: PageDep) -> ThresholdListResponse:
    not_implemented()


@router.put(
    "/{facility_id}/thresholds",
    tags=["thresholds"],
    response_model=ThresholdSetResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 404),
    summary="Replace stock thresholds",
    description=(
        "Admin and store manager only. Replaces the facility's thresholds with exactly "
        "this set. reorder_level must be at least critical_level."
    ),
)
def replace_thresholds(facility_id: UUID, body: ReplaceThresholdsRequest) -> ThresholdSetResponse:
    not_implemented()
