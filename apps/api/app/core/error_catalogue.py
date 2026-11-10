"""The error catalogue: every error code the API can return, with its HTTP status.

AppError takes an ErrorCode and reads the status from CATALOGUE, so a code and its status
can never disagree. docs/contract/errors.json is generated from this module.

Adding a code is an additive contract change. Renaming or removing one is breaking.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

EXAMPLE_REQUEST_ID = "3f2c9d1e8a7b4c6d9e0f1a2b3c4d5e6f"


class ErrorCode(StrEnum):
    # Generic
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    HTTP_ERROR = "HTTP_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    RATE_LIMITED = "RATE_LIMITED"
    # Authentication and authorisation
    UNAUTHENTICATED = "UNAUTHENTICATED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    PASSWORD_CHANGE_REQUIRED = "PASSWORD_CHANGE_REQUIRED"
    CSRF_FAILED = "CSRF_FAILED"
    FORBIDDEN = "FORBIDDEN"
    # Idempotency
    IDEMPOTENCY_KEY_REQUIRED = "IDEMPOTENCY_KEY_REQUIRED"
    IDEMPOTENCY_KEY_CONFLICT = "IDEMPOTENCY_KEY_CONFLICT"
    # Concurrency and workflow
    CONFLICT = "CONFLICT"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    # Stock rules
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    BATCH_EXPIRED = "BATCH_EXPIRED"
    BATCH_QUARANTINED = "BATCH_QUARANTINED"
    BACKDATE_LIMIT_EXCEEDED = "BACKDATE_LIMIT_EXCEEDED"
    OPENING_STOCK_EXISTS = "OPENING_STOCK_EXISTS"
    REVERSAL_NOT_ALLOWED = "REVERSAL_NOT_ALLOWED"
    # Data protection
    PATIENT_DATA_DETECTED = "PATIENT_DATA_DETECTED"


@dataclass(frozen=True, slots=True)
class ErrorSpec:
    http_status: int
    meaning: str
    example_message: str
    example_details: list[dict[str, Any]] | dict[str, Any] | None = None


_ITEM = "7d1c5a52-2b61-4f0e-9d0a-5b8f3c2e1a10"
_BATCH = "c4a9e6b0-8f33-4a57-b1d2-0e6a9f4d7c21"

CATALOGUE: dict[ErrorCode, ErrorSpec] = {
    ErrorCode.VALIDATION_ERROR: ErrorSpec(
        422,
        "The request failed validation. details lists each offending field path.",
        "The request is invalid.",
        [{"path": "quantity", "code": "int_parsing", "message": "Input should be a valid integer"}],
    ),
    ErrorCode.NOT_FOUND: ErrorSpec(
        404,
        "The resource does not exist, or belongs to a facility the caller cannot see.",
        "Not Found",
    ),
    ErrorCode.METHOD_NOT_ALLOWED: ErrorSpec(
        405, "The URL exists but does not accept this HTTP method.", "Method Not Allowed"
    ),
    ErrorCode.HTTP_ERROR: ErrorSpec(
        400,
        "A framework-level HTTP error with no more specific code. "
        "The response keeps the original HTTP status.",
        "Bad Request",
    ),
    ErrorCode.INTERNAL_ERROR: ErrorSpec(
        500,
        "An unexpected server error. Quote the request_id when reporting it.",
        "An unexpected error occurred.",
    ),
    ErrorCode.DATABASE_UNAVAILABLE: ErrorSpec(
        503,
        "The database cannot be reached right now. Retry later.",
        "The database is not reachable.",
    ),
    ErrorCode.NOT_IMPLEMENTED: ErrorSpec(
        501,
        "The endpoint is part of the contract but has not been built yet.",
        "This endpoint is not implemented yet.",
    ),
    ErrorCode.RATE_LIMITED: ErrorSpec(
        429,
        "Too many requests from this client. Retry after the indicated delay.",
        "Too many requests.",
        {"retry_after_seconds": 30},
    ),
    ErrorCode.UNAUTHENTICATED: ErrorSpec(
        401, "No valid session. Log in again.", "Authentication is required."
    ),
    ErrorCode.INVALID_CREDENTIALS: ErrorSpec(
        401,
        "Email or password is wrong. Deliberately does not say which.",
        "Email or password is incorrect.",
    ),
    ErrorCode.ACCOUNT_LOCKED: ErrorSpec(
        423,
        "Too many failed logins. The account is locked for a fixed period.",
        "The account is temporarily locked.",
        {"retry_after_seconds": 900},
    ),
    ErrorCode.PASSWORD_CHANGE_REQUIRED: ErrorSpec(
        403,
        "A temporary password is in use. Only change-password and logout are allowed.",
        "You must change your password before continuing.",
    ),
    ErrorCode.CSRF_FAILED: ErrorSpec(
        403,
        "The CSRF token is missing or wrong on a mutating request.",
        "The CSRF token is missing or invalid.",
    ),
    ErrorCode.FORBIDDEN: ErrorSpec(
        403,
        "The caller is signed in and may see this resource but may not perform this action.",
        "You are not allowed to perform this action.",
    ),
    ErrorCode.IDEMPOTENCY_KEY_REQUIRED: ErrorSpec(
        400,
        "A mutating stock endpoint was called without an Idempotency-Key header.",
        "The Idempotency-Key header is required.",
    ),
    ErrorCode.IDEMPOTENCY_KEY_CONFLICT: ErrorSpec(
        409,
        "The same Idempotency-Key was reused with a different request body.",
        "This Idempotency-Key was already used with a different request.",
    ),
    ErrorCode.CONFLICT: ErrorSpec(
        409,
        "The request conflicts with current data, for example a duplicate unique value.",
        "A record with this value already exists.",
        {"field": "email"},
    ),
    ErrorCode.VERSION_CONFLICT: ErrorSpec(
        409,
        "The record changed since the caller loaded it. Reload and retry.",
        "The record was changed by someone else.",
        {"expected_version": 3, "current_version": 4},
    ),
    ErrorCode.INVALID_TRANSITION: ErrorSpec(
        409,
        "The action is not allowed in the record's current status.",
        "This action is not allowed in the current status.",
        {"current_status": "draft", "action": "dispatch"},
    ),
    ErrorCode.INSUFFICIENT_STOCK: ErrorSpec(
        409,
        "Not enough usable stock in the batch. No stock was changed.",
        "Not enough stock available.",
        {"item_id": _ITEM, "batch_id": _BATCH, "requested": 60, "available": 40},
    ),
    ErrorCode.BATCH_EXPIRED: ErrorSpec(
        409,
        "The batch is past its expiry date and cannot be used.",
        "This batch has expired.",
        {"batch_id": _BATCH, "expiry_date": "2026-10-31"},
    ),
    ErrorCode.BATCH_QUARANTINED: ErrorSpec(
        409,
        "The stock is in quarantine and cannot be used until released.",
        "This stock is quarantined.",
        {"batch_id": _BATCH},
    ),
    ErrorCode.BACKDATE_LIMIT_EXCEEDED: ErrorSpec(
        422,
        "The movement date is further in the past than the allowed backdating window.",
        "The date is too far in the past.",
        {"max_backdate_days": 30},
    ),
    ErrorCode.OPENING_STOCK_EXISTS: ErrorSpec(
        409,
        "Opening stock can be recorded once per facility and batch.",
        "Opening stock was already recorded for this batch.",
        {"batch_id": _BATCH},
    ),
    ErrorCode.REVERSAL_NOT_ALLOWED: ErrorSpec(
        409,
        "The movement cannot be reversed, for example it was already reversed.",
        "This movement cannot be reversed.",
    ),
    ErrorCode.PATIENT_DATA_DETECTED: ErrorSpec(
        422,
        "A free-text field looks like it contains patient data. The value is not echoed back.",
        "Free text must not contain patient data.",
        [{"path": "notes", "code": "patient_data", "message": "Remove patient identifiers."}],
    ),
}
