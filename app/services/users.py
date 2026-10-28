"""User listing, stage advance, and next-step lookup."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.clock import utc_now
from app.config import Settings, get_settings
from app.errors import NotFoundError, ValidationAppError
from app.models import Playbook, PlaybookStep, StageEvent, User
from app.models.enums import SapRole, UserStage
from app.services.stages import next_stage
from app.services.tenants import get_tenant

Clock = Callable[[], datetime]


def advance_user_stage(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    clock: Clock = utc_now,
) -> tuple[User, UserStage, UserStage]:
    """Move the user forward exactly one stage and append a StageEvent."""
    get_tenant(session, tenant_id)
    user = _get_tenant_user(session, tenant_id=tenant_id, user_id=user_id)
    from_stage = user.stage
    to_stage = next_stage(from_stage)
    now = clock()
    user.stage = to_stage
    user.stage_changed_at = now
    session.add(
        StageEvent(
            tenant_id=tenant_id,
            user_id=user.id,
            from_stage=from_stage,
            to_stage=to_stage,
            occurred_at=now,
        )
    )
    session.commit()
    session.refresh(user)
    return user, from_stage, to_stage


def list_users(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stage: UserStage | None = None,
    sap_role: SapRole | None = None,
    limit: int | None = None,
    offset: int = 0,
    settings: Settings | None = None,
) -> tuple[list[User], int]:
    """Return a stable, filtered page of users for a tenant."""
    resolved = settings if settings is not None else get_settings()
    get_tenant(session, tenant_id)
    page_size = resolved.default_page_size if limit is None else limit
    if page_size < 1 or page_size > resolved.max_page_size:
        raise ValidationAppError(
            f"limit must be between 1 and {resolved.max_page_size}."
        )
    if offset < 0:
        raise ValidationAppError("offset must be >= 0.")

    filters = [User.tenant_id == tenant_id]
    if stage is not None:
        filters.append(User.stage == stage)
    if sap_role is not None:
        filters.append(User.sap_role == sap_role)

    total = session.scalar(select(func.count()).select_from(User).where(*filters))
    if total is None:
        total = 0

    statement = (
        select(User)
        .where(*filters)
        .order_by(User.created_at.asc(), User.id.asc())
        .limit(page_size)
        .offset(offset)
    )
    users = list(session.scalars(statement).all())
    return users, total


def get_next_steps(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[User, list[PlaybookStep]]:
    """Return playbook steps for the user's current stage."""
    get_tenant(session, tenant_id)
    user = _get_tenant_user(session, tenant_id=tenant_id, user_id=user_id)
    playbook = _get_tenant_playbook(session, tenant_id)
    steps = [step for step in playbook.steps if step.stage == user.stage]
    steps.sort(key=lambda item: item.position)
    return user, steps


def _get_tenant_user(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> User:
    user = session.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        raise NotFoundError(f"User '{user_id}' was not found.")
    return user


def _get_tenant_playbook(session: Session, tenant_id: uuid.UUID) -> Playbook:
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
    return playbook
