from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.enums import FacilityType, Role
from app.core.schemas import ApiModel, Envelope
from app.schemas.common import Email, Password


class LoginRequest(ApiModel):
    email: Email
    password: str = Field(min_length=1, max_length=128)


class UserSummary(ApiModel):
    id: UUID
    email: str
    full_name: str


class Membership(ApiModel):
    """A user's role at one facility, with enough facility detail to render a menu."""

    facility_id: UUID
    facility_code: str
    facility_name: str
    facility_type: FacilityType
    role: Role


class MeData(ApiModel):
    user: UserSummary
    memberships: list[Membership]
    password_change_required: bool = Field(
        description="True while a temporary password is in use. Only change-password "
        "and logout are allowed until it is changed."
    )
    session_expires_at: datetime = Field(
        description="When the session ends regardless of activity (absolute limit)."
    )


class LoginResponse(Envelope[MeData]):
    pass


class MeResponse(Envelope[MeData]):
    pass


class CsrfData(ApiModel):
    csrf_token: str


class CsrfResponse(Envelope[CsrfData]):
    pass


class LogoutData(ApiModel):
    logged_out: bool


class LogoutResponse(Envelope[LogoutData]):
    pass


class ChangePasswordRequest(ApiModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: Password


class ChangePasswordResponse(Envelope[MeData]):
    pass
