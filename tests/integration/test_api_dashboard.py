"""Dashboard page and accessible-tenant list tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth_helpers import (
    bootstrap_strategist,
    create_tenant_as_strategist,
    login_headers,
)
from tests.conftest import FrozenClock
from tests.factories import create_customer_admin, create_strategist


def test_dashboard_returns_html(client: TestClient) -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Rollout" in response.text
    assert 'id="dashboard-error"' in response.text
    assert 'id="login-error"' in response.text
    assert 'id="tenant-select"' in response.text
    dashboard_at = response.text.index('id="dashboard"')
    error_at = response.text.index('id="dashboard-error"')
    login_error_at = response.text.index('id="login-error"')
    assert login_error_at < dashboard_at < error_at


def test_list_tenants_returns_assigned_for_strategist(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_a = create_tenant_as_strategist(
        client, headers, name="Example Manufacturing GmbH"
    )
    tenant_b = create_tenant_as_strategist(client, headers, name="Demo Logistics AG")

    response = client.get("/tenants", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    ids = {item["id"] for item in items}
    assert ids == {tenant_a, tenant_b}
    names = [item["name"] for item in items]
    assert names == sorted(names)


def test_list_tenants_isolates_customer_admin(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_a = create_tenant_as_strategist(
        client, headers, name="Example Manufacturing GmbH"
    )
    tenant_b = create_tenant_as_strategist(client, headers, name="Demo Logistics AG")
    create_customer_admin(
        db_session,
        tenant_id=tenant_a,
        email="admin-a@example.com",
        password="secure-password-1",
        now=frozen_clock(),
    )
    admin_headers = login_headers(
        client,
        email="admin-a@example.com",
        password="secure-password-1",
        tenant_id=tenant_a,
    )

    response = client.get("/tenants", headers=admin_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == tenant_a
    assert tenant_b not in {item["id"] for item in items}


def test_unassigned_strategist_lists_no_tenants(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    create_tenant_as_strategist(client, headers)
    create_strategist(
        db_session,
        email="outsider@example.com",
        password="secure-password-1",
        now=frozen_clock(),
    )
    outsider = login_headers(
        client,
        email="outsider@example.com",
        password="secure-password-1",
    )
    response = client.get("/tenants", headers=outsider)
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_end_user_cannot_list_tenants(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    invite = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "enduser@example.com", "sap_role": "developer"},
    ).json()
    client.post(
        "/invites/accept",
        json={"token": invite["token"], "password": "secure-password-1"},
    )
    end_user = login_headers(
        client,
        email="enduser@example.com",
        password="secure-password-1",
        tenant_id=tenant_id,
    )
    response = client.get("/tenants", headers=end_user)
    assert response.status_code == 403
