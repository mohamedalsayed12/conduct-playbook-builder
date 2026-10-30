"""Idempotent seed script behaviour."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import StageEvent, StrategistAssignment, Tenant, User
from app.models.enums import UserRole, UserStage
from app.seed_data import (
    TENANT_LOGISTICS,
    TENANT_MANUFACTURING,
    demo_end_users,
    named_demo_email,
    named_demo_users,
    stage_counts,
    stuck_end_user_count,
)
from app.services.seed import count_seed_end_users, run_seed
from app.services.summary import compute_tenant_summary
from tests.conftest import FrozenClock


def test_seed_creates_expected_shape(
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    report = run_seed(db_session, clock=frozen_clock)
    assert report.playbooks_created == 1
    assert report.tenants_created == 2
    assert report.assignments_created == 2
    mfg_users = demo_end_users(TENANT_MANUFACTURING)
    log_users = demo_end_users(TENANT_LOGISTICS)
    expected_users = 1 + 2 + len(mfg_users) + len(log_users)
    assert report.users_created == expected_users
    assert (
        len(named_demo_users(TENANT_MANUFACTURING))
        + len(named_demo_users(TENANT_LOGISTICS))
        == 10
    )

    tenants = {
        tenant.name: tenant for tenant in db_session.scalars(select(Tenant)).all()
    }
    assert set(tenants) == {TENANT_MANUFACTURING, TENANT_LOGISTICS}
    mfg_id = tenants[TENANT_MANUFACTURING].id
    log_id = tenants[TENANT_LOGISTICS].id
    assert count_seed_end_users(db_session, mfg_id) == len(mfg_users)
    assert count_seed_end_users(db_session, log_id) == len(log_users)

    named_emails = {
        named_demo_email(spec)
        for spec in named_demo_users(TENANT_MANUFACTURING)
        + named_demo_users(TENANT_LOGISTICS)
    }
    stored_emails = set(
        db_session.scalars(select(User.email).where(User.email.in_(named_emails))).all()
    )
    assert stored_emails == named_emails

    mfg_summary = compute_tenant_summary(
        db_session, tenant_id=mfg_id, clock=frozen_clock
    )
    log_summary = compute_tenant_summary(
        db_session, tenant_id=log_id, clock=frozen_clock
    )
    assert mfg_summary.users_per_stage == stage_counts(mfg_users)
    assert log_summary.users_per_stage == stage_counts(log_users)
    assert mfg_summary.users_per_stage != log_summary.users_per_stage
    assert mfg_summary.stuck_count == stuck_end_user_count(mfg_users)
    assert log_summary.stuck_count == stuck_end_user_count(log_users)
    assert mfg_summary.stuck_count != log_summary.stuck_count

    events = db_session.scalar(select(func.count()).select_from(StageEvent))
    assert events is not None and events >= 40


def test_seed_is_idempotent(
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    first = run_seed(db_session, clock=frozen_clock)
    tenants_after_first = db_session.scalar(select(func.count()).select_from(Tenant))
    users_after_first = db_session.scalar(select(func.count()).select_from(User))
    assignments_after_first = db_session.scalar(
        select(func.count()).select_from(StrategistAssignment)
    )
    events_after_first = db_session.scalar(select(func.count()).select_from(StageEvent))

    second = run_seed(db_session, clock=frozen_clock)
    assert second.playbooks_created == 0
    assert second.tenants_created == 0
    assert second.users_created == 0
    assert second.assignments_created == 0
    assert first.users_created > 0

    assert db_session.scalar(select(func.count()).select_from(Tenant)) == (
        tenants_after_first
    )
    assert db_session.scalar(select(func.count()).select_from(User)) == (
        users_after_first
    )
    assignment_total = db_session.scalar(
        select(func.count()).select_from(StrategistAssignment)
    )
    assert assignment_total == assignments_after_first
    event_total = db_session.scalar(select(func.count()).select_from(StageEvent))
    assert event_total == events_after_first


def test_seed_users_span_all_stages(
    db_session: Session,
    frozen_clock: FrozenClock,
) -> None:
    run_seed(db_session, clock=frozen_clock)
    stages = set(
        db_session.scalars(
            select(User.stage).where(User.role == UserRole.END_USER).distinct()
        ).all()
    )
    assert stages == set(UserStage)
