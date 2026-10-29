"""Phase 7 hardening: assignment scope, stages, stuck, invites, emails."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import InvalidStageTransitionError
from app.models.enums import UserRole, UserStage
from app.services.stages import next_stage
from tests.auth_helpers import (
    bootstrap_strategist,
    create_tenant_as_strategist,
    login_headers,
)
from tests.conftest import FrozenClock
from tests.factories import create_customer_admin, create_strategist


def test_unassigned_strategist_cannot_self_assign(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    outsider = create_strategist(
        db_session,
        email="outsider@example.com",
        password="secure-password-1",
        now=frozen_clock(),
    )
    outsider_headers = login_headers(
        client,
        email="outsider@example.com",
        password="secure-password-1",
    )
    response = client.post(
        f"/tenants/{tenant_id}/strategists/{outsider.id}",
        headers=outsider_headers,
    )
    assert response.status_code == 404
    still_denied = client.get(f"/tenants/{tenant_id}/users", headers=outsider_headers)
    assert still_denied.status_code == 404


def test_jwt_secret_rejects_placeholder_outside_test() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="development",
            jwt_secret="change-me-in-production-use-a-long-random-secret-value-64b",
        )


def test_jwt_secret_requires_minimum_length_in_test() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="test", jwt_secret="too-short")


def test_advance_from_invited_is_rejected(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    invite = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "newbie@example.com", "sap_role": "developer"},
    ).json()
    advance = client.post(
        f"/tenants/{tenant_id}/users/{invite['user_id']}/advance",
        headers=headers,
    )
    assert advance.status_code == 409
    accept = client.post(
        "/invites/accept",
        json={"token": invite["token"], "password": "secure-password-1"},
    )
    assert accept.status_code == 200
    assert accept.json()["stage"] == "activated"


def test_next_stage_rejects_invited() -> None:
    with pytest.raises(InvalidStageTransitionError):
        next_stage(UserStage.INVITED)


def test_stuck_excludes_active_end_users_and_admins(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    start = frozen_clock()

    invite = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "stuck.dev@example.com", "sap_role": "developer"},
    ).json()
    client.post(
        "/invites/accept",
        json={"token": invite["token"], "password": "secure-password-1"},
    )
    user_id = invite["user_id"]
    for _ in range(2):
        assert (
            client.post(
                f"/tenants/{tenant_id}/users/{user_id}/advance",
                headers=headers,
            ).status_code
            == 200
        )

    create_customer_admin(
        db_session,
        tenant_id=tenant_id,
        email="admin@example.com",
        password="secure-password-1",
        now=start - timedelta(days=30),
    )

    invited = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "parked@example.com", "sap_role": "analyst"},
    )
    assert invited.status_code == 201

    frozen_clock.set(start + timedelta(days=14))
    summary = client.get(f"/tenants/{tenant_id}/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["stuck_count"] == 1
    assert body["users_per_stage"]["active"] == 1
    assert body["users_per_stage"]["invited"] == 1
    # Customer admin must not appear in end-user stage counts.
    assert sum(body["users_per_stage"].values()) == 2

    stuck = client.get(f"/tenants/{tenant_id}/stuck", headers=headers)
    assert stuck.status_code == 200
    assert stuck.json()["total"] == 1
    assert stuck.json()["items"][0]["email"] == "parked@example.com"
    assert stuck.json()["items"][0]["stage"] == "invited"


def test_duplicate_invite_email_returns_409(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    first = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "dup@example.com", "sap_role": "developer"},
    )
    assert first.status_code == 201
    second = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "dup@example.com", "sap_role": "analyst"},
    )
    assert second.status_code == 409


def test_invite_and_login_normalize_email_case(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    invite = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "Casey.Dev@Example.COM", "sap_role": "developer"},
    )
    assert invite.status_code == 201
    assert invite.json()["email"] == "casey.dev@example.com"
    accept = client.post(
        "/invites/accept",
        json={"token": invite.json()["token"], "password": "secure-password-1"},
    )
    assert accept.status_code == 200
    login = client.post(
        "/auth/token",
        json={
            "email": "CASEY.DEV@EXAMPLE.COM",
            "password": "secure-password-1",
            "tenant_id": tenant_id,
        },
    )
    assert login.status_code == 200
    assert login.json()["role"] == UserRole.END_USER.value
