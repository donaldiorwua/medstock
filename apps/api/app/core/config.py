"""Application settings (blueprint section 13). One place, validated at startup."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["development", "test", "e2e", "staging", "production"]

# Environments where unsafe configuration must stop the app from starting.
HARDENED_ENVS: frozenset[str] = frozenset({"staging", "production"})


def normalise_database_url(url: str) -> str:
    """Accept the URL forms hosting providers hand out (postgres://, postgresql://)
    and point them at the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_env: AppEnv = "development"
    database_url: str = "sqlite:///./dev.db"
    session_secret: str = ""
    cookie_secure: bool = False

    expiry_warning_days: int = Field(default=90, ge=1)
    stale_hours: int = Field(default=72, ge=1)
    backdate_days: int = Field(default=30, ge=0)
    adjustment_review_percent: int = Field(default=10, ge=1, le=100)
    session_idle_minutes: int = Field(default=120, ge=1)
    session_absolute_hours: int = Field(default=12, ge=1)
    login_max_failures: int = Field(default=5, ge=1)
    login_lock_minutes: int = Field(default=15, ge=1)

    @field_validator("database_url")
    @classmethod
    def _normalise_url(cls, value: str) -> str:
        return normalise_database_url(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        problems: list[str] = []
        if self.session_idle_minutes > self.session_absolute_hours * 60:
            problems.append("SESSION_IDLE_MINUTES must not exceed SESSION_ABSOLUTE_HOURS")
        if self.app_env in HARDENED_ENVS:
            if len(self.session_secret) < 32:
                problems.append("SESSION_SECRET must be set (at least 32 characters)")
            if not self.cookie_secure:
                problems.append("COOKIE_SECURE must be true")
            if self.database_url.startswith("sqlite"):
                problems.append("DATABASE_URL must point to PostgreSQL")
        if problems:
            raise ValueError("; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
