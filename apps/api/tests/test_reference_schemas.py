"""Rules written into the slice 1 request schemas (auth, users, facilities, items)."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.schemas.facilities import (
    CreateFacilityRequest,
    ReplaceThresholdsRequest,
    ThresholdIn,
    UpdateFacilityRequest,
)
from app.schemas.items import CreateBatchRequest, CreateItemRequest, UpdateItemRequest
from app.schemas.users import (
    CreateUserRequest,
    MembershipIn,
    ReplaceRolesRequest,
    UpdateUserRequest,
)

FACILITY = uuid4()
ITEM = uuid4()


def test_email_is_trimmed_and_lower_cased() -> None:
    assert LoginRequest(email="  Chidi.Officer@Example.ORG ", password="x").email == (
        "chidi.officer@example.org"
    )


@pytest.mark.parametrize("bad", ["", "no-at-sign", "a@b", "two words@example.org"])
def test_malformed_emails_are_rejected(bad: str) -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email=bad, password="x")


def test_codes_are_lower_cased_and_restricted() -> None:
    item = CreateItemRequest(code=" AMOX-250.Cap ", name="Amoxicillin", base_unit="capsule")
    assert item.code == "amox-250.cap"
    with pytest.raises(ValidationError):
        CreateItemRequest(code="has space", name="x", base_unit="capsule")
    with pytest.raises(ValidationError):
        CreateItemRequest(code="-leading-dash", name="x", base_unit="capsule")


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="surprise"):
        LoginRequest(email="a@b.co", password="x", surprise=True)  # type: ignore[call-arg]


def test_new_passwords_need_at_least_ten_characters() -> None:
    ChangePasswordRequest(current_password="old", new_password="0123456789")
    with pytest.raises(ValidationError):
        ChangePasswordRequest(current_password="old", new_password="short")
    with pytest.raises(ValidationError):
        CreateUserRequest(
            email="a@b.co",
            full_name="A",
            temporary_password="short",
            memberships=[MembershipIn(facility_id=FACILITY, role="phc_officer")],
        )


def test_roles_must_be_known_and_unique_per_facility() -> None:
    with pytest.raises(ValidationError):
        MembershipIn(facility_id=FACILITY, role="superuser")
    duplicated = [
        MembershipIn(facility_id=FACILITY, role="phc_officer"),
        MembershipIn(facility_id=FACILITY, role="viewer"),
    ]
    with pytest.raises(ValidationError, match="one role per facility"):
        ReplaceRolesRequest(memberships=duplicated)
    assert ReplaceRolesRequest(memberships=[]).memberships == []  # removing every role is allowed


def test_a_new_user_needs_at_least_one_membership() -> None:
    with pytest.raises(ValidationError):
        CreateUserRequest(
            email="a@b.co", full_name="A", temporary_password="0123456789", memberships=[]
        )


@pytest.mark.parametrize(
    "request_class",
    [UpdateUserRequest, UpdateFacilityRequest, UpdateItemRequest],
)
def test_patch_requests_must_change_something(request_class: type) -> None:
    with pytest.raises(ValidationError, match="at least one field"):
        request_class()


def test_facility_timezone_must_look_like_an_iana_name() -> None:
    CreateFacilityRequest(
        code="cms-01", name="Store", facility_type="central_store", timezone="Africa/Lagos"
    )
    with pytest.raises(ValidationError):
        CreateFacilityRequest(
            code="cms-01", name="Store", facility_type="central_store", timezone="Lagos time"
        )


def test_thresholds_reorder_level_cannot_be_below_critical_level() -> None:
    ThresholdIn(item_id=ITEM, reorder_level=200, critical_level=200)
    with pytest.raises(ValidationError, match="reorder_level"):
        ThresholdIn(item_id=ITEM, reorder_level=100, critical_level=200)
    with pytest.raises(ValidationError):
        ThresholdIn(item_id=ITEM, reorder_level=-1, critical_level=-2)


def test_thresholds_list_rejects_duplicate_items() -> None:
    one = ThresholdIn(item_id=ITEM, reorder_level=10, critical_level=5)
    with pytest.raises(ValidationError, match="only once"):
        ReplaceThresholdsRequest(thresholds=[one, one])


def test_batch_numbers_are_trimmed_and_required() -> None:
    batch = CreateBatchRequest(item_id=ITEM, batch_number=" B-1 ", expiry_date="2027-01-31")
    assert batch.batch_number == "B-1"
    with pytest.raises(ValidationError):
        CreateBatchRequest(item_id=ITEM, batch_number="  ", expiry_date="2027-01-31")
    with pytest.raises(ValidationError):
        CreateBatchRequest(item_id=ITEM, batch_number="B-1", expiry_date="31/01/2027")


@pytest.mark.parametrize("query", ["limit=0", "limit=201", "offset=-1", "limit=abc"])
def test_paging_parameters_are_validated(client: TestClient, query: str) -> None:
    response = client.get(f"/api/v1/users?{query}")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["path"].startswith("query.")


def test_valid_paging_parameters_reach_the_handler(client: TestClient) -> None:
    response = client.get("/api/v1/users?limit=200&offset=10")
    assert response.status_code == 501  # stub: parameters were accepted
