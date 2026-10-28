"""Onboarding stage transition rules."""

from app.errors import InvalidStageTransitionError
from app.models.enums import UserStage

STAGE_ORDER: tuple[UserStage, ...] = (
    UserStage.INVITED,
    UserStage.ACTIVATED,
    UserStage.FIRST_USE,
    UserStage.ACTIVE,
)

_STAGE_INDEX = {stage: index for index, stage in enumerate(STAGE_ORDER)}


def next_stage(current: UserStage) -> UserStage:
    """Return the only legal next stage, or raise if the user cannot advance."""
    index = _STAGE_INDEX[current]
    if index >= len(STAGE_ORDER) - 1:
        raise InvalidStageTransitionError(
            f"Cannot advance beyond stage '{current.value}'."
        )
    return STAGE_ORDER[index + 1]


def assert_transition_allowed(from_stage: UserStage, to_stage: UserStage) -> None:
    """Raise when to_stage is not exactly one step forward from from_stage."""
    expected_index = _STAGE_INDEX[from_stage] + 1
    if expected_index >= len(STAGE_ORDER) or STAGE_ORDER[expected_index] != to_stage:
        raise InvalidStageTransitionError(
            f"Cannot transition from '{from_stage.value}' to '{to_stage.value}'."
        )
