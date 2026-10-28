"""FastAPI dependencies. Temporary Phase 2 caller is replaced in Phase 3."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.clock import Clock, utc_now
from app.config import Settings, get_settings
from app.db import get_session
from app.models.enums import UserRole


@dataclass(frozen=True, slots=True)
class Phase2TemporaryCaller:
    """
    PHASE 2 TEMPORARY AUTH STUB — replaced in Phase 3 by get_current_user.

    Endpoints depend on this so Phase 3 can swap the provider without rewriting
    every signature. It grants unrestricted access by design.
    """

    role: UserRole = UserRole.STRATEGIST


def get_db_session() -> Iterator[Session]:
    """Yield a request-scoped database session."""
    yield from get_session()


def get_clock() -> Clock:
    """Return the process clock (overridable in tests)."""
    return utc_now


def get_phase2_temporary_caller() -> Phase2TemporaryCaller:
    """Return the temporary unauthenticated caller used until Phase 3."""
    return Phase2TemporaryCaller()


DbSession = Annotated[Session, Depends(get_db_session)]
AppClock = Annotated[Clock, Depends(get_clock)]
AppSettings = Annotated[Settings, Depends(get_settings)]
Phase2Caller = Annotated[Phase2TemporaryCaller, Depends(get_phase2_temporary_caller)]
