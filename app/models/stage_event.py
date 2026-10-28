"""StageEvent aggregate — append-only onboarding history."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.clock import utc_now
from app.models.base import Base
from app.models.enums import USER_STAGE_ENUM, UserStage

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class StageEvent(Base):
    """Immutable record of a user moving from one stage to another."""

    __tablename__ = "stage_events"
    __table_args__ = (Index("ix_stage_events_tenant_user", "tenant_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_stage: Mapped[UserStage | None] = mapped_column(USER_STAGE_ENUM, nullable=True)
    to_stage: Mapped[UserStage] = mapped_column(USER_STAGE_ENUM, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="stage_events")
    user: Mapped[User] = relationship(back_populates="stage_events")
