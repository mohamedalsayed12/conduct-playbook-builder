"""Health check endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine

from app.cache import RedisClient, check_redis, get_redis
from app.db import check_database, get_engine

router = APIRouter(tags=["health"])


class HealthChecks(BaseModel):
    """Connectivity results for dependent services."""

    database: bool
    redis: bool


class HealthResponse(BaseModel):
    """Health payload returned to load balancers and operators."""

    status: str = Field(examples=["ok"])
    checks: HealthChecks | None = Field(
        default=None,
        examples=[None],
        description="Present when the service is unavailable.",
    )


class LiveChecks(BaseModel):
    """Postgres connectivity for the platform liveness probe."""

    database: bool


class LiveResponse(BaseModel):
    """Liveness payload. Redis is intentionally omitted."""

    status: str = Field(examples=["ok"])
    checks: LiveChecks | None = Field(
        default=None,
        examples=[None],
        description="Present when Postgres is unreachable.",
    )


def _database_engine() -> Engine:
    return get_engine()


def _redis_client() -> RedisClient:
    return get_redis()


@router.get(
    "/health",
    response_model=HealthResponse,
    response_model_exclude_none=True,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse},
    },
)
def health(
    response: Response,
    engine: Annotated[Engine, Depends(_database_engine)],
    redis_client: Annotated[RedisClient, Depends(_redis_client)],
) -> HealthResponse:
    """Report API liveness plus Postgres and Redis connectivity."""
    database_ok = check_database(engine)
    redis_ok = check_redis(redis_client)
    if database_ok and redis_ok:
        return HealthResponse(status="ok")

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="unavailable",
        checks=HealthChecks(database=database_ok, redis=redis_ok),
    )


@router.get(
    "/health/live",
    response_model=LiveResponse,
    response_model_exclude_none=True,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": LiveResponse},
    },
)
def health_live(
    response: Response,
    engine: Annotated[Engine, Depends(_database_engine)],
) -> LiveResponse:
    """Report whether Postgres is reachable. Redis is not required."""
    if check_database(engine):
        return LiveResponse(status="ok")

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return LiveResponse(status="unavailable", checks=LiveChecks(database=False))
