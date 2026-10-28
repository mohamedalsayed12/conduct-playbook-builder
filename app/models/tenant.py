"""Tenant aggregate."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.clock import utc_now
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.playbook import Playbook
    from app.models.stage_event import StageEvent
    from app.models.strategist_assignment import StrategistAssignment
    from app.models.user import User


class Tenant(Base):
    """A customer account onboarded by the deployment team."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    users: Mapped[list[User]] = relationship(back_populates="tenant")
    playbooks: Mapped[list[Playbook]] = relationship(back_populates="tenant")
    stage_events: Mapped[list[StageEvent]] = relationship(back_populates="tenant")
    strategist_assignments: Mapped[list[StrategistAssignment]] = relationship(
        back_populates="tenant"
    )
