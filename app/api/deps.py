"""FastAPI dependencies including authenticated current user."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.clock import Clock, utc_now
from app.config import Settings, get_settings
from app.db import get_session
from app.errors import AuthenticationError
from app.models import User
from app.models.enums import UserRole
from app.security.jwt import decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


def get_db_session() -> Iterator[Session]:
    """Yield a request-scoped database session."""
    yield from get_session()


def get_clock() -> Clock:
    """Return the process clock (overridable in tests)."""
    return utc_now


def get_current_user(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> User:
    """Load the authenticated user from a Bearer JWT."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Could not validate credentials")

    payload = decode_access_token(credentials.credentials, settings)
    try:
        user_id = uuid.UUID(str(payload["sub"]))
        role = UserRole(str(payload["role"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise AuthenticationError("Could not validate credentials") from exc

    user = session.get(User, user_id)
    if user is None or user.role != role:
        raise AuthenticationError("Could not validate credentials")
    return user


DbSession = Annotated[Session, Depends(get_db_session)]
AppClock = Annotated[Clock, Depends(get_clock)]
AppSettings = Annotated[Settings, Depends(get_settings)]
CurrentUser = Annotated[User, Depends(get_current_user)]
