"""User listing, advance, and next-steps HTTP routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import AppClock, AppSettings, CurrentUser, DbSession
from app.models.enums import SapRole, UserStage
from app.schemas.users import (
    AdvanceStageResponse,
    NextStepsResponse,
    PlaybookStepResponse,
    UserListResponse,
    UserResponse,
)
from app.services import users as user_service

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["users"])


@router.get("/users", response_model=UserListResponse)
def list_users(
    tenant_id: uuid.UUID,
    session: DbSession,
    settings: AppSettings,
    current_user: CurrentUser,
    stage: UserStage | None = None,
    sap_role: SapRole | None = None,
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
) -> UserListResponse:
    """List users for a tenant with optional filters and pagination."""
    users, total = user_service.list_users(
        session,
        tenant_id=tenant_id,
        actor=current_user,
        stage=stage,
        sap_role=sap_role,
        limit=limit,
        offset=offset,
        settings=settings,
    )
    page_limit = settings.default_page_size if limit is None else limit
    return UserListResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        limit=page_limit,
        offset=offset,
    )


@router.post(
    "/users/{user_id}/advance",
    response_model=AdvanceStageResponse,
    status_code=status.HTTP_200_OK,
)
def advance_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    session: DbSession,
    clock: AppClock,
    current_user: CurrentUser,
) -> AdvanceStageResponse:
    """Advance the user exactly one onboarding stage."""
    user, from_stage, to_stage = user_service.advance_user_stage(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        actor=current_user,
        clock=clock,
    )
    return AdvanceStageResponse(
        user_id=user.id,
        from_stage=from_stage,
        to_stage=to_stage,
        stage_changed_at=user.stage_changed_at,
    )


@router.get(
    "/users/{user_id}/next-steps",
    response_model=NextStepsResponse,
)
def get_next_steps(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> NextStepsResponse:
    """Return playbook steps for the user's current stage."""
    user, steps = user_service.get_next_steps(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        actor=current_user,
    )
    return NextStepsResponse(
        user_id=user.id,
        stage=user.stage,
        steps=[PlaybookStepResponse.model_validate(step) for step in steps],
    )
