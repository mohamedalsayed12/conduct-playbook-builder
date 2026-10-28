"""Rollout summary and stuck-user API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SapRole, UserStage
from app.schemas.users import PlaybookStepResponse


class TenantSummaryResponse(BaseModel):
    """Aggregated rollout metrics for one tenant."""

    tenant_id: uuid.UUID
    users_per_stage: dict[UserStage, int]
    users_per_sap_role_per_stage: dict[UserStage, dict[SapRole, int]]
    stuck_count: int = Field(ge=0)
    average_days_per_stage: dict[UserStage, float]
    computed_at: datetime


class StuckUserResponse(BaseModel):
    """One user past the stuck threshold, with their next playbook step."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: str
    stage: UserStage
    stage_changed_at: datetime
    days_stuck: float
    next_step: PlaybookStepResponse | None


class StuckUserListResponse(BaseModel):
    """Paginated stuck-user list."""

    items: list[StuckUserResponse]
    total: int
    limit: int
    offset: int
