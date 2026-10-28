"""Tenant access scoping for authenticated callers."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ForbiddenError, NotFoundError
from app.models import StrategistAssignment, Tenant, User
from app.models.enums import UserRole

logger = logging.getLogger(__name__)


def accessible_tenant_ids(session: Session, user: User) -> frozenset[uuid.UUID]:
    """Return tenant IDs the user may manage (empty for end users)."""
    if user.role == UserRole.END_USER:
        return frozenset()
    if user.role == UserRole.CUSTOMER_ADMIN:
        if user.tenant_id is None:
            return frozenset()
        return frozenset({user.tenant_id})
    if user.role == UserRole.STRATEGIST:
        rows = session.scalars(
            select(StrategistAssignment.tenant_id).where(
                StrategistAssignment.strategist_id == user.id
            )
        ).all()
        return frozenset(rows)
    return frozenset()


def require_tenant_access(
    session: Session,
    user: User,
    tenant_id: uuid.UUID,
) -> Tenant:
    """Return the tenant when accessible; otherwise raise NotFoundError (not 403)."""
    if tenant_id not in accessible_tenant_ids(session, user):
        logger.info(
            "tenant_access_denied",
            extra={"user_id": str(user.id), "tenant_id": str(tenant_id)},
        )
        raise NotFoundError(f"Tenant '{tenant_id}' was not found.")
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        raise NotFoundError(f"Tenant '{tenant_id}' was not found.")
    return tenant


def require_strategist(user: User) -> None:
    """Raise ForbiddenError unless the caller is a strategist."""
    if user.role != UserRole.STRATEGIST:
        raise ForbiddenError("Only strategists may perform this action.")


def require_management_role(user: User) -> None:
    """Raise ForbiddenError unless the caller may manage tenants."""
    if user.role not in {UserRole.STRATEGIST, UserRole.CUSTOMER_ADMIN}:
        raise ForbiddenError("End users cannot manage tenant resources.")
