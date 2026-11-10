"""Engine creation and transaction handling for SQLite (dev/test) and PostgreSQL (staging/prod).

Transaction model
-----------------
Services open a unit of work. `write=True` means "I will change data".
- PostgreSQL: a normal READ COMMITTED transaction. Safe decrements come from conditional
  UPDATE statements (milestone A6), not from locking.
- SQLite: write units start with BEGIN IMMEDIATE, so the write lock is taken up front and
  two writers cannot deadlock halfway through. Read units use a plain BEGIN, and in WAL mode
  they do not block the writer.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any

from sqlalchemy import Connection, Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import Pool

from app.core.config import normalise_database_url

SQLITE_WRITE_OPTION = "medstock_sqlite_write"


def _install_sqlite_hooks(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def on_connect(dbapi_connection: sqlite3.Connection, _record: Any) -> None:
        # Take over transaction control from the sqlite3 module (documented SQLAlchemy recipe).
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()

    @event.listens_for(engine, "begin")
    def on_begin(conn: Connection) -> None:
        if conn.get_execution_options().get(SQLITE_WRITE_OPTION):
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            conn.exec_driver_sql("BEGIN")


def create_db_engine(
    url: str, *, echo: bool = False, poolclass: type[Pool] | None = None
) -> Engine:
    url = normalise_database_url(url)
    options: dict[str, Any] = {"echo": echo}
    if poolclass is not None:
        options["poolclass"] = poolclass
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False}, **options)
        _install_sqlite_hooks(engine)
        return engine
    return create_engine(url, pool_pre_ping=True, **options)


@contextmanager
def unit_of_work(factory: sessionmaker[Session], *, write: bool = False) -> Iterator[Session]:
    session = factory()
    try:
        if write and session.get_bind().dialect.name == "sqlite":
            # Must be the first thing that touches the connection: it makes the
            # "begin" hook above emit BEGIN IMMEDIATE.
            session.connection(execution_options={SQLITE_WRITE_OPTION: True})
        yield session
        if write:
            session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


class Database:
    """Owns the engine and session factory for one application instance."""

    def __init__(self, url: str, *, echo: bool = False) -> None:
        self.engine = create_db_engine(url, echo=echo)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def unit_of_work(self, *, write: bool = False) -> AbstractContextManager[Session]:
        return unit_of_work(self.session_factory, write=write)

    def dispose(self) -> None:
        self.engine.dispose()
