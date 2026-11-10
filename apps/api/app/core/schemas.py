"""Shared API schema conventions (blueprint sections 5 and 6)."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.error_catalogue import ErrorCode

ErrorDetails = list[dict[str, Any]] | dict[str, Any] | None


class ApiModel(BaseModel):
    """Base for every request and response schema: unknown fields are rejected, not ignored."""

    model_config = ConfigDict(extra="forbid")


class Envelope[T](ApiModel):
    """Success envelope. Every endpoint defines a NAMED subclass of this
    (for example `class HealthResponse(Envelope[HealthData])`) so generated clients
    get a readable type name."""

    data: T


class ErrorBody(ApiModel):
    code: ErrorCode
    message: str
    details: ErrorDetails = None
    request_id: str | None = None


class ErrorResponse(ApiModel):
    error: ErrorBody
