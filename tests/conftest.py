"""Shared pytest fixtures. Environment is set before application imports."""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, SessionTransaction

# Bind tests to the dedicated compose test database before settings are loaded.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://conduct:conduct@localhost:5435/conduct_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.api.deps import get_clock, get_db_session
from app.cache import reset_redis_cache
from app.config import get_settings
from app.db import get_engine, reset_db_caches
from app.main import create_app

_REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class FrozenClock:
    """Injectable clock that tests can advance without sleeping."""

    # Default to wall-clock UTC so JWTs (validated against real time) stay valid.
    value: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __call__(self) -> datetime:
        return self.value

    def set(self, value: datetime) -> None:
        self.value = value


def _alembic_config() -> Config:
    config = Config(str(_REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
    config.set_main_option("path_separator", "os")
    return config


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    """Apply migrations once per test session against the test database."""
    get_settings.cache_clear()
    reset_db_caches()
    command.upgrade(_alembic_config(), "head")
    yield


@pytest.fixture(autouse=True)
def _reset_singletons() -> Iterator[None]:
    """Ensure each test sees current env-backed settings and fresh clients."""
    get_settings.cache_clear()
    reset_db_caches()
    reset_redis_cache()
    yield
    get_settings.cache_clear()
    reset_db_caches()
    reset_redis_cache()


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Yield a session wrapped in an outer transaction that always rolls back."""
    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, expire_on_commit=False)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, trans: SessionTransaction) -> None:
        parent = getattr(trans, "_parent", None)
        if trans.nested and parent is not None and not parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def frozen_clock() -> FrozenClock:
    """Return a mutable injectable clock starting at a fixed UTC instant."""
    return FrozenClock()


@pytest.fixture
def app(db_session: Session, frozen_clock: FrozenClock) -> Iterator[FastAPI]:
    """App with DB session and clock overridden for transactional tests."""
    application = create_app(get_settings())

    def _override_session() -> Iterator[Session]:
        yield db_session

    application.dependency_overrides[get_db_session] = _override_session
    application.dependency_overrides[get_clock] = lambda: frozen_clock
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """HTTP client against a fresh app instance with test overrides."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def alembic_config() -> Config:
    """Alembic config bound to the test database URL."""
    get_settings.cache_clear()
    return _alembic_config()
