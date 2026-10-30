"""Login without tenant_id: unique email succeeds, duplicates stay generic."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from tests.auth_helpers import bootstrap_strategist, create_tenant_as_strategist
from tests.conftest import FrozenClock
from tests.factories import create_customer_admin

_PASSWORD = "secure-password-1"
_UNIQUE_EMAIL = "admin@example-manufacturing.example"
_SHARED_EMAIL = "shared.admin@example.com"


def test_login_without_tenant_id_accepts_unique_email(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(
        client, headers, name="Example Manufacturing GmbH"
    )
    create_customer_admin(
        db_session,
        tenant_id=tenant_id,
        email=_UNIQUE_EMAIL,
        password=_PASSWORD,
        now=frozen_clock(),
    )

    response = client.post(
        "/auth/token",
        json={"email": _UNIQUE_EMAIL, "password": _PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == UserRole.CUSTOMER_ADMIN.value
    assert body["tenant_id"] == tenant_id
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_without_tenant_id_rejects_duplicate_email_with_generic_error(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    manufacturing = create_tenant_as_strategist(
        client, headers, name="Example Manufacturing GmbH"
    )
    logistics = create_tenant_as_strategist(client, headers, name="Demo Logistics AG")
    create_customer_admin(
        db_session,
        tenant_id=manufacturing,
        email=_SHARED_EMAIL,
        password=_PASSWORD,
        now=frozen_clock(),
    )
    create_customer_admin(
        db_session,
        tenant_id=logistics,
        email=_SHARED_EMAIL,
        password=_PASSWORD,
        now=frozen_clock(),
    )
    create_customer_admin(
        db_session,
        tenant_id=manufacturing,
        email=_UNIQUE_EMAIL,
        password=_PASSWORD,
        now=frozen_clock(),
    )

    ambiguous = client.post(
        "/auth/token",
        json={"email": _SHARED_EMAIL, "password": _PASSWORD},
    )
    wrong_password = client.post(
        "/auth/token",
        json={"email": _UNIQUE_EMAIL, "password": "not-the-password"},
    )

    assert ambiguous.status_code == 401
    assert wrong_password.status_code == 401
    assert ambiguous.json()["detail"] == wrong_password.json()["detail"]
    assert "tenant" not in ambiguous.json()["detail"].lower()
