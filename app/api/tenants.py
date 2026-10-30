"""Tenant HTTP routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import AppClock, CurrentUser, DbSession
from app.schemas.assignments import StrategistAssignmentResponse
from app.schemas.tenants import (
    TenantCreateRequest,
    TenantListResponse,
    TenantResponse,
)
from app.services import assignments as assignment_service
from app.services import tenants as tenant_service

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=TenantListResponse)
def list_tenants(
    session: DbSession,
    current_user: CurrentUser,
) -> TenantListResponse:
    """List tenants the caller can access (assignments or own tenant)."""
    tenants = tenant_service.list_accessible_tenants(session, actor=current_user)
    return TenantListResponse(
        items=[TenantResponse.model_validate(tenant) for tenant in tenants]
    )


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tenant(
    body: TenantCreateRequest,
    session: DbSession,
    clock: AppClock,
    current_user: CurrentUser,
) -> TenantResponse:
    """Create a tenant and copy the default playbook."""
    tenant = tenant_service.create_tenant(
        session,
        name=body.name,
        actor=current_user,
        clock=clock,
    )
    return TenantResponse.model_validate(tenant)


@router.post(
    "/{tenant_id}/strategists/{strategist_id}",
    response_model=StrategistAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_strategist(
    tenant_id: uuid.UUID,
    strategist_id: uuid.UUID,
    session: DbSession,
    clock: AppClock,
    current_user: CurrentUser,
) -> StrategistAssignmentResponse:
    """Assign a strategist to a tenant (strategist-only)."""
    assignment = assignment_service.assign_strategist(
        session,
        tenant_id=tenant_id,
        strategist_id=strategist_id,
        actor=current_user,
        clock=clock,
    )
    return StrategistAssignmentResponse.model_validate(assignment)
