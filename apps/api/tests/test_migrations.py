from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.pool import NullPool

from app.core.db import create_db_engine
from tests.conftest import API_ROOT


def make_config(url: str) -> Config:
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def current_revision(url: str) -> str | None:
    engine = create_db_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()


def test_there_is_exactly_one_migration_head() -> None:
    script = ScriptDirectory(str(API_ROOT / "migrations"))
    assert len(script.get_heads()) == 1


def test_upgrade_downgrade_upgrade_works(db_url: str) -> None:
    cfg = make_config(db_url)
    head = ScriptDirectory.from_config(cfg).get_current_head()

    command.upgrade(cfg, "head")
    assert current_revision(db_url) == head

    command.downgrade(cfg, "base")
    assert current_revision(db_url) is None

    command.upgrade(cfg, "head")
    assert current_revision(db_url) == head
