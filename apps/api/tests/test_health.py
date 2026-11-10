import re

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_returns_ok_in_the_standard_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok", "database": "ok", "environment": "test"}}
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])


def test_a_sensible_caller_request_id_is_echoed(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-Id": "trace-abc-12345"})
    assert response.headers["x-request-id"] == "trace-abc-12345"


def test_an_unsafe_caller_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-Id": "bad id\twith junk"})
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])


def test_health_reports_an_unreachable_database_as_503(tmp_path) -> None:  # type: ignore[no-untyped-def]
    broken_url = f"sqlite:///{tmp_path / 'no_such_dir' / 'db.sqlite'}"
    settings = Settings(_env_file=None, app_env="test", database_url=broken_url)  # type: ignore[call-arg]
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "DATABASE_UNAVAILABLE"
    assert error["request_id"] == response.headers["x-request-id"]
