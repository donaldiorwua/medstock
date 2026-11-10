from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.api.security import READ_AUTH
from app.api.support import error_responses, not_implemented
from app.core.enums import AlertType, ExportResource
from app.schemas.common import PageDep
from app.schemas.dashboard import AlertListResponse, DashboardSummaryResponse

router = APIRouter()


class CsvResponse(Response):
    media_type = "text/csv"


_CSV_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "A CSV file with a header row.",
        "content": {"text/csv": {"schema": {"type": "string"}}},
        "headers": {
            "Content-Disposition": {
                "description": 'attachment; filename="<resource>-<date>.csv"',
                "schema": {"type": "string"},
            }
        },
    }
}


@router.get(
    "/dashboard/summary",
    tags=["dashboard"],
    response_model=DashboardSummaryResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 404),
    summary="Dashboard summary",
    description=(
        "Per-facility stock and expiry counts, freshness, workflow counts and the "
        "unresolved in-transit quantity per item. Store managers and admins see every "
        "facility; others see their own. Pass facility_id to narrow it."
    ),
)
def dashboard_summary(
    facility_id: Annotated[UUID | None, Query(description="Only this facility.")] = None,
) -> DashboardSummaryResponse:
    not_implemented()


@router.get(
    "/dashboard/alerts",
    tags=["dashboard"],
    response_model=AlertListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 404),
    summary="Dashboard alerts",
    description=(
        "Stock levels at or below the reorder level, batches expiring within 90 days, "
        "expired stock still on the shelf, stale facilities and open discrepancies. "
        "Most urgent first."
    ),
)
def dashboard_alerts(
    page: PageDep,
    facility_id: Annotated[UUID | None, Query(description="Only this facility.")] = None,
    type: Annotated[AlertType | None, Query(description="Only this kind of alert.")] = None,
) -> AlertListResponse:
    not_implemented()


@router.get(
    "/exports/{resource}.csv",
    tags=["exports"],
    response_class=CsvResponse,
    response_model=None,
    dependencies=READ_AUTH,
    responses={**error_responses(401, 403, 404), **_CSV_RESPONSE},
    summary="Export a resource as CSV",
    description=(
        "Members of a facility export that facility's data; admins and store managers "
        "can export everything. Cells that start with =, +, - or @ are prefixed with an "
        "apostrophe so spreadsheets do not run them as formulas. date_from and date_to "
        "apply to movements, requests, shipments and discrepancies."
    ),
)
def export_csv(
    resource: ExportResource,
    facility_id: Annotated[UUID | None, Query(description="Only this facility.")] = None,
    date_from: Annotated[date | None, Query(description="From this date.")] = None,
    date_to: Annotated[date | None, Query(description="Up to this date.")] = None,
) -> Response:
    not_implemented()
