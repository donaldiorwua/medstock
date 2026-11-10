import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.idempotency import IdempotencyKey
from app.core.error_catalogue import ErrorCode
from app.core.errors import AppError
from app.core.schemas import ApiModel


class Payload(ApiModel):
    name: str
    qty: int


def echo(payload: Payload) -> dict[str, str]:
    return {"name": payload.name}


def conflict() -> None:
    raise AppError(ErrorCode.CONFLICT, "Already exists.", details={"field": "name"})


def needs_key(key: IdempotencyKey) -> dict[str, str]:
    return {"key": key}


def crash() -> None:
    raise RuntimeError("secret internal detail")


@pytest.fixture
def api(api_app: FastAPI, client: TestClient) -> TestClient:
    api_app.add_api_route("/echo", echo, methods=["POST"])
    api_app.add_api_route("/conflict", conflict, methods=["GET"])
    api_app.add_api_route("/crash", crash, methods=["GET"])
    api_app.add_api_route("/needs-key", needs_key, methods=["POST"])
    return client


def assert_error_shape(response, status: int, code: str) -> dict:  # type: ignore[no-untyped-def,type-arg]
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    error = body["error"]
    assert set(error) == {"code", "message", "details", "request_id"}
    assert error["code"] == code
    assert error["request_id"] == response.headers["x-request-id"]
    return error


def test_unknown_url_uses_the_error_envelope(api: TestClient) -> None:
    assert_error_shape(api.get("/api/v1/nope"), 404, "NOT_FOUND")


def test_wrong_method_uses_the_error_envelope(api: TestClient) -> None:
    assert_error_shape(api.post("/api/v1/health"), 405, "METHOD_NOT_ALLOWED")


def test_app_error_is_rendered_with_its_code_status_and_details(api: TestClient) -> None:
    error = assert_error_shape(api.get("/conflict"), 409, "CONFLICT")
    assert error["details"] == {"field": "name"}


def test_validation_errors_list_field_paths_matching_the_body(api: TestClient) -> None:
    error = assert_error_shape(
        api.post("/echo", json={"name": "a", "qty": "not-a-number"}), 422, "VALIDATION_ERROR"
    )
    assert [d["path"] for d in error["details"]] == ["qty"]


def test_missing_fields_are_reported(api: TestClient) -> None:
    error = assert_error_shape(api.post("/echo", json={"qty": 1}), 422, "VALIDATION_ERROR")
    assert [d["path"] for d in error["details"]] == ["name"]


def test_unknown_fields_are_rejected_not_ignored(api: TestClient) -> None:
    error = assert_error_shape(
        api.post("/echo", json={"name": "a", "qty": 1, "surprise": True}),
        422,
        "VALIDATION_ERROR",
    )
    assert [d["path"] for d in error["details"]] == ["surprise"]


def test_validation_errors_do_not_echo_submitted_values(api: TestClient) -> None:
    response = api.post("/echo", json={"name": "a", "qty": "hunter2-secret"})
    assert "hunter2-secret" not in response.text


def test_unexpected_errors_return_500_without_leaking_details(api: TestClient) -> None:
    response = api.get("/crash")
    assert_error_shape(response, 500, "INTERNAL_ERROR")
    assert "secret internal detail" not in response.text


def test_missing_idempotency_key_has_its_own_error_code(api: TestClient) -> None:
    assert_error_shape(api.post("/needs-key"), 400, "IDEMPOTENCY_KEY_REQUIRED")


def test_a_valid_idempotency_key_is_accepted(api: TestClient) -> None:
    key = "6f1d2c3b-4a59-4e8f-9b7a-0c1d2e3f4a5b"
    response = api.post("/needs-key", headers={"Idempotency-Key": key})
    assert response.status_code == 200
    assert response.json() == {"key": key}


def test_a_malformed_idempotency_key_is_a_validation_error(api: TestClient) -> None:
    error = assert_error_shape(
        api.post("/needs-key", headers={"Idempotency-Key": "short"}), 422, "VALIDATION_ERROR"
    )
    assert error["details"][0]["path"].lower() == "header.idempotency-key"
