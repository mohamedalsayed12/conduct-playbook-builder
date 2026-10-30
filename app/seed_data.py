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

# Matches Settings.stuck_after_days. Active users are never counted as stuck.
SEED_STUCK_AFTER_DAYS = 7


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

# About 40 generated end users (20 each), plus 10 named demo colleagues.
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


# Early rollout: two full cycles plus four, so 20 users.
# Result: invited 6, activated 6, first_use 4, active 4; 8 stuck.
_MANUFACTURING_CYCLE: tuple[tuple[UserStage, int], ...] = (
    (UserStage.INVITED, 2),
    (UserStage.INVITED, 10),
    (UserStage.ACTIVATED, 1),
    (UserStage.ACTIVATED, 9),
    (UserStage.FIRST_USE, 3),
    (UserStage.FIRST_USE, 12),
    (UserStage.ACTIVE, 4),
    (UserStage.ACTIVE, 20),
)
_MANUFACTURING_STAGE_PLAN: tuple[tuple[UserStage, int], ...] = (
    _MANUFACTURING_CYCLE * 2 + _MANUFACTURING_CYCLE[:4]
)

# Later rollout: mostly active. 2 of 20 stuck, so the dashboard differs at a glance.
_LOGISTICS_STAGE_PLAN: tuple[tuple[UserStage, int], ...] = (
    (UserStage.INVITED, 1),
    (UserStage.INVITED, 15),
    (UserStage.ACTIVATED, 2),
    (UserStage.ACTIVATED, 11),
    (UserStage.FIRST_USE, 1),
    (UserStage.FIRST_USE, 2),
    (UserStage.FIRST_USE, 3),
    (UserStage.FIRST_USE, 4),
    *((UserStage.ACTIVE, 4),) * 12,
)


def manufacturing_end_users() -> tuple[EndUserSpec, ...]:
    """Return 20 fictional end users for Example Manufacturing GmbH."""
    return _build_end_users("mfg", _MANUFACTURING_STAGE_PLAN, count=20)


def logistics_end_users() -> tuple[EndUserSpec, ...]:
    """Return 20 fictional end users for Demo Logistics AG."""
    return _build_end_users("log", _LOGISTICS_STAGE_PLAN, count=20)


# Fictional colleagues for demos. Emails are unique so sign-in stays unambiguous.
_NAMED_DEMO_USERS: tuple[tuple[str, EndUserSpec], ...] = (
    (
        TENANT_MANUFACTURING,
        EndUserSpec("dana.vogel", SapRole.DEVELOPER, UserStage.FIRST_USE, 12),
    ),
    (
        TENANT_MANUFACTURING,
        EndUserSpec("jonas.keller", SapRole.ANALYST, UserStage.INVITED, 10),
    ),
    (
        TENANT_MANUFACTURING,
        EndUserSpec("mira.hoffmann", SapRole.PROCESS_OWNER, UserStage.ACTIVATED, 9),
    ),
    (
        TENANT_MANUFACTURING,
        EndUserSpec("lukas.berger", SapRole.ARCHITECT, UserStage.ACTIVE, 4),
    ),
    (
        TENANT_MANUFACTURING,
        EndUserSpec("anja.schmitt", SapRole.DEVELOPER, UserStage.ACTIVATED, 2),
    ),
    (
        TENANT_LOGISTICS,
        EndUserSpec("peter.lang", SapRole.ANALYST, UserStage.ACTIVE, 4),
    ),
    (
        TENANT_LOGISTICS,
        EndUserSpec("sofia.meier", SapRole.PROCESS_OWNER, UserStage.FIRST_USE, 3),
    ),
    (
        TENANT_LOGISTICS,
        EndUserSpec("henrik.wolf", SapRole.DEVELOPER, UserStage.INVITED, 15),
    ),
    (
        TENANT_LOGISTICS,
        EndUserSpec("clara.neumann", SapRole.ARCHITECT, UserStage.ACTIVE, 4),
    ),
    (
        TENANT_LOGISTICS,
        EndUserSpec("tobias.klein", SapRole.ANALYST, UserStage.ACTIVATED, 1),
    ),
)


def named_demo_users(tenant_name: str) -> tuple[EndUserSpec, ...]:
    """Return the named fictional end users for one demo tenant."""
    return tuple(spec for name, spec in _NAMED_DEMO_USERS if name == tenant_name)


def demo_end_users(tenant_name: str) -> tuple[EndUserSpec, ...]:
    """Return generated plus named end users for one demo tenant."""
    if tenant_name == TENANT_MANUFACTURING:
        generated = manufacturing_end_users()
    elif tenant_name == TENANT_LOGISTICS:
        generated = logistics_end_users()
    else:
        message = f"Unknown demo tenant: {tenant_name}"
        raise ValueError(message)
    return generated + named_demo_users(tenant_name)


def named_demo_email(spec: EndUserSpec) -> str:
    """Return the stored email for a named demo user."""
    return f"{spec.email_local}@example.com"


def stage_counts(users: tuple[EndUserSpec, ...]) -> dict[UserStage, int]:
    """Return how many seeded end users sit in each stage."""
    counts = {stage: 0 for stage in UserStage}
    for user in users:
        counts[user.stage] += 1
    return counts


def stuck_end_user_count(users: tuple[EndUserSpec, ...]) -> int:
    """Return how many seeded end users count as stuck (active excluded)."""
    return sum(
        1
        for user in users
        if user.stage != UserStage.ACTIVE
        and user.days_in_current_stage >= SEED_STUCK_AFTER_DAYS
    )


def _build_end_users(
    prefix: str,
    stage_plan: tuple[tuple[UserStage, int], ...],
    *,
    count: int,
) -> tuple[EndUserSpec, ...]:
    if len(stage_plan) != count:
        message = f"{prefix} stage plan must contain {count} users"
        raise ValueError(message)
    users: list[EndUserSpec] = []
    for index, (stage, days) in enumerate(stage_plan):
        users.append(
            EndUserSpec(
                email_local=f"{prefix}.user{index + 1:02d}",
                sap_role=_SAP_CYCLE[index % len(_SAP_CYCLE)],
                stage=stage,
                days_in_current_stage=days,
            )
        )
    return tuple(users)
