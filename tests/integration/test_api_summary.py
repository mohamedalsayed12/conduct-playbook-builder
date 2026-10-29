"""Integration tests for rollout summary, stuck users, and Redis cache."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.cache import get_redis
from app.models.enums import UserStage
from app.services import summary as summary_service
from app.services.summary_cache import summary_cache_key
from tests.auth_helpers import (
    bootstrap_strategist,
    create_tenant_as_strategist,
    login_headers,
)
from tests.conftest import FrozenClock
from tests.factories import create_customer_admin


@pytest.fixture(autouse=True)
def _clear_summary_cache_keys() -> Iterator[None]:
    """Drop summary keys so Redis state does not leak across rolled-back DB tests."""
    yield
    try:
        client = get_redis()
        for key in client.scan_iter(match="summary:v1:*"):
            client.delete(key)
    except (RedisError, OSError):
        pass


def test_summary_counts_stuck_and_average_days(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    start = frozen_clock()

    invite_a = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "alex@example.com", "sap_role": "developer"},
    )
    assert invite_a.status_code == 201
    token_a = invite_a.json()["token"]
    user_a = invite_a.json()["user_id"]

    frozen_clock.set(start + timedelta(days=2))
    accept = client.post(
        "/invites/accept",
        json={"token": token_a, "password": "secure-password-1"},
    )
    assert accept.status_code == 200

    frozen_clock.set(start + timedelta(days=5))
    advance = client.post(
        f"/tenants/{tenant_id}/users/{user_a}/advance",
        headers=headers,
    )
    assert advance.status_code == 200

    frozen_clock.set(start + timedelta(days=6))
    invite_b = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "blake@example.com", "sap_role": "analyst"},
    )
    assert invite_b.status_code == 201

    frozen_clock.set(start + timedelta(days=8))
    advance_again = client.post(
        f"/tenants/{tenant_id}/users/{user_a}/advance",
        headers=headers,
    )
    assert advance_again.status_code == 200

    # Day 14: stuck threshold is day 7. Blake (changed day 6) stuck; Alex (day 8) not.
    frozen_clock.set(start + timedelta(days=14))

    summary = client.get(f"/tenants/{tenant_id}/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["users_per_stage"]["active"] == 1
    assert body["users_per_stage"]["invited"] == 1
    assert body["users_per_sap_role_per_stage"]["active"]["developer"] == 1
    assert body["users_per_sap_role_per_stage"]["invited"]["analyst"] == 1
    # Threshold day 7; Alex stage_changed_at day 8 → not stuck. Blake day 6 → stuck.
    assert body["stuck_count"] == 1
    # Alex: 2d invited, 3d activated, 3d first_use, 6d active. Blake: 8d invited.
    assert body["average_days_per_stage"]["invited"] == pytest.approx(5.0)
    assert body["average_days_per_stage"]["activated"] == pytest.approx(3.0)
    assert body["average_days_per_stage"]["first_use"] == pytest.approx(3.0)
    assert body["average_days_per_stage"]["active"] == pytest.approx(6.0)

    stuck = client.get(f"/tenants/{tenant_id}/stuck", headers=headers)
    assert stuck.status_code == 200
    stuck_body = stuck.json()
    assert stuck_body["total"] == 1
    assert stuck_body["items"][0]["email"] == "blake@example.com"
    assert stuck_body["items"][0]["stage"] == "invited"
    assert stuck_body["items"][0]["days_stuck"] == pytest.approx(8.0)
    assert stuck_body["items"][0]["next_step"] is None


def test_summary_cache_hit_skips_db_compute(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)

    first = client.get(f"/tenants/{tenant_id}/summary", headers=headers)
    assert first.status_code == 200

    with patch.object(
        summary_service,
        "compute_tenant_summary",
        side_effect=AssertionError("DB compute must not run on cache hit"),
    ):
        second = client.get(f"/tenants/{tenant_id}/summary", headers=headers)
    assert second.status_code == 200
    assert second.json() == first.json()


def test_summary_invalidated_after_invite_accept_and_advance(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)

    empty = client.get(f"/tenants/{tenant_id}/summary", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["users_per_stage"]["invited"] == 0

    invite = client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "casey@example.com", "sap_role": "architect"},
    )
    assert invite.status_code == 201
    after_invite = client.get(f"/tenants/{tenant_id}/summary", headers=headers)
    assert after_invite.json()["users_per_stage"]["invited"] == 1

    accept = client.post(
        "/invites/accept",
        json={
            "token": invite.json()["token"],
            "password": "secure-password-1",
        },
    )
    assert accept.status_code == 200
    after_accept = client.get(f"/tenants/{tenant_id}/summary", headers=headers)
    assert after_accept.json()["users_per_stage"]["invited"] == 0
    assert after_accept.json()["users_per_stage"]["activated"] == 1

    user_id = invite.json()["user_id"]
    advance = client.post(
        f"/tenants/{tenant_id}/users/{user_id}/advance",
        headers=headers,
    )
    assert advance.status_code == 200
    after_advance = client.get(f"/tenants/{tenant_id}/summary", headers=headers)
    assert after_advance.json()["users_per_stage"]["activated"] == 0
    assert after_advance.json()["users_per_stage"]["first_use"] == 1


def test_summary_works_when_redis_is_down(
    client: TestClient,
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    headers, _ = bootstrap_strategist(client, db_session, frozen_clock)
    tenant_id = create_tenant_as_strategist(client, headers)
    client.post(
        f"/tenants/{tenant_id}/invites",
        headers=headers,
        json={"email": "drew@example.com", "sap_role": "process_owner"},
    )

    with patch(
        "app.services.summary_cache.get_redis",
        side_effect=RedisError("redis down"),
    ):
        response = client.get(f"/tenants/{tenant_id}/summary", headers=headers)
    assert response.status_code == 200
    assert response.json()["users_per_stage"]["invited"] == 1


def test_stuck_list_includes_next_playbook_step(
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
        json={"email": "erin@example.com", "sap_role": "developer"},
    )
    token = invite.json()["token"]
    user_id = invite.json()["user_id"]
    client.post(
        "/invites/accept",
        json={"token": token, "password": "secure-password-1"},
    )

    frozen_clock.set(start + timedelta(days=10))
    stuck = client.get(f"/tenants/{tenant_id}/stuck", headers=headers)
    assert stuck.status_code == 200
    item = stuck.json()["items"][0]
    assert item["user_id"] == user_id
    assert item["stage"] == UserStage.ACTIVATED.value
    assert item["next_step"]["title"] == "30-minute guided walkthrough"
    assert item["days_stuck"] == pytest.approx(10.0)


def test_customer_admin_can_read_own_summary(
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
    admin_headers = login_headers(
        client,
        email="admin@example.com",
        password="secure-password-1",
        tenant_id=tenant_id,
    )
    response = client.get(f"/tenants/{tenant_id}/summary", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["tenant_id"] == tenant_id


def test_summary_cache_key_is_versioned() -> None:
    import uuid

    tenant_id = uuid.uuid4()
    assert summary_cache_key(tenant_id) == f"summary:v1:{tenant_id}"
