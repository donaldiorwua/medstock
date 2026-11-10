from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.security import READ_AUTH
from app.api.support import error_responses, not_implemented
from app.schemas.common import PageDep
from app.schemas.operations import AuditListResponse, ReconciliationResponse

router = APIRouter()


@router.get(
    "/audit",
    tags=["audit"],
    response_model=AuditListResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 403),
    summary="Audit history",
    description=(
        "Admin only. Who did what and when, newest first. Every change made through the "
        "API writes one record in the same transaction as the change."
    ),
)
def list_audit(
    page: PageDep,
    facility_id: UUID | None = None,
    actor_id: UUID | None = None,
    entity_type: Annotated[str | None, Query(max_length=60)] = None,
    entity_id: UUID | None = None,
    date_from: Annotated[date | None, Query(description="On or after.")] = None,
    date_to: Annotated[date | None, Query(description="On or before.")] = None,
) -> AuditListResponse:
    not_implemented()


@router.get(
    "/admin/reconciliation",
    tags=["admin"],
    response_model=ReconciliationResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401, 403),
    summary="Reconcile balances with the ledger",
    description=(
        "Admin only. Compares every stock balance with the sum of its ledger rows. "
        "ok is true and differences is empty when the books agree."
    ),
)
def reconciliation(
    facility_id: Annotated[UUID | None, Query(description="Only this facility.")] = None,
) -> ReconciliationResponse:
    not_implemented()
