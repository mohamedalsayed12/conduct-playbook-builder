"""Tenant rollout summary and stuck-user queries."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.clock import utc_now
from app.config import Settings, get_settings
from app.errors import ValidationAppError
from app.models import Playbook, StageEvent, User
from app.models.enums import SapRole, UserStage
from app.schemas.summary import (
    StuckUserListResponse,
    StuckUserResponse,
    TenantSummaryResponse,
)
from app.schemas.users import PlaybookStepResponse
from app.services.scoping import require_management_role, require_tenant_access
from app.services.summary_cache import (
    invalidate_summary_cache,
    read_summary_cache,
    write_summary_cache,
)

Clock = Callable[[], datetime]

_SECONDS_PER_DAY = 86400.0


def get_tenant_summary(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    actor: User,
    settings: Settings | None = None,
    clock: Clock = utc_now,
) -> TenantSummaryResponse:
    """Return rollout summary, preferring Redis cache when available."""
    require_management_role(actor)
    require_tenant_access(session, actor, tenant_id)
    resolved = settings if settings is not None else get_settings()

    cached = read_summary_cache(tenant_id)
    if cached is not None:
        return TenantSummaryResponse.model_validate_json(cached)

    summary = compute_tenant_summary(
        session,
        tenant_id=tenant_id,
        settings=resolved,
        clock=clock,
    )
    write_summary_cache(
        tenant_id,
        summary.model_dump_json(),
        ttl_seconds=resolved.summary_cache_ttl_seconds,
    )
    return summary


def compute_tenant_summary(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    clock: Clock = utc_now,
) -> TenantSummaryResponse:
    """Compute rollout aggregates in SQL (no Python row loops)."""
    resolved = settings if settings is not None else get_settings()
    now = clock()
    stuck_threshold = now - timedelta(days=resolved.stuck_after_days)

    users_per_stage = _empty_stage_counts()
    for stage, count in session.execute(
        select(User.stage, func.count())
        .where(User.tenant_id == tenant_id)
        .group_by(User.stage)
    ):
        users_per_stage[UserStage(stage)] = int(count)

    users_per_sap_role_per_stage = _empty_sap_role_matrix()
    for stage, sap_role, count in session.execute(
        select(User.stage, User.sap_role, func.count())
        .where(User.tenant_id == tenant_id, User.sap_role.is_not(None))
        .group_by(User.stage, User.sap_role)
    ):
        if sap_role is None:
            continue
        users_per_sap_role_per_stage[UserStage(stage)][SapRole(sap_role)] = int(count)

    stuck_count = session.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.tenant_id == tenant_id,
            User.stage_changed_at <= stuck_threshold,
        )
    )
    if stuck_count is None:
        stuck_count = 0

    average_days_per_stage = _average_days_per_stage(
        session, tenant_id=tenant_id, now=now
    )

    return TenantSummaryResponse(
        tenant_id=tenant_id,
        users_per_stage=users_per_stage,
        users_per_sap_role_per_stage=users_per_sap_role_per_stage,
        stuck_count=int(stuck_count),
        average_days_per_stage=average_days_per_stage,
        computed_at=now,
    )


def list_stuck_users(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    actor: User,
    limit: int | None = None,
    offset: int = 0,
    settings: Settings | None = None,
    clock: Clock = utc_now,
) -> StuckUserListResponse:
    """Return a paginated list of users past the stuck threshold."""
    require_management_role(actor)
    require_tenant_access(session, actor, tenant_id)
    resolved = settings if settings is not None else get_settings()
    page_size = resolved.default_page_size if limit is None else limit
    if page_size < 1 or page_size > resolved.max_page_size:
        raise ValidationAppError(
            f"limit must be between 1 and {resolved.max_page_size}."
        )
    if offset < 0:
        raise ValidationAppError("offset must be >= 0.")

    now = clock()
    stuck_threshold = now - timedelta(days=resolved.stuck_after_days)
    stuck_filter = (
        User.tenant_id == tenant_id,
        User.stage_changed_at <= stuck_threshold,
    )

    total = session.scalar(select(func.count()).select_from(User).where(*stuck_filter))
    if total is None:
        total = 0

    users = list(
        session.scalars(
            select(User)
            .where(*stuck_filter)
            .order_by(User.stage_changed_at.asc(), User.id.asc())
            .limit(page_size)
            .offset(offset)
        ).all()
    )
    next_steps = _first_steps_by_stage(session, tenant_id)

    items = [
        StuckUserResponse(
            user_id=user.id,
            email=user.email,
            stage=user.stage,
            stage_changed_at=user.stage_changed_at,
            days_stuck=_days_between(user.stage_changed_at, now),
            next_step=next_steps.get(user.stage),
        )
        for user in users
    ]
    return StuckUserListResponse(
        items=items,
        total=int(total),
        limit=page_size,
        offset=offset,
    )


def invalidate_tenant_summary_after_commit(tenant_id: uuid.UUID) -> None:
    """Drop the summary cache after the DB transaction has committed."""
    invalidate_summary_cache(tenant_id)


def _average_days_per_stage(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    now: datetime,
) -> dict[UserStage, float]:
    spans = (
        select(
            StageEvent.to_stage.label("stage"),
            StageEvent.occurred_at.label("entered_at"),
            func.lead(StageEvent.occurred_at)
            .over(
                partition_by=StageEvent.user_id,
                order_by=(StageEvent.occurred_at, StageEvent.id),
            )
            .label("left_at"),
        )
        .where(StageEvent.tenant_id == tenant_id)
        .subquery()
    )
    duration_days = (
        func.extract(
            "epoch",
            func.coalesce(spans.c.left_at, now) - spans.c.entered_at,
        )
        / _SECONDS_PER_DAY
    )
    averages = _empty_stage_floats()
    for stage, average in session.execute(
        select(spans.c.stage, func.avg(duration_days)).group_by(spans.c.stage)
    ):
        averages[UserStage(stage)] = float(average)
    return averages


def _first_steps_by_stage(
    session: Session,
    tenant_id: uuid.UUID,
) -> dict[UserStage, PlaybookStepResponse]:
    playbook = session.scalars(
        select(Playbook)
        .where(Playbook.tenant_id == tenant_id)
        .options(selectinload(Playbook.steps))
        .order_by(Playbook.created_at.asc())
        .limit(1)
    ).first()
    if playbook is None:
        return {}

    by_stage: dict[UserStage, PlaybookStepResponse] = {}
    for step in sorted(playbook.steps, key=lambda item: (item.stage, item.position)):
        if step.stage not in by_stage:
            by_stage[step.stage] = PlaybookStepResponse.model_validate(step)
    return by_stage


def _days_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / _SECONDS_PER_DAY


def _empty_stage_counts() -> dict[UserStage, int]:
    return {stage: 0 for stage in UserStage}


def _empty_stage_floats() -> dict[UserStage, float]:
    return {stage: 0.0 for stage in UserStage}


def _empty_sap_role_matrix() -> dict[UserStage, dict[SapRole, int]]:
    return {stage: {role: 0 for role in SapRole} for stage in UserStage}
