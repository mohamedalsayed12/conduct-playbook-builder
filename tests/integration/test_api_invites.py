"""Integration tests for invite create/accept flows."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import FrozenClock
from tests.factories import seed_default_playbook


def _create_tenant(
    client: TestClient,
    db_session: Session,
    clock: FrozenClock,
) -> str:
    seed_default_playbook(db_session, now=clock())
    response = client.post("/tenants", json={"name": "Example Manufacturing GmbH"})
    assert response.status_code == 201
    return str(response.json()["id"])


def test_create_and_accept_invite(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    tenant_id = _create_tenant(client, db_session, frozen_clock)

    invite_response = client.post(
        f"/tenants/{tenant_id}/invites",
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

    next_steps = client.get(f"/tenants/{tenant_id}/users/{user_id}/next-steps")
    assert next_steps.status_code == 200
    assert next_steps.json()["stage"] == "activated"
    assert len(next_steps.json()["steps"]) == 1


def test_accept_expired_invite_returns_generic_error(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    tenant_id = _create_tenant(client, db_session, frozen_clock)
    invite_response = client.post(
        f"/tenants/{tenant_id}/invites",
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
    tenant_id = _create_tenant(client, db_session, frozen_clock)
    invite_response = client.post(
        f"/tenants/{tenant_id}/invites",
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
    tenant_id = _create_tenant(client, db_session, frozen_clock)
    invite_response = client.post(
        f"/tenants/{tenant_id}/invites",
        json={"email": "owner@example.com", "sap_role": "process_owner"},
    )
    from datetime import datetime

    expires_at = datetime.fromisoformat(
        invite_response.json()["expires_at"].replace("Z", "+00:00")
    )
    assert expires_at == frozen_clock() + timedelta(hours=72)
