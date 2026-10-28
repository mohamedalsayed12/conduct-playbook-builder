"""SQLAlchemy engine, session factory, and FastAPI dependency."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_CONNECT_TIMEOUT_SECONDS = 5


@lru_cache
def get_engine() -> Engine:
    """Create (and cache) the SQLAlchemy engine from settings."""
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": _CONNECT_TIMEOUT_SECONDS},
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return a cached sessionmaker bound to the application engine."""
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_session() -> Iterator[Session]:
    """Yield a database session and close it after the request."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def check_database(engine: Engine | None = None) -> bool:
    """Return True when a simple connectivity probe against Postgres succeeds."""
    target = engine if engine is not None else get_engine()
    try:
        with target.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OSError:
        return False
    except Exception:  # connectivity probe: catch driver/DBAPI failures without raising
        return False
    return True


def reset_db_caches() -> None:
    """Dispose and clear cached engine/session factory so tests can rebind settings."""
    if get_engine.cache_info().currsize > 0:
        get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
