"""Test data helpers using fictional companies only."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Playbook, PlaybookStep
from app.models.enums import UserStage


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
