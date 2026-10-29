"""Canonical fictional seed constants shared by scripts and tests."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import SapRole, UserStage

SEED_STRATEGIST_EMAIL = "strategist@example.com"
SEED_STRATEGIST_PASSWORD = "seed-strategist-pass-1"

SEED_ADMIN_PASSWORD = "seed-admin-pass-1"
SEED_USER_PASSWORD = "seed-user-pass-1"

TENANT_MANUFACTURING = "Example Manufacturing GmbH"
TENANT_LOGISTICS = "Demo Logistics AG"

DEFAULT_PLAYBOOK_NAME = "Default Conduct Playbook"


@dataclass(frozen=True, slots=True)
class PlaybookStepSpec:
    """One default playbook step definition."""

    stage: UserStage
    position: int
    title: str
    description: str
    due_within_days: int


DEFAULT_PLAYBOOK_STEPS: tuple[PlaybookStepSpec, ...] = (
    PlaybookStepSpec(
        stage=UserStage.ACTIVATED,
        position=1,
        title="30-minute guided walkthrough",
        description="Complete the product walkthrough within 3 days.",
        due_within_days=3,
    ),
    PlaybookStepSpec(
        stage=UserStage.FIRST_USE,
        position=1,
        title="Run first system question",
        description="Ask the first question on own custom code within 7 days.",
        due_within_days=7,
    ),
    PlaybookStepSpec(
        stage=UserStage.ACTIVE,
        position=1,
        title="Weekly check-in",
        description="Confirm ongoing usage with the deployment strategist.",
        due_within_days=14,
    ),
)

# About 40 end users across both tenants (20 each), deterministic emails.
_SAP_CYCLE: tuple[SapRole, ...] = (
    SapRole.DEVELOPER,
    SapRole.ANALYST,
    SapRole.PROCESS_OWNER,
    SapRole.ARCHITECT,
)


@dataclass(frozen=True, slots=True)
class EndUserSpec:
    """One seeded end user and how far through onboarding they are."""

    email_local: str
    sap_role: SapRole
    stage: UserStage
    days_in_current_stage: int


def manufacturing_end_users() -> tuple[EndUserSpec, ...]:
    """Return 20 fictional end users for Example Manufacturing GmbH."""
    return _build_end_users("mfg", count=20)


def logistics_end_users() -> tuple[EndUserSpec, ...]:
    """Return 20 fictional end users for Demo Logistics AG."""
    return _build_end_users("log", count=20)


def _build_end_users(prefix: str, *, count: int) -> tuple[EndUserSpec, ...]:
    # Stage mix: invited, activated, first_use, active — some stuck (>= 7 days).
    stage_plan: list[tuple[UserStage, int]] = [
        (UserStage.INVITED, 2),
        (UserStage.INVITED, 10),  # stuck
        (UserStage.ACTIVATED, 1),
        (UserStage.ACTIVATED, 9),  # stuck
        (UserStage.FIRST_USE, 3),
        (UserStage.FIRST_USE, 12),  # stuck
        (UserStage.ACTIVE, 4),
        (UserStage.ACTIVE, 20),
    ]
    users: list[EndUserSpec] = []
    for index in range(count):
        stage, days = stage_plan[index % len(stage_plan)]
        users.append(
            EndUserSpec(
                email_local=f"{prefix}.user{index + 1:02d}",
                sap_role=_SAP_CYCLE[index % len(_SAP_CYCLE)],
                stage=stage,
                days_in_current_stage=days,
            )
        )
    return tuple(users)
