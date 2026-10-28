"""Test data helpers using fictional companies only."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Playbook, PlaybookStep, User
from app.models.enums import UserRole, UserStage
from app.security.passwords import hash_password


def seed_default_playbook(
    session: Session,
    *,
    now: datetime,
    name: str = "Default Conduct Playbook",
) -> Playbook:
    """Insert the global default playbook used when creating tenants."""
    playbook = Playbook(tenant_id=None, name=name, created_at=now)
    session.add(playbook)
    session.flush()
    steps = [
        PlaybookStep(
            playbook_id=playbook.id,
            stage=UserStage.ACTIVATED,
            position=1,
            title="30-minute guided walkthrough",
            description="Complete the product walkthrough within 3 days.",
            due_within_days=3,
        ),
        PlaybookStep(
            playbook_id=playbook.id,
            stage=UserStage.FIRST_USE,
            position=1,
            title="Run first system question",
            description="Ask the first question on own custom code within 7 days.",
            due_within_days=7,
        ),
        PlaybookStep(
            playbook_id=playbook.id,
            stage=UserStage.ACTIVE,
            position=1,
            title="Weekly check-in",
            description="Confirm ongoing usage with the deployment strategist.",
            due_within_days=14,
        ),
    ]
    session.add_all(steps)
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
    tenant_id: object,
    email: str,
    password: str,
    now: datetime,
) -> User:
    """Insert a customer admin for a tenant."""
    import uuid as uuid_module

    resolved_tenant_id = (
        tenant_id
        if isinstance(tenant_id, uuid_module.UUID)
        else uuid_module.UUID(str(tenant_id))
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
