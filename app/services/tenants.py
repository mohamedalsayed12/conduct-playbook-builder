"""Tenant creation and default playbook copying."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.clock import utc_now
from app.errors import DefaultPlaybookMissingError
from app.models import Playbook, PlaybookStep, StrategistAssignment, Tenant, User
from app.services.scoping import require_strategist

Clock = Callable[[], datetime]


def create_tenant(
    session: Session,
    *,
    name: str,
    actor: User,
    clock: Clock = utc_now,
) -> Tenant:
    """Create a tenant, copy the default playbook, assign the creating strategist."""
    require_strategist(actor)
    now = clock()
    tenant = Tenant(name=name, created_at=now)
    session.add(tenant)
    session.flush()

    default_playbook = get_default_playbook(session)
    copy_playbook_to_tenant(session, default_playbook, tenant.id, now)
    session.add(
        StrategistAssignment(
            strategist_id=actor.id,
            tenant_id=tenant.id,
            assigned_at=now,
        )
    )
    session.commit()
    session.refresh(tenant)
    return tenant


def get_default_playbook(session: Session) -> Playbook:
    statement = (
        select(Playbook)
        .where(Playbook.tenant_id.is_(None))
        .options(selectinload(Playbook.steps))
        .order_by(Playbook.created_at.asc())
        .limit(1)
    )
    playbook = session.scalars(statement).first()
    if playbook is None:
        raise DefaultPlaybookMissingError(
            "No global default playbook exists; seed one before creating tenants."
        )
    return playbook


def copy_playbook_to_tenant(
    session: Session,
    source: Playbook,
    tenant_id: uuid.UUID,
    now: datetime,
) -> Playbook:
    copy = Playbook(
        tenant_id=tenant_id,
        name=source.name,
        created_at=now,
    )
    session.add(copy)
    session.flush()
    for step in source.steps:
        session.add(
            PlaybookStep(
                playbook_id=copy.id,
                stage=step.stage,
                position=step.position,
                title=step.title,
                description=step.description,
                due_within_days=step.due_within_days,
            )
        )
    return copy
