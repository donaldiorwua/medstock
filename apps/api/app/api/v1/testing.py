"""Test-only endpoints. create_app registers this router only when APP_ENV is test or e2e;
in every other environment these URLs do not exist (404)."""

from fastapi import APIRouter

from app.api.support import not_implemented
from app.schemas.operations import ResetResponse, SeedRequest, SeedResponse

router = APIRouter(
    prefix="/test",
    tags=["test-only"],
    # No session: end-to-end runs reset the data (and with it every session) before logging in.
)

_ONLY = {"x-environments": ["test", "e2e"]}


@router.post(
    "/reset",
    response_model=ResetResponse,
    openapi_extra=_ONLY,
    summary="Empty the database (test and e2e only)",
    description="Deletes all data but keeps the schema. Exists only when APP_ENV is test or e2e.",
)
def reset_test_data() -> ResetResponse:
    not_implemented()


@router.post(
    "/seed",
    response_model=SeedResponse,
    openapi_extra=_ONLY,
    summary="Load a fictional dataset (test and e2e only)",
    description="Idempotent. Exists only when APP_ENV is test or e2e.",
)
def seed_test_data(body: SeedRequest) -> SeedResponse:
    not_implemented()
