"""Test fixtures: a real app, wired to a throwaway in-memory database."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session", autouse=True)
def _isolate_settings() -> Iterator[None]:
    """Keep the suite away from the developer's .env and their local database."""
    from app.config import get_settings

    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    os.environ["AUTO_CREATE_SCHEMA"] = "false"
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def engine() -> Iterator[Engine]:
    from app.db.models import Base

    # StaticPool keeps every connection on the same in-memory database.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    from app.db.session import get_session
    from app.main import create_app

    def session_override() -> Iterator[Session]:
        with session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as test_client:
        yield test_client
