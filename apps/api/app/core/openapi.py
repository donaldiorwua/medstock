"""OpenAPI customisation so the generated contract is stable and matches our conventions."""

from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

_HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def operation_id(route: APIRoute) -> str:
    """Operation ID = the route function's name (e.g. `health`).

    FastAPI's default (`health_api_v1_health_get`) would become the function name in
    Engineer B's generated client. Names must be unique; a test enforces it.
    """
    return route.name


def _use_error_envelope_for_422(schema: dict[str, Any]) -> None:
    """FastAPI documents 422 with its own HTTPValidationError shape, but this API answers
    validation failures with the standard error envelope. Make the contract say so."""
    for path_item in schema.get("paths", {}).values():
        for method in _HTTP_METHODS:
            operation = path_item.get(method)
            if operation and "422" in operation.get("responses", {}):
                operation["responses"]["422"] = {
                    "description": "Validation error (code VALIDATION_ERROR)",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                        }
                    },
                }
    components = schema.get("components", {}).get("schemas", {})
    components.pop("HTTPValidationError", None)
    components.pop("ValidationError", None)


def _require_all_security_schemes(schema: dict[str, Any]) -> None:
    """FastAPI lists each security dependency as an alternative (OR). Our write endpoints
    need the session cookie AND the CSRF header, so merge them into one requirement."""
    for path_item in schema.get("paths", {}).values():
        for method in _HTTP_METHODS:
            operation = path_item.get(method)
            if operation and len(operation.get("security", [])) > 1:
                merged: dict[str, list[str]] = {}
                for requirement in operation["security"]:
                    merged.update(requirement)
                operation["security"] = [merged]


def install_openapi_customisation(app: FastAPI) -> None:
    original = app.openapi

    def customised() -> dict[str, Any]:
        first_time = app.openapi_schema is None
        schema = original()
        if first_time:
            _use_error_envelope_for_422(schema)
            _require_all_security_schemes(schema)
        return schema

    app.openapi = customised  # type: ignore[method-assign]
