"""Integration tests for tenant creation and playbook endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Playbook, PlaybookStep
from app.models.enums import UserStage
from tests.conftest import FrozenClock
from tests.factories import seed_default_playbook


def test_create_tenant_copies_default_playbook(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    seed_default_playbook(db_session, now=frozen_clock())

    response = client.post(
        "/tenants",
        json={"name": "Example Manufacturing GmbH"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Example Manufacturing GmbH"
    tenant_id = body["id"]

    playbook = db_session.scalars(
        select(Playbook).where(Playbook.tenant_id == tenant_id)
    ).one()
    steps = list(
        db_session.scalars(
            select(PlaybookStep).where(PlaybookStep.playbook_id == playbook.id)
        ).all()
    )
    assert len(steps) == 3
    assert {step.stage for step in steps} == {
        UserStage.ACTIVATED,
        UserStage.FIRST_USE,
        UserStage.ACTIVE,
    }

    playbook_response = client.get(f"/tenants/{tenant_id}/playbook")
    assert playbook_response.status_code == 200
    grouped = playbook_response.json()["steps_by_stage"]
    assert "activated" in grouped
    assert grouped["activated"][0]["title"] == "30-minute guided walkthrough"


def test_create_tenant_without_default_playbook_returns_503(
    client: TestClient,
) -> None:
    response = client.post("/tenants", json={"name": "Demo Logistics AG"})
    assert response.status_code == 503
