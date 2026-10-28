"""Helpers for authenticated API tests."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import FrozenClock
from tests.factories import create_strategist, seed_default_playbook

STRATEGIST_EMAIL = "strategist@example.com"
STRATEGIST_PASSWORD = "secure-password-1"


def bootstrap_strategist(
    client: TestClient,
    db_session: Session,
    clock: FrozenClock,
    *,
    email: str = STRATEGIST_EMAIL,
    password: str = STRATEGIST_PASSWORD,
) -> tuple[dict[str, str], str]:
    """Seed default playbook + strategist; return auth headers and strategist id."""
    seed_default_playbook(db_session, now=clock())
    strategist = create_strategist(
        db_session,
        email=email,
        password=password,
        now=clock(),
    )
    return login_headers(client, email=email, password=password), str(strategist.id)


def login_headers(
    client: TestClient,
    *,
    email: str,
    password: str,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, str]:
    """Return Authorization headers from POST /auth/token."""
    body: dict[str, object] = {"email": email, "password": password}
    if tenant_id is not None:
        body["tenant_id"] = str(tenant_id)
    response = client.post("/auth/token", json=body)
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_tenant_as_strategist(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Example Manufacturing GmbH",
) -> str:
    """Create a tenant with strategist auth and return its id."""
    response = client.post("/tenants", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])
