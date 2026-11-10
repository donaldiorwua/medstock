"""Guards for the contract (docs/contract/): generated files in sync, vocabulary consistent,
examples valid against the real response models."""

import inspect
import json
import re
from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.contract import __main__ as contract_cli
from app.contract.build import (
    CONTRACT_DIR,
    CONTRACT_FILES,
    check,
    enums_document,
    errors_document,
    export,
    generate,
)
from app.core import enums as enums_module
from app.core.enums import ALL_ENUMS
from app.core.error_catalogue import CATALOGUE, ErrorCode
from app.core.errors import AppError
from app.core.schemas import ErrorResponse

HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
EXAMPLE_FILES = sorted((CONTRACT_DIR / "examples").glob("*/*.json"))


def operations(spec: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for path, item in spec["paths"].items():
        for method in HTTP_METHODS:
            if method in item:
                yield path, method, item[method]


def walk_refs(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value
            else:
                yield from walk_refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_refs(value)


# ---------------------------------------------------------------- generated files


def test_committed_contract_files_match_the_code() -> None:
    problems = check()
    assert not problems, (
        "docs/contract is out of date. Run `python -m app.contract export` and commit.\n\n"
        + "\n".join(problems)
    )


def test_export_then_check_round_trip(tmp_path: Path) -> None:
    export(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(CONTRACT_FILES)
    assert check(tmp_path) == []


def test_check_reports_a_missing_file_and_a_changed_file(tmp_path: Path) -> None:
    export(tmp_path)
    (tmp_path / "errors.json").unlink()
    (tmp_path / "openapi.json").write_text("{}\n", encoding="utf-8")
    problems = check(tmp_path)
    assert any(p.startswith("errors.json: file is missing") for p in problems)
    assert any(p.startswith("openapi.json: differs") for p in problems)


def test_cli_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert contract_cli.main(["export", "--dir", str(tmp_path)]) == 0
    assert contract_cli.main(["check", "--dir", str(tmp_path)]) == 0
    (tmp_path / "enums.json").write_text("{}\n", encoding="utf-8")
    assert contract_cli.main(["check", "--dir", str(tmp_path)]) == 1
    assert "python -m app.contract export" in capsys.readouterr().err


def test_generation_is_deterministic() -> None:
    from app.contract.build import generate

    assert generate() == generate()


# ---------------------------------------------------------------- openapi shape


def test_operation_ids_are_unique_and_are_plain_function_names(api_app: FastAPI) -> None:
    ids = [op["operationId"] for _, _, op in operations(api_app.openapi())]
    assert len(ids) == len(set(ids)), "operation IDs must be unique"
    for operation_id in ids:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", operation_id), operation_id
        # FastAPI's default IDs embed the URL and method (health_api_v1_health_get).
        assert "api_v1" not in operation_id, f"{operation_id} looks like a default ID"
    assert "health" in ids


def test_info_version_is_the_contract_version(api_app: FastAPI) -> None:
    from app.contract import CONTRACT_VERSION

    assert api_app.openapi()["info"]["version"] == CONTRACT_VERSION


def test_no_dangling_schema_references(api_app: FastAPI) -> None:
    spec = api_app.openapi()
    defined = set(spec["components"]["schemas"])
    for ref in walk_refs(spec):
        assert ref.startswith("#/components/schemas/")
        assert ref.rsplit("/", 1)[1] in defined, f"{ref} is not defined"


def test_validation_errors_are_documented_with_the_error_envelope(api_app: FastAPI) -> None:
    spec = api_app.openapi()
    assert "HTTPValidationError" not in spec["components"]["schemas"]
    assert "ValidationError" not in spec["components"]["schemas"]
    for _, _, op in operations(spec):
        if "422" in op["responses"]:
            schema = op["responses"]["422"]["content"]["application/json"]["schema"]
            assert schema == {"$ref": "#/components/schemas/ErrorResponse"}


def test_error_code_enum_in_openapi_matches_the_catalogue(api_app: FastAPI) -> None:
    schemas = api_app.openapi()["components"]["schemas"]
    assert set(schemas["ErrorCode"]["enum"]) == {c.value for c in ErrorCode}
    assert schemas["ErrorBody"]["properties"]["code"] == {"$ref": "#/components/schemas/ErrorCode"}


# ---------------------------------------------------------------- error catalogue


def test_every_code_has_exactly_one_catalogue_entry() -> None:
    assert set(CATALOGUE) == set(ErrorCode)


@pytest.mark.parametrize("code", list(ErrorCode), ids=lambda c: c.value)
def test_catalogue_entry_is_well_formed(code: ErrorCode) -> None:
    spec = CATALOGUE[code]
    assert 400 <= spec.http_status <= 599
    assert spec.meaning and spec.example_message
    assert re.fullmatch(r"[A-Z][A-Z0-9_]*", code.value)
    assert code.value == code.name


@pytest.mark.parametrize("code", list(ErrorCode), ids=lambda c: c.value)
def test_app_error_takes_its_status_from_the_catalogue(code: ErrorCode) -> None:
    assert AppError(code, "x").status_code == CATALOGUE[code].http_status


@pytest.mark.parametrize("code", list(ErrorCode), ids=lambda c: c.value)
def test_every_catalogue_example_is_a_valid_error_response(code: ErrorCode) -> None:
    example = errors_document()["errors"][code.value]["example"]
    parsed = ErrorResponse.model_validate(example)
    assert parsed.error.code is code


# ---------------------------------------------------------------- enums


def test_every_enum_in_the_module_is_registered() -> None:
    defined = {
        obj
        for _, obj in inspect.getmembers(enums_module, inspect.isclass)
        if issubclass(obj, StrEnum) and obj.__module__ == enums_module.__name__
    }
    assert defined == set(ALL_ENUMS)


@pytest.mark.parametrize("enum_cls", ALL_ENUMS, ids=lambda e: e.__name__)
def test_enum_values_are_snake_case_and_unique(enum_cls: type[StrEnum]) -> None:
    values = [m.value for m in enum_cls]
    assert values, "an enum must have at least one value"
    assert len(values) == len(set(values))
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", v) for v in values)
    assert (enum_cls.__doc__ or "").strip(), "every enum needs a one-line docstring"


def test_enums_document_lists_every_enum() -> None:
    document = enums_document()["enums"]
    assert set(document) == {e.__name__ for e in ALL_ENUMS}


# ---------------------------------------------------------------- examples


def find_operation(spec: dict[str, Any], operation_id: str) -> tuple[str, str, dict[str, Any]]:
    for path, method, op in operations(spec):
        if op["operationId"] == operation_id:
            return path, method, op
    raise AssertionError(f"No operation with operationId {operation_id!r}")


def test_every_operation_has_a_success_example_and_no_example_is_orphaned(
    api_app: FastAPI,
) -> None:
    ids = {op["operationId"] for _, _, op in operations(api_app.openapi())}
    with_success = {p.parent.name for p in EXAMPLE_FILES if p.name.startswith("2")}
    assert ids - with_success == set(), "operations without a 2xx example"
    assert {p.parent.name for p in EXAMPLE_FILES} <= ids, "examples for unknown operations"


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_example_matches_the_contract(path: Path, api_app: FastAPI) -> None:
    example = json.loads(path.read_text(encoding="utf-8"))
    assert set(example) == {"description", "request", "response"}
    assert path.name == f"{example['response']['status']}.json"

    spec = api_app.openapi()
    url_template, method, operation = find_operation(spec, path.parent.name)

    request = example["request"]
    assert request["method"] == method.upper()
    pattern = "[^/]+".join(re.escape(part) for part in re.split(r"\{[^}]*\}", url_template))
    assert re.fullmatch(pattern, request["path"]), "example path does not fit the URL template"

    status = example["response"]["status"]
    body = example["response"]["body"]
    assert str(status) in operation["responses"], f"status {status} is not declared"

    if 200 <= status < 300:
        content_type = example["response"].get("content_type", "application/json")
        declared_content = operation["responses"][str(status)]["content"]
        assert content_type in declared_content, f"{content_type} is not declared"
        if content_type != "application/json":
            assert isinstance(body, str) and body.strip(), "non-JSON examples are text"
            return
        response_schema = declared_content[content_type]["schema"]
        # Attach the components so "$ref": "#/components/schemas/X" resolves.
        schema = {**response_schema, "components": spec["components"]}
        errors = sorted(
            Draft202012Validator(schema).iter_errors(body), key=lambda e: list(e.absolute_path)
        )
        assert not errors, [f"{list(e.absolute_path)}: {e.message}" for e in errors]

        request_body = request.get("body")
        if request_body is not None:
            declared = operation.get("requestBody")
            assert declared is not None, "example has a request body but the operation has none"
            req_schema = {
                **declared["content"]["application/json"]["schema"],
                "components": spec["components"],
            }
            req_errors = sorted(
                Draft202012Validator(req_schema).iter_errors(request_body),
                key=lambda e: list(e.absolute_path),
            )
            assert not req_errors, [f"{list(e.absolute_path)}: {e.message}" for e in req_errors]
    else:
        parsed = ErrorResponse.model_validate(body)
        if parsed.error.code is not ErrorCode.HTTP_ERROR:
            assert CATALOGUE[parsed.error.code].http_status == status


# ---------------------------------------------------------------- the planned surface

# Every operation the contract is expected to contain so far: operationId -> (METHOD, path).
# Each A2b slice extends this. An operation not listed here fails the test, so nothing
# slips into the contract unplanned.
EXPECTED_OPERATIONS: dict[str, tuple[str, str]] = {
    "health": ("GET", "/api/v1/health"),
    "login": ("POST", "/api/v1/auth/login"),
    "logout": ("POST", "/api/v1/auth/logout"),
    "me": ("GET", "/api/v1/auth/me"),
    "csrf": ("GET", "/api/v1/auth/csrf"),
    "change_password": ("POST", "/api/v1/auth/change-password"),
    "list_users": ("GET", "/api/v1/users"),
    "create_user": ("POST", "/api/v1/users"),
    "update_user": ("PATCH", "/api/v1/users/{user_id}"),
    "replace_user_roles": ("PUT", "/api/v1/users/{user_id}/roles"),
    "list_facilities": ("GET", "/api/v1/facilities"),
    "create_facility": ("POST", "/api/v1/facilities"),
    "update_facility": ("PATCH", "/api/v1/facilities/{facility_id}"),
    "get_thresholds": ("GET", "/api/v1/facilities/{facility_id}/thresholds"),
    "replace_thresholds": ("PUT", "/api/v1/facilities/{facility_id}/thresholds"),
    "list_items": ("GET", "/api/v1/items"),
    "create_item": ("POST", "/api/v1/items"),
    "update_item": ("PATCH", "/api/v1/items/{item_id}"),
    "list_item_batches": ("GET", "/api/v1/items/{item_id}/batches"),
    "create_batch": ("POST", "/api/v1/batches"),
    "list_stock": ("GET", "/api/v1/facilities/{facility_id}/stock"),
    "get_stock_item": ("GET", "/api/v1/facilities/{facility_id}/stock/items/{item_id}"),
    "list_movements": ("GET", "/api/v1/facilities/{facility_id}/movements"),
    "post_opening_stock": ("POST", "/api/v1/facilities/{facility_id}/stock/opening"),
    "post_receipt": ("POST", "/api/v1/facilities/{facility_id}/stock/receipts"),
    "post_issue": ("POST", "/api/v1/facilities/{facility_id}/stock/issues"),
    "post_adjustment": ("POST", "/api/v1/facilities/{facility_id}/stock/adjustments"),
    "post_quarantine": ("POST", "/api/v1/facilities/{facility_id}/stock/quarantine"),
    "post_release": ("POST", "/api/v1/facilities/{facility_id}/stock/release"),
    "post_expiry_writeoff": ("POST", "/api/v1/facilities/{facility_id}/stock/expiry-writeoffs"),
    "reverse_movement": ("POST", "/api/v1/movements/{movement_id}/reversal"),
    "create_request": ("POST", "/api/v1/requests"),
    "list_requests": ("GET", "/api/v1/requests"),
    "get_request": ("GET", "/api/v1/requests/{request_id}"),
    "update_request": ("PATCH", "/api/v1/requests/{request_id}"),
    "submit_request": ("POST", "/api/v1/requests/{request_id}/submit"),
    "cancel_request": ("POST", "/api/v1/requests/{request_id}/cancel"),
    "review_request": ("POST", "/api/v1/requests/{request_id}/review"),
    "get_allocation_suggestion": ("GET", "/api/v1/requests/{request_id}/allocation-suggestion"),
    "dispatch_request": ("POST", "/api/v1/requests/{request_id}/dispatch"),
    "list_shipments": ("GET", "/api/v1/shipments"),
    "get_shipment": ("GET", "/api/v1/shipments/{shipment_id}"),
    "confirm_shipment_receipt": ("POST", "/api/v1/shipments/{shipment_id}/receipt"),
    "list_discrepancies": ("GET", "/api/v1/discrepancies"),
    "get_discrepancy": ("GET", "/api/v1/discrepancies/{discrepancy_id}"),
    "resolve_discrepancy": ("POST", "/api/v1/discrepancies/{discrepancy_id}/resolve"),
    "dashboard_summary": ("GET", "/api/v1/dashboard/summary"),
    "dashboard_alerts": ("GET", "/api/v1/dashboard/alerts"),
    "export_csv": ("GET", "/api/v1/exports/{resource}.csv"),
    "list_audit": ("GET", "/api/v1/audit"),
    "reconciliation": ("GET", "/api/v1/admin/reconciliation"),
    "reset_test_data": ("POST", "/api/v1/test/reset"),
    "seed_test_data": ("POST", "/api/v1/test/seed"),
}

# Operations that change stock or workflow state. They must declare the required
# Idempotency-Key header and the Idempotent-Replay response header. Later slices extend it.
IDEMPOTENT_OPERATIONS = {
    "post_opening_stock",
    "post_receipt",
    "post_issue",
    "post_adjustment",
    "post_quarantine",
    "post_release",
    "post_expiry_writeoff",
    "reverse_movement",
    "submit_request",
    "cancel_request",
    "review_request",
    "dispatch_request",
    "confirm_shipment_receipt",
    "resolve_discrepancy",
}

# Operations that are really implemented. Every other one must still answer 501.
# When a milestone implements an endpoint, add its operationId here.
IMPLEMENTED = {"health"}

# Operations that need no session (health, and login which creates one).
PUBLIC_OPERATIONS = {"health", "login", "reset_test_data", "seed_test_data"}


def test_the_contract_contains_exactly_the_planned_operations(api_app: FastAPI) -> None:
    actual = {
        op["operationId"]: (method.upper(), path)
        for path, method, op in operations(api_app.openapi())
    }
    assert actual == EXPECTED_OPERATIONS


def test_security_requirements_follow_the_convention(api_app: FastAPI) -> None:
    spec = api_app.openapi()
    assert set(spec["components"]["securitySchemes"]) == {"sessionCookie", "csrfToken"}
    for _, method, op in operations(spec):
        operation_id = op["operationId"]
        security = op.get("security")
        if operation_id in PUBLIC_OPERATIONS:
            assert not security, operation_id
        elif method == "get":
            assert security == [{"sessionCookie": []}], operation_id
        else:  # writes need the session AND the CSRF token in one requirement
            assert security == [{"sessionCookie": [], "csrfToken": []}], operation_id


def test_every_operation_has_a_summary_and_a_known_tag(api_app: FastAPI) -> None:
    from app.api.v1 import OPENAPI_TAGS

    known = {tag["name"] for tag in OPENAPI_TAGS}
    spec = api_app.openapi()
    for _, _, op in operations(spec):
        assert op.get("summary"), op["operationId"]
        assert op.get("tags") and set(op["tags"]) <= known, op["operationId"]


def test_response_schemas_use_readable_names(api_app: FastAPI) -> None:
    names = set(api_app.openapi()["components"]["schemas"])
    generic = {n for n in names if re.search(r"(Envelope|ListEnvelope)[_\[]", n)}
    assert not generic, f"name your response classes instead of exposing {generic}"


def test_list_operations_accept_limit_and_offset(api_app: FastAPI) -> None:
    spec = api_app.openapi()
    for _, _, op in operations(spec):
        schema = op["responses"].get("200", {}).get("content", {}).get("application/json", {})
        ref = schema.get("schema", {}).get("$ref", "")
        if ref.endswith("ListResponse"):
            names = {p["name"] for p in op.get("parameters", [])}
            assert {"limit", "offset"} <= names, op["operationId"]


# ---------------------------------------------------------------- examples inside openapi.json


def test_examples_are_embedded_in_the_generated_openapi() -> None:
    spec = json.loads(generate()["openapi.json"])
    for path in EXAMPLE_FILES:
        example = json.loads(path.read_text(encoding="utf-8"))
        status = str(example["response"]["status"])
        content_type = example["response"].get("content_type", "application/json")
        found = None
        for _, _, op in operations(spec):
            if op["operationId"] == path.parent.name:
                found = op["responses"][status]["content"][content_type]["example"]
        assert found == example["response"]["body"], f"{path} not embedded"


def test_success_request_bodies_are_embedded_too() -> None:
    spec = json.loads(generate()["openapi.json"])
    login = spec["paths"]["/api/v1/auth/login"]["post"]
    embedded = login["requestBody"]["content"]["application/json"]["example"]
    assert set(embedded) == {"email", "password"}


# ---------------------------------------------------------------- stubs


STUB_EXAMPLES = [
    p for p in EXAMPLE_FILES if p.parent.name not in IMPLEMENTED and p.name.startswith("2")
]


@pytest.mark.parametrize("path", STUB_EXAMPLES, ids=lambda p: p.parent.name)
def test_unimplemented_operations_answer_501_with_the_error_envelope(
    path: Path, client: TestClient
) -> None:
    request = json.loads(path.read_text(encoding="utf-8"))["request"]
    response = client.request(
        request["method"],
        request["path"],
        json=request.get("body"),
        headers=request.get("headers"),
    )
    assert response.status_code == 501, response.text
    assert response.json()["error"]["code"] == "NOT_IMPLEMENTED"


def test_idempotency_is_declared_exactly_where_the_contract_says(api_app: FastAPI) -> None:
    spec = api_app.openapi()
    for _, _, op in operations(spec):
        operation_id = op["operationId"]
        headers = {p["name"]: p for p in op.get("parameters", []) if p["in"] == "header"}
        if operation_id in IDEMPOTENT_OPERATIONS:
            assert headers["Idempotency-Key"]["required"] is True, operation_id
            success = "201" if "201" in op["responses"] else "200"
            replay = op["responses"][success]["headers"]
            assert "Idempotent-Replay" in replay, operation_id
            assert "400" in op["responses"], operation_id
        else:
            assert "Idempotency-Key" not in headers, operation_id
