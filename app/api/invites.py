"""Invite HTTP routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import AppClock, AppSettings, CurrentUser, DbSession
from app.schemas.invites import (
    InviteAcceptRequest,
    InviteAcceptResponse,
    InviteCreateRequest,
    InviteCreateResponse,
)
from app.services import invites as invite_service

router = APIRouter(tags=["invites"])


@router.post(
    "/tenants/{tenant_id}/invites",
    response_model=InviteCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invite(
    tenant_id: uuid.UUID,
    body: InviteCreateRequest,
    session: DbSession,
    settings: AppSettings,
    clock: AppClock,
    current_user: CurrentUser,
) -> InviteCreateResponse:
    """Invite an end user; returns the raw token once."""
    invite, user, raw_token = invite_service.create_invite(
        session,
        tenant_id=tenant_id,
        email=body.email,
        sap_role=body.sap_role,
        actor=current_user,
        settings=settings,
        clock=clock,
    )
    return InviteCreateResponse(
        invite_id=invite.id,
        user_id=user.id,
        email=user.email,
        sap_role=user.sap_role if user.sap_role is not None else body.sap_role,
        expires_at=invite.expires_at,
        token=raw_token,
    )


@router.post(
    "/invites/accept",
    response_model=InviteAcceptResponse,
    status_code=status.HTTP_200_OK,
)
def accept_invite(
    body: InviteAcceptRequest,
    session: DbSession,
    clock: AppClock,
) -> InviteAcceptResponse:
    """Accept an invite with a password and move the user to activated."""
    user = invite_service.accept_invite(
        session,
        raw_token=body.token,
        password=body.password,
        clock=clock,
    )
    if user.tenant_id is None:
        raise RuntimeError("Activated end user is missing tenant_id.")
    return InviteAcceptResponse(
        user_id=user.id,
        tenant_id=user.tenant_id,
        stage=user.stage.value,
    )
