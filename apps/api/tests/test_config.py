import pytest
from pydantic import ValidationError

from app.core.config import Settings, normalise_database_url

VALID_PRODUCTION = {
    "app_env": "production",
    "database_url": "postgresql+psycopg://u:p@db.example.com/medstock",
    "session_secret": "s" * 32,
    "cookie_secure": True,
}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)


def make(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_defaults_are_the_documented_ones() -> None:
    s = make()
    assert s.app_env == "development"
    assert s.database_url == "sqlite:///./dev.db"
    assert s.cookie_secure is False
    assert (s.expiry_warning_days, s.stale_hours, s.backdate_days) == (90, 72, 30)
    assert s.adjustment_review_percent == 10
    assert (s.session_idle_minutes, s.session_absolute_hours) == (120, 12)
    assert (s.login_max_failures, s.login_lock_minutes) == (5, 15)


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STALE_HOURS", "48")
    assert make().stale_hours == 48


@pytest.mark.parametrize("env", ["production", "staging"])
def test_hardened_environments_accept_a_safe_configuration(env: str) -> None:
    assert make(**{**VALID_PRODUCTION, "app_env": env}).app_env == env


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"session_secret": ""}, "SESSION_SECRET"),
        ({"session_secret": "short"}, "SESSION_SECRET"),
        ({"cookie_secure": False}, "COOKIE_SECURE"),
        ({"database_url": "sqlite:///./prod.db"}, "PostgreSQL"),
    ],
)
@pytest.mark.parametrize("env", ["production", "staging"])
def test_hardened_environments_refuse_unsafe_configuration(
    env: str, override: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        make(**{**VALID_PRODUCTION, "app_env": env, **override})


def test_development_does_not_require_secrets() -> None:
    assert make(app_env="development").session_secret == ""


def test_idle_timeout_cannot_exceed_absolute_timeout() -> None:
    with pytest.raises(ValidationError, match="SESSION_IDLE_MINUTES"):
        make(session_idle_minutes=800, session_absolute_hours=12)


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite:///x.db", "sqlite:///x.db"),
    ],
)
def test_database_url_normalisation(given: str, expected: str) -> None:
    assert normalise_database_url(given) == expected
    assert make(database_url=given).database_url == expected
