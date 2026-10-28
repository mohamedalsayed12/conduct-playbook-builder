"""Tenant API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantCreateRequest(BaseModel):
    """Body for creating a customer tenant."""

    name: str = Field(
        min_length=1, max_length=255, examples=["Example Manufacturing GmbH"]
    )


class TenantResponse(BaseModel):
    """Tenant returned after creation or lookup."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
