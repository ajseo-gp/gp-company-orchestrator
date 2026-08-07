"""RED-first tests for the status-transition guard."""
import pytest

from hermes_orchestrator.enums import Status
from hermes_orchestrator.transitions import (
    InvalidTransition,
    can_transition,
    transition,
)


def test_valid_forward_transition():
    state = {"status": Status.PROPOSED, "history": []}
    transition(state, Status.CLASSIFIED, node="CLASSIFY")
    assert state["status"] == Status.CLASSIFIED
    assert state["history"][-1] == {"status": "CLASSIFIED", "node": "CLASSIFY"}


def test_invalid_transition_raises():
    state = {"status": Status.PROPOSED, "history": []}
    with pytest.raises(InvalidTransition):
        transition(state, Status.PROMOTED, node="PROMOTE")


def test_terminal_status_cannot_advance_except_close():
    assert can_transition(Status.PROMOTED, Status.CLOSED)
    assert not can_transition(Status.PROMOTED, Status.IMPLEMENTING)
    assert not can_transition(Status.CLOSED, Status.PROMOTED)


def test_reject_reachable_from_classified():
    assert can_transition(Status.CLASSIFIED, Status.REJECTED)
    assert can_transition(Status.CLASSIFIED, Status.CEO_REVIEW)
    assert can_transition(Status.CLASSIFIED, Status.APPROVED_FOR_EXPERIMENT)
