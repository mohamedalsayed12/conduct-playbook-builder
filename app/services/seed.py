"""Idempotent demo-data seeding for local and staging environments."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clock import utc_now
from app.models import (
    Playbook,
    PlaybookStep,
    StageEvent,
    StrategistAssignment,
    Tenant,
    User,
)
from app.models.enums import UserRole, UserStage
from app.security.passwords import hash_password
from app.seed_data import (
    DEFAULT_PLAYBOOK_NAME,
    DEFAULT_PLAYBOOK_STEPS,
    SEED_ADMIN_PASSWORD,
    SEED_STRATEGIST_EMAIL,
    SEED_STRATEGIST_PASSWORD,
    SEED_USER_PASSWORD,
    TENANT_LOGISTICS,
    TENANT_MANUFACTURING,
    EndUserSpec,
    logistics_end_users,
    manufacturing_end_users,
)
from app.services.tenants import copy_playbook_to_tenant, get_default_playbook

Clock = Callable[[], datetime]

logger = logging.getLogger(__name__)

_STAGE_PATH: dict[UserStage, tuple[UserStage, ...]] = {
    UserStage.INVITED: (UserStage.INVITED,),
    UserStage.ACTIVATED: (UserStage.INVITED, UserStage.ACTIVATED),
    UserStage.FIRST_USE: (
        UserStage.INVITED,
        UserStage.ACTIVATED,
        UserStage.FIRST_USE,
    ),
    UserStage.ACTIVE: (
        UserStage.INVITED,
        UserStage.ACTIVATED,
        UserStage.FIRST_USE,
        UserStage.ACTIVE,
    ),
}


@dataclass(frozen=True, slots=True)
class SeedReport:
    """Counts of rows created on this run (skips are not counted)."""

    playbooks_created: int
    tenants_created: int
    users_created: int
    assignments_created: int


def run_seed(session: Session, *, clock: Clock = utc_now) -> SeedReport:
    """Seed fictional tenants and users; safe to run repeatedly."""
    now = clock()
    playbooks_created = _ensure_default_playbook(session, now=now)
    strategist, strategist_created = _ensure_strategist(session, now=now)

    mfg, mfg_created = _ensure_tenant(session, name=TENANT_MANUFACTURING, now=now)
    logi, logi_created = _ensure_tenant(session, name=TENANT_LOGISTICS, now=now)

    assignments_created = 0
    assignments_created += _ensure_assignment(
        session, strategist_id=strategist.id, tenant_id=mfg.id, now=now
    )
    assignments_created += _ensure_assignment(
        session, strategist_id=strategist.id, tenant_id=logi.id, now=now
    )

    users_created = 0
    if strategist_created:
        users_created += 1

    admin_mfg_created = _ensure_customer_admin(
        session,
        tenant_id=mfg.id,
        email="admin@example-manufacturing.example",
        now=now,
    )
    admin_log_created = _ensure_customer_admin(
        session,
        tenant_id=logi.id,
        email="admin@demo-logistics.example",
        now=now,
    )
    users_created += admin_mfg_created + admin_log_created

    for tenant, specs in (
        (mfg, manufacturing_end_users()),
        (logi, logistics_end_users()),
    ):
        for spec in specs:
            users_created += _ensure_end_user(
                session,
                tenant_id=tenant.id,
                spec=spec,
                now=now,
            )

    session.commit()
    report = SeedReport(
        playbooks_created=playbooks_created,
        tenants_created=mfg_created + logi_created,
        users_created=users_created,
        assignments_created=assignments_created,
    )
    logger.info(
        "seed_complete",
        extra={
            "playbooks_created": report.playbooks_created,
            "tenants_created": report.tenants_created,
            "users_created": report.users_created,
            "assignments_created": report.assignments_created,
        },
    )
    return report


def _ensure_default_playbook(session: Session, *, now: datetime) -> int:
    existing = session.scalars(
        select(Playbook)
        .where(Playbook.tenant_id.is_(None))
        .order_by(Playbook.created_at.asc())
        .limit(1)
    ).first()
    if existing is not None:
        return 0
    playbook = Playbook(
        tenant_id=None,
        name=DEFAULT_PLAYBOOK_NAME,
        created_at=now,
    )
    session.add(playbook)
    session.flush()
    for step in DEFAULT_PLAYBOOK_STEPS:
        session.add(
            PlaybookStep(
                playbook_id=playbook.id,
                stage=step.stage,
                position=step.position,
                title=step.title,
                description=step.description,
                due_within_days=step.due_within_days,
            )
        )
    session.flush()
    return 1


def _ensure_strategist(session: Session, *, now: datetime) -> tuple[User, bool]:
    existing = session.scalars(
        select(User).where(
            User.role == UserRole.STRATEGIST,
            User.email == SEED_STRATEGIST_EMAIL,
            User.tenant_id.is_(None),
        )
    ).first()
    if existing is not None:
        return existing, False
    user = User(
        tenant_id=None,
        email=SEED_STRATEGIST_EMAIL,
        password_hash=hash_password(SEED_STRATEGIST_PASSWORD),
        role=UserRole.STRATEGIST,
        sap_role=None,
        stage=UserStage.ACTIVE,
        stage_changed_at=now,
        created_at=now,
    )
    session.add(user)
    session.flush()
    return user, True


def _ensure_tenant(
    session: Session,
    *,
    name: str,
    now: datetime,
) -> tuple[Tenant, int]:
    existing = session.scalars(select(Tenant).where(Tenant.name == name)).first()
    if existing is not None:
        return existing, 0
    tenant = Tenant(name=name, created_at=now)
    session.add(tenant)
    session.flush()
    default_playbook = get_default_playbook(session)
    copy_playbook_to_tenant(session, default_playbook, tenant.id, now)
    return tenant, 1


def _ensure_assignment(
    session: Session,
    *,
    strategist_id: uuid.UUID,
    tenant_id: uuid.UUID,
    now: datetime,
) -> int:
    existing = session.get(StrategistAssignment, (strategist_id, tenant_id))
    if existing is not None:
        return 0
    session.add(
        StrategistAssignment(
            strategist_id=strategist_id,
            tenant_id=tenant_id,
            assigned_at=now,
        )
    )
    session.flush()
    return 1


def _ensure_customer_admin(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    email: str,
    now: datetime,
) -> int:
    existing = session.scalars(
        select(User).where(
            User.tenant_id == tenant_id,
            User.email == email,
            User.role == UserRole.CUSTOMER_ADMIN,
        )
    ).first()
    if existing is not None:
        return 0
    session.add(
        User(
            tenant_id=tenant_id,
            email=email,
            password_hash=hash_password(SEED_ADMIN_PASSWORD),
            role=UserRole.CUSTOMER_ADMIN,
            sap_role=None,
            stage=UserStage.ACTIVE,
            stage_changed_at=now,
            created_at=now,
        )
    )
    session.flush()
    return 1


def _ensure_end_user(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    spec: EndUserSpec,
    now: datetime,
) -> int:
    email = f"{spec.email_local}@example.com"
    existing = session.scalars(
        select(User).where(User.tenant_id == tenant_id, User.email == email)
    ).first()
    if existing is not None:
        return 0

    path = _STAGE_PATH[spec.stage]
    # Walk history so the user arrived at `spec.stage` with the requested dwell time.
    entered_current = now - timedelta(days=spec.days_in_current_stage)
    step_gap = timedelta(days=2)
    timestamps: list[datetime] = []
    cursor = entered_current
    for _ in range(len(path) - 1):
        cursor = cursor - step_gap
        timestamps.append(cursor)
    timestamps.reverse()
    timestamps.append(entered_current)

    created_at = timestamps[0]
    user = User(
        tenant_id=tenant_id,
        email=email,
        password_hash=(
            None
            if spec.stage == UserStage.INVITED
            else hash_password(SEED_USER_PASSWORD)
        ),
        role=UserRole.END_USER,
        sap_role=spec.sap_role,
        stage=spec.stage,
        stage_changed_at=entered_current,
        created_at=created_at,
    )
    session.add(user)
    session.flush()

    previous: UserStage | None = None
    for stage, occurred_at in zip(path, timestamps, strict=True):
        session.add(
            StageEvent(
                tenant_id=tenant_id,
                user_id=user.id,
                from_stage=previous,
                to_stage=stage,
                occurred_at=occurred_at,
            )
        )
        previous = stage
    session.flush()
    return 1


def count_seed_end_users(session: Session, tenant_id: uuid.UUID) -> int:
    """Return end-user count for a tenant (used by idempotency tests)."""
    total = session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.tenant_id == tenant_id, User.role == UserRole.END_USER)
    )
    return int(total or 0)
