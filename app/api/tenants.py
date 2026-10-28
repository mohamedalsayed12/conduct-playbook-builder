"""Tenant HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import AppClock, DbSession, Phase2Caller
from app.schemas.tenants import TenantCreateRequest, TenantResponse
from app.services import tenants as tenant_service

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tenant(
    body: TenantCreateRequest,
    session: DbSession,
    clock: AppClock,
    _caller: Phase2Caller,
) -> TenantResponse:
    """Create a tenant and copy the default playbook."""
    tenant = tenant_service.create_tenant(session, name=body.name, clock=clock)
    return TenantResponse.model_validate(tenant)
