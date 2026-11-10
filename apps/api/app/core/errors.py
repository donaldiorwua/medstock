"""One error shape for the whole API:

    {"error": {"code": "...", "message": "...", "details": ..., "request_id": "..."}}

Raise AppError(ErrorCode.X, "message") from services and routers. The HTTP status comes from
the error catalogue. Everything else (validation failures, unknown URLs, crashes) is converted
here so clients never see a framework default or a stack trace.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.error_catalogue import CATALOGUE, ErrorCode
from app.core.request_id import HEADER
from app.core.schemas import ErrorBody, ErrorDetails, ErrorResponse

logger = logging.getLogger("medstock.errors")

_HTTP_ERROR_CODES: dict[int, ErrorCode] = {
    401: ErrorCode.UNAUTHENTICATED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    429: ErrorCode.RATE_LIMITED,
}


class AppError(Exception):
    def __init__(self, code: ErrorCode, message: str, *, details: ErrorDetails = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = CATALOGUE[code].http_status
        self.details = details


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def error_response(
    request: Request,
    status_code: int,
    code: ErrorCode,
    message: str,
    details: ErrorDetails = None,
) -> JSONResponse:
    request_id = _request_id(request)
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details, request_id=request_id)
    )
    # Set the header here too: crashes are answered outside the request-ID middleware.
    headers = {HEADER: request_id} if request_id else None
    return JSONResponse(
        status_code=status_code, content=body.model_dump(mode="json"), headers=headers
    )


def _validation_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", ())]
        if loc and loc[0] == "body":
            loc = loc[1:]  # paths match the JSON body the client sent
        # The submitted value is deliberately not echoed back (it could be a password).
        details.append(
            {
                "path": ".".join(loc),
                "code": str(err.get("type", "invalid")),
                "message": str(err.get("msg", "")),
            }
        )
    return details


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return error_response(request, exc.status_code, exc.code, exc.message, exc.details)


def _is_missing_idempotency_key(exc: RequestValidationError) -> bool:
    for err in exc.errors():
        loc = tuple(err.get("loc", ()))
        if (
            len(loc) == 2
            and loc[0] == "header"
            and str(loc[1]).lower() == "idempotency-key"
            and err.get("type") == "missing"
        ):
            return True
    return False


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    if _is_missing_idempotency_key(exc):
        spec = CATALOGUE[ErrorCode.IDEMPOTENCY_KEY_REQUIRED]
        return error_response(
            request,
            spec.http_status,
            ErrorCode.IDEMPOTENCY_KEY_REQUIRED,
            spec.example_message,
        )
    return error_response(
        request,
        CATALOGUE[ErrorCode.VALIDATION_ERROR].http_status,
        ErrorCode.VALIDATION_ERROR,
        "The request is invalid.",
        _validation_details(exc),
    )


async def _handle_http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _HTTP_ERROR_CODES.get(exc.status_code, ErrorCode.HTTP_ERROR)
    response = error_response(request, exc.status_code, code, str(exc.detail))
    for name, value in (exc.headers or {}).items():  # e.g. the Allow header on a 405
        response.headers[name] = value
    return response


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error (request_id=%s)", _request_id(request), exc_info=exc)
    return error_response(
        request,
        CATALOGUE[ErrorCode.INTERNAL_ERROR].http_status,
        ErrorCode.INTERNAL_ERROR,
        "An unexpected error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
