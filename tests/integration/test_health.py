"""Integration tests for GET /health against real Postgres and Redis."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.api.health import _database_engine, _redis_client
from app.cache import RedisClient, reset_redis_cache
from app.config import get_settings
from app.db import reset_db_caches
from app.main import create_app

_PROBE_CONNECT_TIMEOUT_SECONDS = 1


@pytest.fixture
def health_app() -> Iterator[FastAPI]:
    get_settings.cache_clear()
    reset_db_caches()
    reset_redis_cache()
    application = create_app(get_settings())
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def app_client(health_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(health_app) as test_client:
        yield test_client


def test_health_returns_ok_when_dependencies_are_up(app_client: TestClient) -> None:
    response = app_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_database_is_unreachable(
    health_app: FastAPI,
    app_client: TestClient,
) -> None:
    broken_engine = create_engine(
        "postgresql+psycopg://conduct:conduct@127.0.0.1:1/conduct_test",
        pool_pre_ping=True,
        connect_args={"connect_timeout": _PROBE_CONNECT_TIMEOUT_SECONDS},
    )
    health_app.dependency_overrides[_database_engine] = lambda: broken_engine
    try:
        response = app_client.get("/health")
    finally:
        broken_engine.dispose()

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"]["database"] is False
    assert body["checks"]["redis"] is True


def test_health_returns_503_when_redis_is_unreachable(
    health_app: FastAPI,
    app_client: TestClient,
) -> None:
    broken_redis = RedisClient(
        host="127.0.0.1",
        port=1,
        socket_connect_timeout=0.2,
        socket_timeout=0.2,
        decode_responses=True,
    )
    health_app.dependency_overrides[_redis_client] = lambda: broken_redis
    try:
        response = app_client.get("/health")
    finally:
        broken_redis.close()

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"]["database"] is True
    assert body["checks"]["redis"] is False


def test_health_live_returns_ok_when_redis_is_unreachable(
    health_app: FastAPI,
    app_client: TestClient,
) -> None:
    broken_redis = RedisClient(
        host="127.0.0.1",
        port=1,
        socket_connect_timeout=0.2,
        socket_timeout=0.2,
        decode_responses=True,
    )
    health_app.dependency_overrides[_redis_client] = lambda: broken_redis
    try:
        response = app_client.get("/health/live")
    finally:
        broken_redis.close()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_live_returns_503_when_database_is_unreachable(
    health_app: FastAPI,
    app_client: TestClient,
) -> None:
    broken_engine = create_engine(
        "postgresql+psycopg://conduct:conduct@127.0.0.1:1/conduct_test",
        pool_pre_ping=True,
        connect_args={"connect_timeout": _PROBE_CONNECT_TIMEOUT_SECONDS},
    )
    health_app.dependency_overrides[_database_engine] = lambda: broken_engine
    try:
        response = app_client.get("/health/live")
    finally:
        broken_engine.dispose()

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"] == {"database": False}
