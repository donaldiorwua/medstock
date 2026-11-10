from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from app.core.enums import Role
from app.core.schemas import ApiModel, Envelope
from app.schemas.auth import Membership
from app.schemas.common import Email, ListEnvelope, Password, PersonName


class MembershipIn(ApiModel):
    facility_id: UUID
    role: Role


def _reject_duplicate_facilities(memberships: list[MembershipIn]) -> list[MembershipIn]:
    facility_ids = [m.facility_id for m in memberships]
    if len(facility_ids) != len(set(facility_ids)):
        raise ValueError("A user can have only one role per facility.")
    return memberships


class UserRecord(ApiModel):
    id: UUID
    email: str
    full_name: str
    is_active: bool
    password_change_required: bool
    locked_until: datetime | None = Field(description="Set while the account is locked out.")
    last_login_at: datetime | None
    created_at: datetime
    memberships: list[Membership]


class CreateUserRequest(ApiModel):
    email: Email
    full_name: PersonName
    temporary_password: Password = Field(
        description="The user must change it at first login (password_change_required)."
    )
    memberships: list[MembershipIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _one_role_per_facility(self) -> Self:
        _reject_duplicate_facilities(self.memberships)
        return self


class UpdateUserRequest(ApiModel):
    full_name: PersonName | None = None
    is_active: bool | None = None
    temporary_password: Password | None = Field(
        default=None, description="Resets the password and forces a change at next login."
    )
    unlock: bool | None = Field(
        default=None, description="True clears a lockout caused by failed logins."
    )

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if all(
            value is None
            for value in (self.full_name, self.is_active, self.temporary_password, self.unlock)
        ):
            raise ValueError("Provide at least one field to change.")
        return self


class ReplaceRolesRequest(ApiModel):
    memberships: list[MembershipIn] = Field(
        description="The complete set of roles. Anything not listed is removed."
    )

    @model_validator(mode="after")
    def _one_role_per_facility(self) -> Self:
        _reject_duplicate_facilities(self.memberships)
        return self


class UserResponse(Envelope[UserRecord]):
    pass


class UserListResponse(ListEnvelope[UserRecord]):
    pass
