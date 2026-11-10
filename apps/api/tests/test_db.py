import sqlite3
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from app.core.db import Database
from app.core.types import utcnow
from tests.probe import Widget


def _can_take_write_lock(path: str) -> bool:
    """True if a second, independent connection can start a write transaction right now."""
    conn = sqlite3.connect(path, timeout=0.2, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("ROLLBACK")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()


def test_sqlite_connections_have_the_agreed_pragmas(database: Database, dialect: str) -> None:
    if dialect != "sqlite":
        pytest.skip("SQLite only")
    with database.unit_of_work() as session:
        assert session.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert str(session.execute(text("PRAGMA journal_mode")).scalar_one()).lower() == "wal"
        assert session.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000


def test_sqlite_write_unit_takes_the_write_lock_immediately(
    database: Database, db_url: str, dialect: str
) -> None:
    if dialect != "sqlite":
        pytest.skip("SQLite only")
    path = str(make_url(db_url).database)
    with database.unit_of_work(write=True) as session:
        session.execute(text("SELECT 1"))  # no data changed yet, lock must already be held
        assert _can_take_write_lock(path) is False
    assert _can_take_write_lock(path) is True


def test_sqlite_read_unit_does_not_block_a_writer(
    database: Database, db_url: str, dialect: str
) -> None:
    if dialect != "sqlite":
        pytest.skip("SQLite only")
    path = str(make_url(db_url).database)
    with database.unit_of_work() as session:
        session.execute(text("SELECT 1"))
        assert _can_take_write_lock(path) is True


def test_write_unit_commits_on_success_and_rolls_back_on_error(
    database: Database, probe_tables: None
) -> None:
    with database.unit_of_work(write=True) as session:
        session.add(Widget(name="kept", seen_at=utcnow()))

    with pytest.raises(RuntimeError), database.unit_of_work(write=True) as session:
        session.add(Widget(name="lost", seen_at=utcnow()))
        session.flush()
        raise RuntimeError("boom")

    with database.unit_of_work() as session:
        names = set(session.scalars(select(Widget.name)))
    assert names == {"kept"}


def test_read_unit_does_not_persist_changes(database: Database, probe_tables: None) -> None:
    with database.unit_of_work() as session:
        session.add(Widget(id=uuid.uuid4(), name="ghost", seen_at=utcnow()))
        session.flush()
    with database.unit_of_work() as session:
        assert list(session.scalars(select(Widget.name))) == []
