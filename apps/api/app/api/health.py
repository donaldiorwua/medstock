from typing import Literal

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbDep, SettingsDep
from app.core.error_catalogue import ErrorCode
from app.core.errors import AppError
from app.core.schemas import ApiModel, Envelope, ErrorResponse

router = APIRouter(tags=["operations"])


class HealthData(ApiModel):
    status: Literal["ok"]
    database: Literal["ok"]
    environment: str


class HealthResponse(Envelope[HealthData]):
    pass


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": ErrorResponse}},
    summary="Liveness and database reachability",
)
def health(db: DbDep, settings: SettingsDep) -> HealthResponse:
    try:
        with db.unit_of_work() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise AppError(ErrorCode.DATABASE_UNAVAILABLE, "The database is not reachable.") from exc
    return HealthResponse(data=HealthData(status="ok", database="ok", environment=settings.app_env))
