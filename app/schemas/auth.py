"""Auth request and response schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models.enums import UserRole


class TokenRequest(BaseModel):
    """Password grant for a short-lived access token."""

    email: str = Field(
        min_length=3,
        max_length=320,
        examples=["strategist@example.com"],
    )
    password: str = Field(
        min_length=1,
        max_length=128,
        examples=["secure-password-1"],
    )
    tenant_id: uuid.UUID | None = Field(
        default=None,
        description="Required for tenant-scoped users; omit for strategists.",
    )


class TokenResponse(BaseModel):
    """Bearer access token payload."""

    access_token: str
    token_type: str = Field(default="bearer", examples=["bearer"])
    role: UserRole
    tenant_id: uuid.UUID | None = None
