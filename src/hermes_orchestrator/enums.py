"""Enumerations for the experiment orchestrator.

These are the ONLY valid domains, risk levels, and statuses. The Status order
below is contractual and is asserted by the tests.
"""
from __future__ import annotations

from enum import Enum


class Domain(str, Enum):
    WORKBENCH = "WORKBENCH"
    BRAND = "BRAND"
    CONTENT = "CONTENT"
    AUTOMATION = "AUTOMATION"
    MANUFACTURING = "MANUFACTURING"
    OEM = "OEM"
    INFRA = "INFRA"
    OS = "OS"


class Risk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @property
    def _rank(self) -> int:
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[self.value]

    def __lt__(self, other: "Risk") -> bool:  # type: ignore[override]
        if not isinstance(other, Risk):
            return NotImplemented
        return self._rank < other._rank

    def __le__(self, other: "Risk") -> bool:  # type: ignore[override]
        if not isinstance(other, Risk):
            return NotImplemented
        return self._rank <= other._rank

    @classmethod
    def max_of(cls, *risks: "Risk") -> "Risk":
        return max(risks, key=lambda r: r._rank)


class Status(str, Enum):
    PROPOSED = "PROPOSED"
    CLASSIFIED = "CLASSIFIED"
    APPROVED_FOR_EXPERIMENT = "APPROVED_FOR_EXPERIMENT"
    IMPLEMENTING = "IMPLEMENTING"
    PREVIEW_READY = "PREVIEW_READY"
    CEO_REVIEW = "CEO_REVIEW"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"
