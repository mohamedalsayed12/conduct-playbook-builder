"""HS256 JWT creation and validation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import Settings
from app.errors import AuthenticationError
from app.models.enums import UserRole

_JWT_ALGORITHM = "HS256"
_GENERIC_AUTH_ERROR = "Could not validate credentials"


def create_access_token(
    *,
    user_id: uuid.UUID,
    role: UserRole,
    tenant_id: uuid.UUID | None,
    settings: Settings,
    now: datetime | None = None,
) -> str:
    """Return a signed HS256 access token with sub, role, tenant_id, and exp."""
    issued_at = now if now is not None else datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role.value,
        "tenant_id": str(tenant_id) if tenant_id is not None else None,
        "exp": issued_at + timedelta(minutes=settings.jwt_expiry_minutes),
        "iat": issued_at,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decode and validate an access token; reject wrong algorithms and expiry."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[_JWT_ALGORITHM],
            options={"require": ["exp", "sub", "role"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError(_GENERIC_AUTH_ERROR) from exc

    if not isinstance(payload, dict):
        raise AuthenticationError(_GENERIC_AUTH_ERROR)
    return payload
