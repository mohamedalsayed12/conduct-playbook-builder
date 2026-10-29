"""Strategist-to-tenant assignment."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.clock import utc_now
from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models import StrategistAssignment, User
from app.models.enums import UserRole
from app.services.scoping import require_tenant_access

Clock = Callable[[], datetime]
logger = logging.getLogger(__name__)


def assign_strategist(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    strategist_id: uuid.UUID,
    actor: User,
    clock: Clock = utc_now,
) -> StrategistAssignment:
    """Assign a strategist to a tenant; rejects duplicates and non-strategists."""
    if actor.role != UserRole.STRATEGIST:
        # Preserve 404-for-out-of-scope before revealing a role denial.
        require_tenant_access(session, actor, tenant_id)
        raise ForbiddenError("Only strategists may perform this action.")

    # Actor must already cover the tenant (blocks self-assign onto foreign accounts).
    require_tenant_access(session, actor, tenant_id)

    strategist = session.get(User, strategist_id)
    if strategist is None or strategist.role != UserRole.STRATEGIST:
        raise NotFoundError(f"Strategist '{strategist_id}' was not found.")
    if strategist.tenant_id is not None:
        raise ValidationAppError("Strategist accounts must not belong to a tenant.")

    existing = session.get(
        StrategistAssignment,
        {"strategist_id": strategist_id, "tenant_id": tenant_id},
    )
    if existing is not None:
        raise ConflictError("Strategist is already assigned to this tenant.")

    assignment = StrategistAssignment(
        strategist_id=strategist_id,
        tenant_id=tenant_id,
        assigned_at=clock(),
    )
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    logger.info(
        "strategist_assigned",
        extra={
            "strategist_id": str(strategist_id),
            "tenant_id": str(tenant_id),
        },
    )
    return assignment
