from fastapi import APIRouter

from app.api.security import READ_AUTH, WRITE_AUTH
from app.api.support import error_responses, not_implemented
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    CsrfResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MeResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    responses=error_responses(401, 423, 429),
    summary="Log in",
    description=(
        "Starts a session and sets the session cookie. No CSRF token is needed here. "
        "After five failed attempts the account is locked (ACCOUNT_LOCKED) for 15 minutes."
    ),
)
def login(body: LoginRequest) -> LoginResponse:
    not_implemented()


@router.post(
    "/logout",
    response_model=LogoutResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403),
    summary="Log out",
    description="Ends the session and clears the cookie.",
)
def logout() -> LogoutResponse:
    not_implemented()


@router.get(
    "/me",
    response_model=MeResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401),
    summary="Current user",
    description="The signed-in user with their facilities and roles.",
)
def me() -> MeResponse:
    not_implemented()


@router.get(
    "/csrf",
    response_model=CsrfResponse,
    dependencies=READ_AUTH,
    responses=error_responses(401),
    summary="Get a CSRF token",
    description="Send the token in the X-CSRF-Token header on every POST, PUT and PATCH.",
)
def csrf() -> CsrfResponse:
    not_implemented()


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    dependencies=WRITE_AUTH,
    responses=error_responses(401, 403, 429),
    summary="Change own password",
    description=(
        "Allowed even while a temporary password is in use. A wrong current_password is "
        "reported as VALIDATION_ERROR on that field (not 401, which means 'not signed in')."
    ),
)
def change_password(body: ChangePasswordRequest) -> ChangePasswordResponse:
    not_implemented()
