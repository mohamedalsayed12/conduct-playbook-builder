"""Tenant playbook queries."""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.errors import NotFoundError
from app.models import Playbook, PlaybookStep
from app.models.enums import UserStage
from app.services.tenants import get_tenant


def get_tenant_playbook_grouped(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> tuple[Playbook, dict[UserStage, list[PlaybookStep]]]:
    """Return the tenant playbook with steps grouped by stage."""
    get_tenant(session, tenant_id)
    statement = (
        select(Playbook)
        .where(Playbook.tenant_id == tenant_id)
        .options(selectinload(Playbook.steps))
        .order_by(Playbook.created_at.asc())
        .limit(1)
    )
    playbook = session.scalars(statement).first()
    if playbook is None:
        raise NotFoundError(f"Playbook for tenant '{tenant_id}' was not found.")

    grouped: dict[UserStage, list[PlaybookStep]] = defaultdict(list)
    for step in sorted(
        playbook.steps, key=lambda item: (item.stage.value, item.position)
    ):
        grouped[step.stage].append(step)
    return playbook, dict(grouped)
