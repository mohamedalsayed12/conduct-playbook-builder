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

DEFAULT_PLAYBOOK_NAME = "Default Conduct deployment playbook"

# Matches Settings.stuck_after_days. Active users are never counted as stuck.
SEED_STUCK_AFTER_DAYS = 7

USERS_PER_TENANT = 100

_SAP_ROLE_WEIGHTS: tuple[tuple[SapRole, int], ...] = (
    (SapRole.DEVELOPER, 40),
    (SapRole.ANALYST, 30),
    (SapRole.PROCESS_OWNER, 20),
    (SapRole.ARCHITECT, 10),
)


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
        title="48-hour Conduct orientation",
        description=(
            "Complete the guided walkthrough: connect to the customer SAP "
            "landscape and see how Conduct reads custom code."
        ),
        due_within_days=3,
    ),
    PlaybookStepSpec(
        stage=UserStage.FIRST_USE,
        position=1,
        title="First question on own custom code",
        description=(
            "Ask Conduct about a real dependency or change in the team's "
            "custom code so first value lands on their system."
        ),
        due_within_days=7,
    ),
    PlaybookStepSpec(
        stage=UserStage.ACTIVE,
        position=1,
        title="Weekly deployment check-in",
        description=(
            "Confirm ongoing use with the deployment strategist: stuck work, "
            "S/4 or change pipelines, and next playbook actions."
        ),
        due_within_days=14,
    ),
)


@dataclass(frozen=True, slots=True)
class EndUserSpec:
    """One seeded end user and how far through onboarding they are."""

    email_local: str
    sap_role: SapRole
    stage: UserStage
    days_in_current_stage: int


_MANUFACTURING_STAGE_COUNTS: dict[UserStage, int] = {
    UserStage.INVITED: 28,
    UserStage.ACTIVATED: 28,
    UserStage.FIRST_USE: 22,
    UserStage.ACTIVE: 22,
}
_MANUFACTURING_DAYS: dict[UserStage, tuple[int, ...]] = {
    UserStage.INVITED: (2, 8, 12, 18),
    UserStage.ACTIVATED: (1, 4, 9, 14),
    UserStage.FIRST_USE: (3, 6, 11, 16),
    UserStage.ACTIVE: (4, 10, 20, 30),
}

_LOGISTICS_STAGE_COUNTS: dict[UserStage, int] = {
    UserStage.INVITED: 8,
    UserStage.ACTIVATED: 12,
    UserStage.FIRST_USE: 20,
    UserStage.ACTIVE: 60,
}
_LOGISTICS_DAYS: dict[UserStage, tuple[int, ...]] = {
    UserStage.INVITED: (1, 10, 15),
    UserStage.ACTIVATED: (2, 5, 11),
    UserStage.FIRST_USE: (1, 3, 4, 8),
    UserStage.ACTIVE: (4, 12, 20, 40),
}


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
        generated = _build_end_users(
            "mfg",
            _stage_plan(_MANUFACTURING_STAGE_COUNTS, _MANUFACTURING_DAYS),
        )
    elif tenant_name == TENANT_LOGISTICS:
        generated = _build_end_users(
            "log",
            _stage_plan(_LOGISTICS_STAGE_COUNTS, _LOGISTICS_DAYS),
        )
    else:
        message = f"Unknown demo tenant: {tenant_name}"
        raise ValueError(message)
    return generated + named_demo_users(tenant_name)


def demo_email(spec: EndUserSpec) -> str:
    """Return the email stored for a seeded end user."""
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


def _sap_role_for_index(index: int) -> SapRole:
    slot = index % 100
    cursor = 0
    for role, weight in _SAP_ROLE_WEIGHTS:
        cursor += weight
        if slot < cursor:
            return role
    return SapRole.DEVELOPER


def _stage_plan(
    counts: dict[UserStage, int],
    days_by_stage: dict[UserStage, tuple[int, ...]],
) -> tuple[tuple[UserStage, int], ...]:
    total = sum(counts.values())
    if total != USERS_PER_TENANT:
        message = f"stage counts must sum to {USERS_PER_TENANT}, got {total}"
        raise ValueError(message)
    plan: list[tuple[UserStage, int]] = []
    for stage in (
        UserStage.INVITED,
        UserStage.ACTIVATED,
        UserStage.FIRST_USE,
        UserStage.ACTIVE,
    ):
        days_opts = days_by_stage[stage]
        for index in range(counts[stage]):
            plan.append((stage, days_opts[index % len(days_opts)]))
    return tuple(plan)


def _build_end_users(
    prefix: str,
    stage_plan: tuple[tuple[UserStage, int], ...],
) -> tuple[EndUserSpec, ...]:
    if len(stage_plan) != USERS_PER_TENANT:
        message = f"{prefix} stage plan must contain {USERS_PER_TENANT} users"
        raise ValueError(message)
    users: list[EndUserSpec] = []
    for index, (stage, days) in enumerate(stage_plan):
        users.append(
            EndUserSpec(
                email_local=f"{prefix}.user{index + 1:02d}",
                sap_role=_sap_role_for_index(index),
                stage=stage,
                days_in_current_stage=days,
            )
        )
    return tuple(users)
