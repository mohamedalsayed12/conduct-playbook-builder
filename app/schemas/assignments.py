"""Strategist assignment schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StrategistAssignmentResponse(BaseModel):
    """Confirmation of a strategist assignment."""

    model_config = ConfigDict(from_attributes=True)

    strategist_id: uuid.UUID
    tenant_id: uuid.UUID
    assigned_at: datetime
