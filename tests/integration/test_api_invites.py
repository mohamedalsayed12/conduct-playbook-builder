"""Integration tests for invite create/accept flows."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth_helpers import bootstrap_strategist, create_tenant_as_strategist
from tests.conftest import FrozenClock


def test_create_and_accept_invite(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)

    invite_response = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "developer@example.com", "sap_role": "developer"},
    )
    assert invite_response.status_code == 201
    invite_body = invite_response.json()
    assert "token" in invite_body
    assert invite_body["email"] == "developer@example.com"
    token = invite_body["token"]
    user_id = invite_body["user_id"]

    accept_response = client.post(
        "/invites/accept",
        json={"token": token, "password": "secure-password-1"},
    )
    assert accept_response.status_code == 200
    assert accept_response.json() == {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "stage": "activated",
    }

    next_steps = client.get(
        f"/tenants/{tenant_id}/users/{user_id}/next-steps",
        headers=headers,
    )
    assert next_steps.status_code == 200
    assert next_steps.json()["stage"] == "activated"
    assert len(next_steps.json()["steps"]) == 1


def test_accept_expired_invite_returns_generic_error(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    invite_response = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "analyst@example.com", "sap_role": "analyst"},
    )
    token = invite_response.json()["token"]

    frozen_clock.set(frozen_clock() + timedelta(hours=73))

    expired = client.post(
        "/invites/accept",
        json={"token": token, "password": "secure-password-1"},
    )
    assert expired.status_code == 400
    assert expired.json()["detail"] == "Invite is invalid or has expired"


def test_accept_used_invite_returns_generic_error(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    invite_response = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "architect@example.com", "sap_role": "architect"},
    )
    token = invite_response.json()["token"]

    first = client.post(
        "/invites/accept",
        json={"token": token, "password": "secure-password-1"},
    )
    assert first.status_code == 200

    second = client.post(
        "/invites/accept",
        json={"token": token, "password": "secure-password-1"},
    )
    assert second.status_code == 400
    assert second.json()["detail"] == "Invite is invalid or has expired"


def test_accept_unknown_invite_returns_generic_error(client: TestClient) -> None:
    response = client.post(
        "/invites/accept",
        json={"token": "definitely-not-a-real-token", "password": "secure-password-1"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invite is invalid or has expired"


def test_invite_expiry_uses_settings_hours(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    invite_response = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "owner@example.com", "sap_role": "process_owner"},
    )
    expires_at = datetime.fromisoformat(
        invite_response.json()["expires_at"].replace("Z", "+00:00")
    )
    assert expires_at == frozen_clock() + timedelta(hours=72)
