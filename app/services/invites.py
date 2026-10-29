"""Invite creation and acceptance."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import utc_now
from app.config import Settings, get_settings
from app.errors import ConflictError, InviteTokenInvalidError
from app.models import Invite, StageEvent, User
from app.models.enums import SapRole, UserRole, UserStage
from app.security.emails import normalize_email
from app.security.invite_tokens import generate_invite_token, hash_invite_token
from app.security.passwords import hash_password
from app.services.scoping import require_management_role, require_tenant_access
from app.services.stages import assert_transition_allowed
from app.services.summary import invalidate_tenant_summary_after_commit

Clock = Callable[[], datetime]

_GENERIC_INVITE_ERROR = "Invite is invalid or has expired"


def create_invite(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    email: str,
    sap_role: SapRole,
    actor: User,
    settings: Settings | None = None,
    clock: Clock = utc_now,
) -> tuple[Invite, User, str]:
    """Create an invited end user and return the invite, user, and raw token once."""
    require_management_role(actor)
    require_tenant_access(session, actor, tenant_id)
    resolved = settings if settings is not None else get_settings()
    now = clock()
    normalized_email = normalize_email(email)

    existing = session.scalars(
        select(User).where(
            User.tenant_id == tenant_id,
            User.email == normalized_email,
        )
    ).first()
    if existing is not None:
        raise ConflictError("A user with this email already exists in the tenant.")

    user = User(
        tenant_id=tenant_id,
        email=normalized_email,
        password_hash=None,
        role=UserRole.END_USER,
        sap_role=sap_role,
        stage=UserStage.INVITED,
        stage_changed_at=now,
        created_at=now,
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "A user with this email already exists in the tenant."
        ) from exc

    raw_token = generate_invite_token()
    invite = Invite(
        user_id=user.id,
        token_hash=hash_invite_token(raw_token),
        expires_at=now + timedelta(hours=resolved.invite_expiry_hours),
        used_at=None,
    )
    session.add(invite)
    session.add(
        StageEvent(
            tenant_id=tenant_id,
            user_id=user.id,
            from_stage=None,
            to_stage=UserStage.INVITED,
            occurred_at=now,
        )
    )
    session.commit()
    invalidate_tenant_summary_after_commit(tenant_id)
    session.refresh(invite)
    session.refresh(user)
    return invite, user, raw_token


def accept_invite(
    session: Session,
    *,
    raw_token: str,
    password: str,
    clock: Clock = utc_now,
) -> User:
    """Accept an invite: hash password, mark used, activate user, write StageEvent."""
    now = clock()
    invite = _load_usable_invite(session, raw_token=raw_token, now=now)
    user = session.scalars(
        select(User).where(User.id == invite.user_id).with_for_update()
    ).first()
    if user is None or user.tenant_id is None:
        raise InviteTokenInvalidError(_GENERIC_INVITE_ERROR)
    tenant_id = user.tenant_id

    assert_transition_allowed(user.stage, UserStage.ACTIVATED)
    from_stage = user.stage
    user.password_hash = hash_password(password)
    user.stage = UserStage.ACTIVATED
    user.stage_changed_at = now
    invite.used_at = now
    session.add(
        StageEvent(
            tenant_id=tenant_id,
            user_id=user.id,
            from_stage=from_stage,
            to_stage=UserStage.ACTIVATED,
            occurred_at=now,
        )
    )
    session.commit()
    invalidate_tenant_summary_after_commit(tenant_id)
    session.refresh(user)
    return user


def _load_usable_invite(
    session: Session,
    *,
    raw_token: str,
    now: datetime,
) -> Invite:
    token_hash = hash_invite_token(raw_token)
    invite = session.scalars(
        select(Invite).where(Invite.token_hash == token_hash).with_for_update()
    ).first()
    if invite is None or invite.used_at is not None or invite.expires_at <= now:
        raise InviteTokenInvalidError(_GENERIC_INVITE_ERROR)
    return invite
