"""Integration tests for tenant creation and playbook endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Playbook, PlaybookStep
from app.models.enums import UserStage
from tests.auth_helpers import bootstrap_strategist, create_tenant_as_strategist
from tests.conftest import FrozenClock


def test_create_tenant_copies_default_playbook(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)

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

    playbook_response = client.get(
        f"/tenants/{tenant_id}/playbook",
        headers=headers,
    )
    assert playbook_response.status_code == 200
    grouped = playbook_response.json()["steps_by_stage"]
    assert "activated" in grouped
    assert grouped["activated"][0]["title"] == "30-minute guided walkthrough"


def test_create_tenant_without_default_playbook_returns_503(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    from tests.auth_helpers import login_headers
    from tests.factories import create_strategist

    create_strategist(
        db_session,
        email="lonely@example.com",
        password="secure-password-1",
        now=frozen_clock(),
    )
    headers = login_headers(
        client,
        email="lonely@example.com",
        password="secure-password-1",
    )
    response = client.post(
        "/tenants",
        json={"name": "Demo Logistics AG"},
        headers=headers,
    )
    assert response.status_code == 503
