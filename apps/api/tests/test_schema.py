"""The migrations as a whole: reversible step by step, and identical to the models."""

import re

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.pool import NullPool

from app.core.db import create_db_engine
from app.models import Base
from tests.conftest import API_ROOT
from tests.test_migrations import current_revision, make_config


def table_names(url: str) -> set[str]:
    engine = create_db_engine(url, poolclass=NullPool)
    try:
        return set(sa.inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def test_there_are_seventeen_tables_in_the_models() -> None:
    assert len(Base.metadata.tables) == 17


def test_each_revision_goes_up_and_down_one_step_at_a_time(db_url: str) -> None:
    cfg = make_config(db_url)
    script = ScriptDirectory(str(API_ROOT / "migrations"))
    revisions = [r.revision for r in reversed(list(script.walk_revisions()))]  # base to head
    assert revisions[-1] == script.get_current_head()

    for revision in revisions:
        command.upgrade(cfg, revision)
        assert current_revision(db_url) == revision
    assert table_names(db_url) == set(Base.metadata.tables)

    for revision in reversed(revisions):
        assert current_revision(db_url) == revision
        command.downgrade(cfg, "-1")
    assert current_revision(db_url) is None
    assert table_names(db_url) == set()


def test_the_migrated_schema_matches_the_models(db_url: str) -> None:
    command.upgrade(make_config(db_url), "head")
    engine = create_db_engine(db_url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            differences = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()
    # Alembic cannot compare partial indexes reliably; that one index is checked by
    # test_constraints (a second opening for the same batch is rejected).
    remaining = [d for d in differences if "uq_stock_movements_opening" not in repr(d)]
    assert remaining == [], remaining


def test_check_constraints_list_exactly_the_enum_values_in_the_models(db_url: str) -> None:
    """Alembic does not compare CHECK constraints, so compare the enum ones here."""
    command.upgrade(make_config(db_url), "head")
    engine = create_db_engine(db_url, poolclass=NullPool)
    problems: list[str] = []
    try:
        inspector = sa.inspect(engine)
        for table in Base.metadata.tables.values():
            checks = {c["name"]: c["sqltext"] for c in inspector.get_check_constraints(table.name)}
            for column in table.columns:
                if not isinstance(column.type, sa.Enum):
                    continue
                name = f"ck_{table.name}_{column.type.name}"
                if name not in checks:
                    problems.append(f"{name}: missing")
                    continue
                in_database = set(re.findall(r"'([^']+)'", str(checks[name])))
                in_models = set(column.type.enums)
                if in_database != in_models:
                    problems.append(
                        f"{name}: database {sorted(in_database)} != models {sorted(in_models)}"
                    )
    finally:
        engine.dispose()
    assert problems == [], problems
