"""Playbook aggregate and ordered steps."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.clock import utc_now
from app.models.base import Base
from app.models.enums import USER_STAGE_ENUM, UserStage

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class Playbook(Base):
    """Ordered onboarding steps; null tenant_id means the global default template."""

    __tablename__ = "playbooks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    tenant: Mapped[Tenant | None] = relationship(back_populates="playbooks")
    steps: Mapped[list[PlaybookStep]] = relationship(
        back_populates="playbook",
        order_by="PlaybookStep.position",
    )


class PlaybookStep(Base):
    """One actionable step within a playbook stage."""

    __tablename__ = "playbook_steps"
    __table_args__ = (
        UniqueConstraint(
            "playbook_id",
            "stage",
            "position",
            name="uq_playbook_steps_playbook_stage_position",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    playbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("playbooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage: Mapped[UserStage] = mapped_column(USER_STAGE_ENUM, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_within_days: Mapped[int] = mapped_column(Integer, nullable=False)

    playbook: Mapped[Playbook] = relationship(back_populates="steps")
