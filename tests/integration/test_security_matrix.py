"""Tenant isolation and JWT security integration tests."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from tests.auth_helpers import (
    bootstrap_strategist,
    create_tenant_as_strategist,
    login_headers,
)
from tests.conftest import FrozenClock
from tests.factories import create_customer_admin, create_strategist


def _tenant_b_endpoints(
    tenant_b: str, user_id: str, strategist_id: str
) -> list[tuple[str, str]]:
    return [
        ("GET", f"/tenants/{tenant_b}/users"),
        ("GET", f"/tenants/{tenant_b}/playbook"),
        ("POST", f"/tenants/{tenant_b}/invites"),
        ("POST", f"/tenants/{tenant_b}/users/{user_id}/advance"),
        ("GET", f"/tenants/{tenant_b}/users/{user_id}/next-steps"),
        ("POST", f"/tenants/{tenant_b}/strategists/{strategist_id}"),
    ]


def test_customer_admin_of_a_gets_404_on_every_tenant_b_endpoint(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers_a, strategist_id = bootstrap_strategist(
        client,
        db_session,
        frozen_clock,
        email="lead@example.com",
    )
    tenant_a = create_tenant_as_strategist(
        client, headers_a, name="Example Manufacturing GmbH"
    )
    tenant_b = create_tenant_as_strategist(client, headers_a, name="Demo Logistics AG")
    invite = client.post(
        f"/tenants/{tenant_b}/invites",
        headers=headers_a,
        json={"email": "dev@example.com", "sap_role": "developer"},
    ).json()

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

    for method, path in _tenant_b_endpoints(tenant_b, invite["user_id"], strategist_id):
        if method == "GET":
            response = client.get(path, headers=admin_headers)
        else:
            body = (
                {"email": "x@example.com", "sap_role": "developer"}
                if path.endswith("/invites")
                else None
            )
            response = client.post(path, headers=admin_headers, json=body)
        assert response.status_code == 404, f"{method} {path} -> {response.status_code}"


def test_unassigned_strategist_cannot_see_tenant(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)

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
    response = client.get(f"/tenants/{tenant_id}/users", headers=outsider)
    assert response.status_code == 404


def test_assigned_strategist_can_see_tenant(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(
        client,
        db_session,
        frozen_clock,
        email="owner@example.com",
    )
    tenant_id = create_tenant_as_strategist(client, headers)

    other = create_strategist(
        db_session,
        email="partner@example.com",
        password="secure-password-1",
        now=frozen_clock(),
    )
    assign = client.post(
        f"/tenants/{tenant_id}/strategists/{other.id}",
        headers=headers,
    )
    assert assign.status_code == 201

    partner = login_headers(
        client,
        email="partner@example.com",
        password="secure-password-1",
    )
    response = client.get(f"/tenants/{tenant_id}/users", headers=partner)
    assert response.status_code == 200


def test_expired_jwt_rejected(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    from app.models.enums import UserRole
    from app.security.jwt import create_access_token
    from tests.factories import create_strategist, seed_default_playbook

    seed_default_playbook(db_session, now=frozen_clock())
    strategist = create_strategist(
        db_session,
        email="expired@example.com",
        password="secure-password-1",
        now=frozen_clock(),
    )
    headers = login_headers(
        client,
        email="expired@example.com",
        password="secure-password-1",
    )
    tenant_id = create_tenant_as_strategist(client, headers)
    expired_token = create_access_token(
        user_id=strategist.id,
        role=UserRole.STRATEGIST,
        tenant_id=None,
        settings=get_settings(),
        now=frozen_clock() - timedelta(hours=2),
    )
    response = client.get(
        f"/tenants/{tenant_id}/users",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


def test_tampered_jwt_rejected(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    token = headers["Authorization"].removeprefix("Bearer ")
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
    response = client.get(
        f"/tenants/{tenant_id}/users",
        headers={"Authorization": f"Bearer {tampered}"},
    )
    assert response.status_code == 401


def test_wrong_algorithm_jwt_rejected(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    import warnings

    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    settings = get_settings()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", jwt.InsecureKeyLengthWarning)
        bad_token = jwt.encode(
            {
                "sub": str(uuid4()),
                "role": "strategist",
                "tenant_id": None,
                "exp": frozen_clock() + timedelta(minutes=5),
            },
            settings.jwt_secret,
            algorithm="HS512",
        )
    response = client.get(
        f"/tenants/{tenant_id}/users",
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert response.status_code == 401


def test_end_user_cannot_manage_tenant(
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
    response = client.get(f"/tenants/{tenant_id}/users", headers=end_user)
    assert response.status_code == 403


def test_customer_admin_cannot_create_tenant(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    create_customer_admin(
        db_session,
        tenant_id=tenant_id,
        email="admin@example.com",
        password="secure-password-1",
        now=frozen_clock(),
    )
    admin = login_headers(
        client,
        email="admin@example.com",
        password="secure-password-1",
        tenant_id=tenant_id,
    )
    response = client.post(
        "/tenants",
        headers=admin,
        json={"name": "Should Not Exist GmbH"},
    )
    assert response.status_code == 403
