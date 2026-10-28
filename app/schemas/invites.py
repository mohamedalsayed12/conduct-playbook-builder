"""Invite API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SapRole


class InviteCreateRequest(BaseModel):
    """Body for inviting an end user into a tenant."""

    email: str = Field(min_length=3, max_length=320, examples=["developer@example.com"])
    sap_role: SapRole = Field(examples=[SapRole.DEVELOPER])


class InviteCreateResponse(BaseModel):
    """Invite metadata plus the raw token (shown once)."""

    model_config = ConfigDict(from_attributes=True)

    invite_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    sap_role: SapRole
    expires_at: datetime
    token: str = Field(
        description="Raw invite token; returned only on creation.",
        examples=["xY7_raw-token-example"],
    )


class InviteAcceptRequest(BaseModel):
    """Body for accepting an invite and setting a password."""

    token: str = Field(min_length=1, examples=["xY7_raw-token-example"])
    password: str = Field(
        min_length=8, max_length=128, examples=["correct-horse-battery"]
    )


class InviteAcceptResponse(BaseModel):
    """Confirmation after a successful invite acceptance."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    stage: str = Field(examples=["activated"])
