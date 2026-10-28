"""Playbook API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserStage
from app.schemas.users import PlaybookStepResponse


class PlaybookResponse(BaseModel):
    """Tenant playbook with steps grouped by stage."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    created_at: datetime
    steps_by_stage: dict[UserStage, list[PlaybookStepResponse]] = Field(
        description="Playbook steps keyed by onboarding stage.",
    )
