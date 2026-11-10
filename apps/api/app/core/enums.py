"""Shared vocabulary of the API (contract section 5.6).

Every status, role and reason code the API can return lives here, once. Models store these
as VARCHAR + CHECK (core/types.string_enum), schemas expose them to clients, and
docs/contract/enums.json is generated from ALL_ENUMS.

Rules:
- Values are lowercase snake_case strings.
- Adding a value is an additive change; renaming or removing one is a breaking change.
- Every enum defined in this module must be listed in ALL_ENUMS (a test enforces it).
"""

from enum import StrEnum


class Role(StrEnum):
    """What a user may do at a facility."""

    ADMIN = "admin"  # manage users, facilities and items
    STORE_MANAGER = "store_manager"  # central store: review requests, dispatch, resolve
    PHC_OFFICER = "phc_officer"  # PHC: record stock, raise requests, confirm receipt
    VIEWER = "viewer"  # read-only oversight


class FacilityType(StrEnum):
    """Kind of facility in the supply chain."""

    CENTRAL_STORE = "central_store"
    PHC = "phc"


class MovementType(StrEnum):
    """Why a row was appended to the stock ledger."""

    OPENING = "opening"
    RECEIPT = "receipt"  # stock received from outside the system
    ISSUE = "issue"  # stock used or handed out at a facility
    ADJUSTMENT = "adjustment"
    QUARANTINE = "quarantine"
    RELEASE = "release"  # quarantine released back to available
    EXPIRY_WRITEOFF = "expiry_writeoff"
    REVERSAL = "reversal"
    DISPATCH = "dispatch"  # central store sends a shipment
    SHIPMENT_RECEIPT = "shipment_receipt"  # PHC confirms what arrived
    DISCREPANCY_WRITE_OFF = "discrepancy_write_off"
    DISCREPANCY_RECOVERY_TO_PHC = "discrepancy_recovery_to_phc"
    DISCREPANCY_RECOVERY_TO_STORE = "discrepancy_recovery_to_store"


class RequestStatus(StrEnum):
    """Lifecycle of a resupply request (derived from its lines where relevant)."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    REJECTED = "rejected"
    DISPATCHED = "dispatched"
    RECEIVED = "received"
    DISCREPANCY_OPEN = "discrepancy_open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class LineStatus(StrEnum):
    """Status of one item line inside a resupply request."""

    PENDING = "pending"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    REJECTED = "rejected"
    DISPATCHED = "dispatched"
    RECEIVED = "received"
    SHORT_RECEIVED = "short_received"


class ShipmentStatus(StrEnum):
    """Lifecycle of a shipment."""

    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    RECEIVED_WITH_DISCREPANCY = "received_with_discrepancy"


class DiscrepancyStatus(StrEnum):
    """Whether a shipment shortfall is still unresolved."""

    OPEN = "open"
    RESOLVED = "resolved"


class DiscrepancyResolution(StrEnum):
    """How a discrepancy was resolved, with the stock effect each one has."""

    WRITTEN_OFF = "written_off"
    RECOVERED_TO_PHC = "recovered_to_phc"
    RECOVERED_TO_STORE = "recovered_to_store"


class AlertLevel(StrEnum):
    """Stock level of an item at a facility, derived from its thresholds."""

    OK = "ok"
    REORDER = "reorder"
    CRITICAL = "critical"
    OUT_OF_STOCK = "out_of_stock"


class AdjustmentReason(StrEnum):
    """Reason code required on every stock adjustment."""

    COUNT_CORRECTION = "count_correction"
    DAMAGE = "damage"
    LOSS = "loss"
    FOUND = "found"
    ENTRY_ERROR = "entry_error"
    OTHER = "other"


class RequestAction(StrEnum):
    """Actions a user may take on a resupply request (its allowed_actions)."""

    EDIT = "edit"
    SUBMIT = "submit"
    CANCEL = "cancel"
    REVIEW = "review"
    DISPATCH = "dispatch"


class ShipmentAction(StrEnum):
    """Actions a user may take on a shipment (its allowed_actions)."""

    CONFIRM_RECEIPT = "confirm_receipt"


class DiscrepancyAction(StrEnum):
    """Actions a user may take on a discrepancy (its allowed_actions)."""

    RESOLVE = "resolve"


class AlertType(StrEnum):
    """Kind of alert on the dashboard."""

    STOCK_LEVEL = "stock_level"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED_STOCK = "expired_stock"
    FACILITY_STALE = "facility_stale"
    DISCREPANCY_OPEN = "discrepancy_open"


class ExportResource(StrEnum):
    """What a CSV export contains."""

    STOCK = "stock"
    MOVEMENTS = "movements"
    REQUESTS = "requests"
    SHIPMENTS = "shipments"
    DISCREPANCIES = "discrepancies"


class SeedProfile(StrEnum):
    """Which fictional dataset the test-only seed endpoint loads."""

    DEMO = "demo"
    E2E = "e2e"


class StockBucket(StrEnum):
    """Which balance a ledger row changes. Quarantine and release post one row to each."""

    AVAILABLE = "available"
    QUARANTINED = "quarantined"


class MovementAction(StrEnum):
    """Actions a user may take on a ledger row (listed in its allowed_actions)."""

    REVERSE = "reverse"


class WarningCode(StrEnum):
    """Non-fatal notes the API can attach to a successful response (meta.warnings)."""

    ADJUSTMENT_NEEDS_REVIEW = "adjustment_needs_review"
    BATCH_EXPIRING_SOON = "batch_expiring_soon"
    FACILITY_DATA_STALE = "facility_data_stale"


ALL_ENUMS: tuple[type[StrEnum], ...] = (
    AdjustmentReason,
    AlertLevel,
    AlertType,
    DiscrepancyAction,
    DiscrepancyResolution,
    DiscrepancyStatus,
    ExportResource,
    FacilityType,
    LineStatus,
    MovementAction,
    MovementType,
    RequestAction,
    RequestStatus,
    Role,
    SeedProfile,
    ShipmentAction,
    ShipmentStatus,
    StockBucket,
    WarningCode,
)
