from fastapi import APIRouter

from app.api.v1 import (
    auth,
    dashboard,
    discrepancies,
    facilities,
    items,
    operations,
    requests,
    shipments,
    stock,
    users,
)

v1_router = APIRouter()
for _module in (
    auth,
    users,
    facilities,
    items,
    stock,
    requests,
    shipments,
    discrepancies,
    dashboard,
    operations,
):
    v1_router.include_router(_module.router)

OPENAPI_TAGS = [
    {"name": "operations", "description": "Health and operational endpoints."},
    {"name": "auth", "description": "Login, logout, session and password."},
    {"name": "users", "description": "User accounts and facility roles (admin)."},
    {"name": "facilities", "description": "Central store and primary health centres."},
    {"name": "thresholds", "description": "Reorder and critical stock levels per facility."},
    {"name": "items", "description": "The item catalogue and base units."},
    {"name": "batches", "description": "Batches and expiry dates."},
    {"name": "stock", "description": "The stock register and stock-changing actions."},
    {"name": "movements", "description": "The append-only ledger and reversals."},
    {"name": "requests", "description": "Resupply requests: draft, submit, review, cancel."},
    {"name": "shipments", "description": "Allocation, dispatch and receipt of shipments."},
    {"name": "discrepancies", "description": "Shortfalls found at receipt, and their resolution."},
    {"name": "dashboard", "description": "Summary figures and alerts."},
    {"name": "exports", "description": "CSV exports."},
    {"name": "audit", "description": "The audit trail (admin)."},
    {"name": "admin", "description": "Administrative checks such as reconciliation."},
    {"name": "test-only", "description": "Exist only when APP_ENV is test or e2e."},
]
