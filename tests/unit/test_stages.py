"""Unit tests for every valid and invalid stage transition."""

import pytest

from app.errors import InvalidStageTransitionError
from app.models.enums import UserStage
from app.services.stages import STAGE_ORDER, assert_transition_allowed, next_stage


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        (UserStage.INVITED, UserStage.ACTIVATED),
        (UserStage.ACTIVATED, UserStage.FIRST_USE),
        (UserStage.FIRST_USE, UserStage.ACTIVE),
    ],
)
def test_valid_next_stage(current: UserStage, expected: UserStage) -> None:
    assert next_stage(current) == expected
    assert_transition_allowed(current, expected)


def test_cannot_advance_past_active() -> None:
    with pytest.raises(InvalidStageTransitionError):
        next_stage(UserStage.ACTIVE)


@pytest.mark.parametrize("current", list(STAGE_ORDER))
@pytest.mark.parametrize("target", list(STAGE_ORDER))
def test_invalid_transitions_rejected(current: UserStage, target: UserStage) -> None:
    expected_index = STAGE_ORDER.index(current) + 1
    is_valid = (
        expected_index < len(STAGE_ORDER) and STAGE_ORDER[expected_index] == target
    )
    if is_valid:
        assert_transition_allowed(current, target)
        return
    with pytest.raises(InvalidStageTransitionError):
        assert_transition_allowed(current, target)
