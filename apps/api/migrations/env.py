"""Alembic environment.

- The database URL comes from `sqlalchemy.url` if set programmatically (tests), otherwise from
  the application settings (DATABASE_URL).
- The engine is built with the application's own factory, so SQLite gets the same pragmas
  and transaction handling as the running app.
- render_as_batch=True makes ALTER operations work on SQLite.
- On SQLite, foreign keys are switched off while migrating (the approach Alembic recommends
  for batch table rebuilds), then a foreign_key_check proves nothing was left inconsistent.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401  (registers every model on Base.metadata)
from app.core.config import get_settings
from app.core.db import create_db_engine
from app.models.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def get_url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    is_sqlite = connection.dialect.name == "sqlite"
    raw = connection.connection.driver_connection  # the sqlite3 connection, no transaction open
    if is_sqlite:
        raw.execute("PRAGMA foreign_keys=OFF")
    try:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        connection.commit()
        if is_sqlite:
            violations = raw.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"Foreign key violations after migration: {violations}")
    finally:
        if is_sqlite:
            raw.execute("PRAGMA foreign_keys=ON")


def run_migrations_online() -> None:
    engine = create_db_engine(get_url(), poolclass=NullPool)
    try:
        with engine.connect() as connection:
            _run(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
