"""Playbook HTTP routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.playbooks import PlaybookResponse
from app.schemas.users import PlaybookStepResponse
from app.services import playbooks as playbook_service

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["playbooks"])


@router.get("/playbook", response_model=PlaybookResponse)
def get_tenant_playbook(
    tenant_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> PlaybookResponse:
    """Return the tenant playbook with steps grouped by stage."""
    playbook, grouped = playbook_service.get_tenant_playbook_grouped(
        session,
        tenant_id=tenant_id,
        actor=current_user,
    )
    steps_by_stage = {
        stage: [PlaybookStepResponse.model_validate(step) for step in steps]
        for stage, steps in grouped.items()
    }
    return PlaybookResponse(
        id=playbook.id,
        tenant_id=playbook.tenant_id,
        name=playbook.name,
        created_at=playbook.created_at,
        steps_by_stage=steps_by_stage,
    )
