"""Test data helpers using fictional companies only."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Playbook, PlaybookStep, User
from app.models.enums import UserRole, UserStage
from app.security.passwords import hash_password
from app.seed_data import DEFAULT_PLAYBOOK_NAME, DEFAULT_PLAYBOOK_STEPS


def seed_default_playbook(
    session: Session,
    *,
    now: datetime,
    name: str = DEFAULT_PLAYBOOK_NAME,
) -> Playbook:
    """Insert the global default playbook used when creating tenants."""
    playbook = Playbook(tenant_id=None, name=name, created_at=now)
    session.add(playbook)
    session.flush()
    session.add_all(
        [
            PlaybookStep(
                playbook_id=playbook.id,
                stage=step.stage,
                position=step.position,
                title=step.title,
                description=step.description,
                due_within_days=step.due_within_days,
            )
            for step in DEFAULT_PLAYBOOK_STEPS
        ]
    )
    session.flush()
    return playbook


def create_strategist(
    session: Session,
    *,
    email: str,
    password: str,
    now: datetime,
) -> User:
    """Insert a strategist with a password hash for authenticated tests."""
    user = User(
        tenant_id=None,
        email=email,
        password_hash=hash_password(password),
        role=UserRole.STRATEGIST,
        sap_role=None,
        stage=UserStage.ACTIVE,
        stage_changed_at=now,
        created_at=now,
    )
    session.add(user)
    session.flush()
    return user


def create_customer_admin(
    session: Session,
    *,
    tenant_id: uuid.UUID | str,
    email: str,
    password: str,
    now: datetime,
) -> User:
    """Insert a customer admin for a tenant."""
    resolved_tenant_id = (
        tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    )
    user = User(
        tenant_id=resolved_tenant_id,
        email=email,
        password_hash=hash_password(password),
        role=UserRole.CUSTOMER_ADMIN,
        sap_role=None,
        stage=UserStage.ACTIVE,
        stage_changed_at=now,
        created_at=now,
    )
    session.add(user)
    session.flush()
    return user
