"""Integration tests for user list, advance, and next-steps."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth_helpers import bootstrap_strategist, create_tenant_as_strategist
from tests.conftest import FrozenClock


def _tenant_with_activated_user(
    client: TestClient,
    db_session: Session,
    clock: FrozenClock,
) -> tuple[str, str, dict[str, str]]:
    headers, _ = bootstrap_strategist(client, db_session, clock)
    tenant_id = create_tenant_as_strategist(
        client,
        headers,
        name="Demo Logistics AG",
    )
    invite = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "developer@example.com", "sap_role": "developer"},
    ).json()
    client.post(
        "/invites/accept",
        json={"token": invite["token"], "password": "secure-password-1"},
    )
    return tenant_id, str(invite["user_id"]), headers


def test_advance_user_through_stages(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    tenant_id, user_id, headers = _tenant_with_activated_user(
        client, db_session, frozen_clock
    )

    to_first_use = client.post(
        f"/tenants/{tenant_id}/users/{user_id}/advance",
        headers=headers,
    )
    assert to_first_use.status_code == 200
    assert to_first_use.json()["from_stage"] == "activated"
    assert to_first_use.json()["to_stage"] == "first_use"

    to_active = client.post(
        f"/tenants/{tenant_id}/users/{user_id}/advance",
        headers=headers,
    )
    assert to_active.status_code == 200
    assert to_active.json()["to_stage"] == "active"

    past_active = client.post(
        f"/tenants/{tenant_id}/users/{user_id}/advance",
        headers=headers,
    )
    assert past_active.status_code == 409


def test_list_users_filters_and_pagination(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)

    for index, sap_role in enumerate(("developer", "analyst", "architect")):
        client.post(
            f"/tenants/{tenant_id}/invites",
            headers=headers,
            json={"email": f"user{index}@example.com", "sap_role": sap_role},
        )

    all_users = client.get(f"/tenants/{tenant_id}/users", headers=headers)
    assert all_users.status_code == 200
    assert all_users.json()["total"] == 3
    assert len(all_users.json()["items"]) == 3

    developers = client.get(
        f"/tenants/{tenant_id}/users",
        headers=headers,
        params={"sap_role": "developer", "stage": "invited"},
    )
    assert developers.status_code == 200
    assert developers.json()["total"] == 1
    assert developers.json()["items"][0]["email"] == "user0@example.com"

    page = client.get(
        f"/tenants/{tenant_id}/users",
        headers=headers,
        params={"limit": 2, "offset": 0},
    )
    assert page.status_code == 200
    assert len(page.json()["items"]) == 2
    assert page.json()["limit"] == 2


def test_list_users_rejects_oversized_page(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    response = client.get(
        f"/tenants/{tenant_id}/users",
        headers=headers,
        params={"limit": 101},
    )
    assert response.status_code == 422
