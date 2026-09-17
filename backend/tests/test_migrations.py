"""The migrations and the ORM models must describe the same schema.

Two places define the table -- ``app/db/models.py`` for the application and
``migrations/versions/`` for the database -- and nothing but a test stops them
drifting. This runs the migrations against an empty database and compares the
result to the metadata the application expects.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.db.models import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def migrated_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from app.config import get_settings

    url = f"sqlite+pysqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    command.upgrade(config, "head")

    engine = create_engine(url)
    yield engine, config
    engine.dispose()
    get_settings.cache_clear()


def test_migrations_build_the_table_the_models_expect(migrated_database) -> None:
    engine, _ = migrated_database
    inspector = inspect(engine)
    expected = Base.metadata.tables["accommodation_bookings"]

    assert "accommodation_bookings" in inspector.get_table_names()

    migrated_columns = {
        column["name"]: column
        for column in inspector.get_columns("accommodation_bookings")
    }
    assert set(migrated_columns) == {column.name for column in expected.columns}

    for column in expected.columns:
        assert migrated_columns[column.name]["nullable"] == column.nullable, column.name


def test_migrations_build_the_indexes_the_queries_need(migrated_database) -> None:
    engine, _ = migrated_database
    migrated = {
        index["name"] for index in inspect(engine).get_indexes("accommodation_bookings")
    }

    assert {
        "ix_accommodation_bookings_created_at",
        "ix_accommodation_bookings_meal_plan",
    } <= migrated
    # Bill numbers must be unique: the retry on collision depends on it.
    unique = inspect(engine).get_unique_constraints("accommodation_bookings")
    assert {"bill_number"} in [set(c["column_names"]) for c in unique]


def test_downgrade_removes_everything_it_created(migrated_database) -> None:
    engine, config = migrated_database

    command.downgrade(config, "base")

    assert "accommodation_bookings" not in inspect(engine).get_table_names()
