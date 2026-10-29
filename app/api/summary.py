"""Rollout summary and stuck-user HTTP routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import AppClock, AppSettings, CurrentUser, DbSession
from app.schemas.summary import StuckUserListResponse, TenantSummaryResponse
from app.services import summary as summary_service

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["summary"])


@router.get("/summary", response_model=TenantSummaryResponse)
def get_tenant_summary(
    tenant_id: uuid.UUID,
    session: DbSession,
    settings: AppSettings,
    clock: AppClock,
    current_user: CurrentUser,
) -> TenantSummaryResponse:
    """Return rollout counts, stuck total, and average days per stage."""
    return summary_service.get_tenant_summary(
        session,
        tenant_id=tenant_id,
        actor=current_user,
        settings=settings,
        clock=clock,
    )


@router.get("/stuck", response_model=StuckUserListResponse)
def list_stuck_users(
    tenant_id: uuid.UUID,
    session: DbSession,
    settings: AppSettings,
    clock: AppClock,
    current_user: CurrentUser,
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
) -> StuckUserListResponse:
    """List users with no stage change for STUCK_AFTER_DAYS or longer."""
    return summary_service.list_stuck_users(
        session,
        tenant_id=tenant_id,
        actor=current_user,
        limit=limit,
        offset=offset,
        settings=settings,
        clock=clock,
    )
