"""Integration tests for database constraints on the real Postgres test DB."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    SapRole,
    StrategistAssignment,
    Tenant,
    User,
    UserRole,
    UserStage,
)


def _create_tenant(session: Session, name: str) -> Tenant:
    tenant = Tenant(name=name)
    session.add(tenant)
    session.flush()
    return tenant


def _create_end_user(session: Session, tenant_id: uuid.UUID, email: str) -> User:
    user = User(
        tenant_id=tenant_id,
        email=email,
        role=UserRole.END_USER,
        sap_role=SapRole.DEVELOPER,
        stage=UserStage.INVITED,
    )
    session.add(user)
    session.flush()
    return user


def _create_strategist(session: Session, email: str) -> User:
    user = User(
        tenant_id=None,
        email=email,
        role=UserRole.STRATEGIST,
        sap_role=None,
        stage=UserStage.ACTIVE,
    )
    session.add(user)
    session.flush()
    return user


def test_email_unique_per_tenant(db_session: Session) -> None:
    tenant_a = _create_tenant(db_session, "Example Manufacturing GmbH")
    tenant_b = _create_tenant(db_session, "Demo Logistics AG")
    email = "user@example.com"

    _create_end_user(db_session, tenant_a.id, email)
    _create_end_user(db_session, tenant_b.id, email)

    with pytest.raises(IntegrityError):
        _create_end_user(db_session, tenant_a.id, email)


def test_strategist_must_have_null_tenant_id(db_session: Session) -> None:
    tenant = _create_tenant(db_session, "Example Manufacturing GmbH")

    with pytest.raises(IntegrityError):
        db_session.add(
            User(
                tenant_id=tenant.id,
                email="strategist@example.com",
                role=UserRole.STRATEGIST,
                sap_role=None,
                stage=UserStage.ACTIVE,
            )
        )
        db_session.flush()


def test_non_strategist_must_have_tenant_id(db_session: Session) -> None:
    with pytest.raises(IntegrityError):
        db_session.add(
            User(
                tenant_id=None,
                email="admin@example.com",
                role=UserRole.CUSTOMER_ADMIN,
                sap_role=None,
                stage=UserStage.ACTIVATED,
            )
        )
        db_session.flush()


def test_duplicate_strategist_assignment_rejected(db_session: Session) -> None:
    tenant = _create_tenant(db_session, "Example Manufacturing GmbH")
    strategist = _create_strategist(db_session, "strategist@example.com")

    db_session.add(
        StrategistAssignment(strategist_id=strategist.id, tenant_id=tenant.id)
    )
    db_session.flush()

    with pytest.raises(IntegrityError):
        db_session.add(
            StrategistAssignment(strategist_id=strategist.id, tenant_id=tenant.id)
        )
        db_session.flush()
