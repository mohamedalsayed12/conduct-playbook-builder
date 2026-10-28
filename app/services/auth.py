"""Authentication and access-token issuance."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import utc_now
from app.config import Settings, get_settings
from app.errors import AuthenticationError
from app.models import User
from app.models.enums import UserRole
from app.security.jwt import create_access_token
from app.security.passwords import verify_password

Clock = Callable[[], datetime]
logger = logging.getLogger(__name__)

_GENERIC_CREDENTIALS_ERROR = "Invalid credentials"


def issue_access_token(
    session: Session,
    *,
    email: str,
    password: str,
    tenant_id: uuid.UUID | None = None,
    settings: Settings | None = None,
    clock: Clock = utc_now,
) -> tuple[str, User]:
    """Validate credentials and return a JWT plus the authenticated user."""
    resolved = settings if settings is not None else get_settings()
    user = _find_user_for_login(session, email=email, tenant_id=tenant_id)
    if (
        user is None
        or user.password_hash is None
        or not verify_password(user.password_hash, password)
    ):
        logger.info("login_failed", extra={"reason": "invalid_credentials"})
        raise AuthenticationError(_GENERIC_CREDENTIALS_ERROR)

    token = create_access_token(
        user_id=user.id,
        role=user.role,
        tenant_id=user.tenant_id,
        settings=resolved,
        now=clock(),
    )
    logger.info(
        "login_succeeded",
        extra={"user_id": str(user.id), "role": user.role.value},
    )
    return token, user


def _find_user_for_login(
    session: Session,
    *,
    email: str,
    tenant_id: uuid.UUID | None,
) -> User | None:
    if tenant_id is None:
        statement = select(User).where(
            User.email == email,
            User.role == UserRole.STRATEGIST,
            User.tenant_id.is_(None),
        )
    else:
        statement = select(User).where(
            User.email == email,
            User.tenant_id == tenant_id,
        )
    return session.scalars(statement).first()
