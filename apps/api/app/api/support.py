"""Helpers shared by the route modules."""

from typing import Any, NoReturn

from app.core.error_catalogue import ErrorCode
from app.core.errors import AppError
from app.core.schemas import ErrorResponse

_ERROR_DESCRIPTIONS = {
    400: "Bad request",
    401: "Not signed in, or the session expired",
    403: "Not allowed (role, CSRF token, or password change required)",
    404: "Not found (or belongs to a facility the caller cannot see)",
    409: "Conflicts with current data or with the record's status",
    423: "Account locked",
    429: "Too many requests",
}


def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """Document which error statuses an endpoint can return (all use ErrorResponse)."""
    return {
        status: {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS[status]}
        for status in statuses
    }


def not_implemented() -> NoReturn:
    """Body of every stub route. A later milestone replaces the call, not the signature."""
    raise AppError(ErrorCode.NOT_IMPLEMENTED, "This endpoint is not implemented yet.")


_REPLAY_HEADER = {
    "Idempotent-Replay": {
        "description": (
            "Present and set to true when this response was replayed from an earlier "
            "request with the same Idempotency-Key. Nothing was posted a second time."
        ),
        "schema": {"type": "string", "enum": ["true"]},
    }
}


def _idempotent_responses(
    success_status: int, description: str, extra_statuses: tuple[int, ...]
) -> dict[int | str, dict[str, Any]]:
    responses = error_responses(400, 401, 403, 404, 409, *extra_statuses)
    responses[success_status] = {"description": description, "headers": _REPLAY_HEADER}
    return responses


def posting_responses(*extra_statuses: int) -> dict[int | str, dict[str, Any]]:
    """A stock-changing POST that creates something: 201 with the replay header, plus the
    errors every idempotent action can return."""
    return _idempotent_responses(201, "Posted", extra_statuses)


def action_responses(*extra_statuses: int) -> dict[int | str, dict[str, Any]]:
    """An idempotent action on an existing record: 200 with the replay header."""
    return _idempotent_responses(200, "Done", extra_statuses)
