"""User listing and stage-advance API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import SapRole, UserRole, UserStage


class UserResponse(BaseModel):
    """Tenant-scoped user summary."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    email: str
    role: UserRole
    sap_role: SapRole | None
    stage: UserStage
    stage_changed_at: datetime
    created_at: datetime


class UserListResponse(BaseModel):
    """Paginated user list."""

    items: list[UserResponse]
    total: int
    limit: int
    offset: int


class AdvanceStageResponse(BaseModel):
    """Result of advancing a user one stage."""

    user_id: uuid.UUID
    from_stage: UserStage
    to_stage: UserStage
    stage_changed_at: datetime


class PlaybookStepResponse(BaseModel):
    """One playbook step."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stage: UserStage
    position: int
    title: str
    description: str
    due_within_days: int


class NextStepsResponse(BaseModel):
    """Playbook steps for the user's current stage."""

    user_id: uuid.UUID
    stage: UserStage
    steps: list[PlaybookStepResponse]
