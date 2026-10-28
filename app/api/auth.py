"""Authentication HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import AppClock, AppSettings, DbSession
from app.schemas.auth import TokenRequest, TokenResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def create_token(
    body: TokenRequest,
    session: DbSession,
    settings: AppSettings,
    clock: AppClock,
) -> TokenResponse:
    """Exchange email/password for a short-lived JWT."""
    access_token, user = auth_service.issue_access_token(
        session,
        email=body.email,
        password=body.password,
        tenant_id=body.tenant_id,
        settings=settings,
        clock=clock,
    )
    return TokenResponse(
        access_token=access_token,
        role=user.role,
        tenant_id=user.tenant_id,
    )
