"""User aggregate."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.clock import utc_now
from app.models.base import Base
from app.models.enums import (
    SAP_ROLE_ENUM,
    USER_ROLE_ENUM,
    USER_STAGE_ENUM,
    SapRole,
    UserRole,
    UserStage,
)

if TYPE_CHECKING:
    from app.models.invite import Invite
    from app.models.stage_event import StageEvent
    from app.models.strategist_assignment import StrategistAssignment
    from app.models.tenant import Tenant


class User(Base):
    """A strategist, customer admin, or end user tracked through onboarding."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        CheckConstraint(
            "(role = 'strategist' AND tenant_id IS NULL) OR "
            "(role <> 'strategist' AND tenant_id IS NOT NULL)",
            name="ck_users_strategist_tenant",
        ),
        Index("ix_users_tenant_stage", "tenant_id", "stage"),
        Index("ix_users_tenant_stage_changed_at", "tenant_id", "stage_changed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(USER_ROLE_ENUM, nullable=False)
    sap_role: Mapped[SapRole | None] = mapped_column(SAP_ROLE_ENUM, nullable=True)
    stage: Mapped[UserStage] = mapped_column(
        USER_STAGE_ENUM,
        nullable=False,
        default=UserStage.INVITED,
    )
    stage_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    tenant: Mapped[Tenant | None] = relationship(back_populates="users")
    invites: Mapped[list[Invite]] = relationship(back_populates="user")
    stage_events: Mapped[list[StageEvent]] = relationship(back_populates="user")
    strategist_assignments: Mapped[list[StrategistAssignment]] = relationship(
        back_populates="strategist"
    )
