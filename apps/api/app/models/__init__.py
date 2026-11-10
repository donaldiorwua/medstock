"""Import every model module here so Alembic autogenerate can see all tables.

Models hold columns and constraints only. Business rules live in services.
"""

from app.models.audit import AuditRecord, IdempotencyKey
from app.models.base import Base, UUIDPrimaryKeyMixin
from app.models.catalogue import Batch, Item, StockThreshold
from app.models.identity import Facility, User, UserFacilityRole, UserSession
from app.models.stock import StockBalance, StockMovement
from app.models.workflow import (
    Discrepancy,
    ReceiptLine,
    ResupplyRequest,
    ResupplyRequestLine,
    Shipment,
    ShipmentLine,
)

__all__ = [
    "AuditRecord",
    "Base",
    "Batch",
    "Discrepancy",
    "Facility",
    "IdempotencyKey",
    "Item",
    "ReceiptLine",
    "ResupplyRequest",
    "ResupplyRequestLine",
    "Shipment",
    "ShipmentLine",
    "StockBalance",
    "StockMovement",
    "StockThreshold",
    "UUIDPrimaryKeyMixin",
    "User",
    "UserFacilityRole",
    "UserSession",
]
