"""Test harness. Runs on SQLite by default; set TEST_DATABASE_URL to run on PostgreSQL.

    TEST_DATABASE_URL=postgresql+psycopg://medstock:medstock@localhost:5432/medstock_test pytest

For PostgreSQL the public schema is wiped before every test, so the database name must
contain 'test'. The harness refuses to run against anything else.
"""

import os
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.core.config import Settings, normalise_database_url
from app.core.db import Database, create_db_engine
from app.core.enums import FacilityType, Role
from app.main import create_app
from app.models import UserFacilityRole
from tests import factories
from tests.probe import ProbeBase

API_ROOT = Path(__file__).resolve().parents[1]


def _reset_postgres(url: str) -> None:
    name = make_url(url).database or ""
    if "test" not in name:
        pytest.exit(
            f"Refusing to wipe database {name!r}: for tests its name must contain 'test'.",
            returncode=2,
        )
    engine = create_db_engine(url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    finally:
        engine.dispose()


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        return f"sqlite:///{tmp_path / 'test.db'}"
    url = normalise_database_url(url)
    if make_url(url).get_backend_name() == "postgresql":
        _reset_postgres(url)
    return url


@pytest.fixture
def dialect(db_url: str) -> str:
    return make_url(db_url).get_backend_name()


@pytest.fixture
def database(db_url: str) -> Iterator[Database]:
    db = Database(db_url)
    yield db
    db.dispose()


@pytest.fixture
def probe_tables(database: Database) -> Iterator[None]:
    ProbeBase.metadata.create_all(database.engine)
    yield
    ProbeBase.metadata.drop_all(database.engine)


@pytest.fixture
def settings(db_url: str) -> Settings:
    return Settings(_env_file=None, app_env="test", database_url=db_url)  # type: ignore[call-arg]


@pytest.fixture
def api_app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(api_app: FastAPI) -> Iterator[TestClient]:
    # raise_server_exceptions=False so a crash is answered by our 500 handler, as in production.
    with TestClient(api_app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def migrated(db_url: str, database: Database) -> Database:
    """The database with every migration applied: the real schema, constraints included."""
    from tests.test_migrations import make_config

    command.upgrade(make_config(db_url), "head")
    return database


@pytest.fixture
def world(migrated: Database) -> SimpleNamespace:
    """A committed starting point: a central store, a PHC, a user with a role at the PHC,
    an item and a batch of it."""
    with migrated.unit_of_work(write=True) as session:
        store = factories.make_facility(session, FacilityType.CENTRAL_STORE)
        phc = factories.make_facility(session)
        user = factories.make_user(session)
        session.add(UserFacilityRole(user_id=user.id, facility_id=phc.id, role=Role.PHC_OFFICER))
        item = factories.make_item(session)
        batch = factories.make_batch(session, item)
    return SimpleNamespace(store=store, phc=phc, user=user, item=item, batch=batch)


@pytest.fixture
def flow(migrated: Database, world: SimpleNamespace) -> SimpleNamespace:
    """On top of world: a request with one approved line and its shipment line."""
    with migrated.unit_of_work(write=True) as session:
        request = factories.make_request(session, world.phc, world.store, world.user)
        line = factories.make_line(session, request, world.item, qty_approved=10)
        shipment = factories.make_shipment(session, request, world.store, world.phc, world.user)
        shipment_line = factories.make_shipment_line(session, shipment, line, world.batch)
    return SimpleNamespace(
        request=request, line=line, shipment=shipment, shipment_line=shipment_line
    )
