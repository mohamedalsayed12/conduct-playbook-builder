"""Ensure invite and login logs never contain personal secrets."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth_helpers import bootstrap_strategist, create_tenant_as_strategist
from tests.conftest import FrozenClock

_FORBIDDEN_FRAGMENTS = (
    "developer@example.com",
    "strategist@example.com",
    "secure-password-1",
    "Bearer ",
)


def test_invite_and_login_logs_contain_no_personal_data(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
        tenant_id = create_tenant_as_strategist(client, headers)
        invite = client.post(
            f"/tenants/{tenant_id}/invites",
            headers=headers,
            json={"email": "developer@example.com", "sap_role": "developer"},
        ).json()
        token = invite["token"]
        client.post(
            "/invites/accept",
            json={"token": token, "password": "secure-password-1"},
        )
        client.post(
            "/auth/token",
            json={
                "email": "strategist@example.com",
                "password": "secure-password-1",
            },
        )

    combined = "\n".join(
        f"{record.getMessage()} {record.__dict__}" for record in caplog.records
    )
    for fragment in _FORBIDDEN_FRAGMENTS:
        assert fragment not in combined
    assert token not in combined
    assert headers["Authorization"].removeprefix("Bearer ") not in combined
