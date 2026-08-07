"""Status-transition guard.

The status machine is enforced here so no node can jump the experiment to an
illegal status (e.g. straight to PROMOTED). Every transition is recorded in the
state history for auditability.
"""
from __future__ import annotations

from typing import Any

from .enums import Status

# Allowed forward transitions. Anything not listed is illegal.
ALLOWED_TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.PROPOSED: frozenset({Status.CLASSIFIED, Status.REJECTED}),
    Status.CLASSIFIED: frozenset(
        {Status.APPROVED_FOR_EXPERIMENT, Status.CEO_REVIEW, Status.REJECTED}
    ),
    Status.APPROVED_FOR_EXPERIMENT: frozenset(
        {Status.IMPLEMENTING, Status.CEO_REVIEW, Status.CLOSED}
    ),
    Status.IMPLEMENTING: frozenset({Status.PREVIEW_READY, Status.CLOSED}),
    Status.PREVIEW_READY: frozenset(
        {Status.CEO_REVIEW, Status.PROMOTED, Status.CLOSED}
    ),
    Status.CEO_REVIEW: frozenset(
        {Status.PROMOTED, Status.REJECTED, Status.CLOSED, Status.APPROVED_FOR_EXPERIMENT}
    ),
    Status.PROMOTED: frozenset({Status.CLOSED}),
    Status.REJECTED: frozenset({Status.CLOSED}),
    Status.CLOSED: frozenset(),
}


class InvalidTransition(Exception):
    """Raised when a status transition is not permitted."""


def can_transition(current: Status, new: Status) -> bool:
    return new in ALLOWED_TRANSITIONS.get(current, frozenset())


def transition(state: dict[str, Any], new: Status, *, node: str) -> None:
    current = state["status"]
    if current == new:
        return
    if not can_transition(current, new):
        raise InvalidTransition(f"{current.value} -> {new.value} is not permitted (node={node})")
    state["status"] = new
    state.setdefault("history", []).append({"status": new.value, "node": node})
