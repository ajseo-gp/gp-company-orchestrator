"""Request and graph-state models.

Only SAFE, redacted experiment metadata is ever represented here. There is no
field for customer / recipe / cost / credential data, by construction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, TypedDict

from .enums import Domain, Risk, Status

# Categories that force a CEO/OS gate (and a HIGH risk floor). These are flags,
# never the sensitive data itself.
SENSITIVE_CATEGORIES = frozenset(
    {
        "authorization",
        "automatic_publishing",
        "ad_claim_safety",
        "money_pricing",
        "customer_data",
        "production_state_transition",
        "agent_roles",
        "security",
        "external_permission_change",
    }
)

VALID_SCOPES = frozenset({"small", "large"})


@dataclass
class ExperimentRequest:
    """A single experiment proposal. Safe metadata only."""

    experiment_id: str
    title: str
    domain: Domain
    reversible: bool
    scope: str = "small"
    declared_risk: Optional[Risk] = None
    topics: list[str] = field(default_factory=list)
    sensitive_categories: list[str] = field(default_factory=list)
    # Optional dry-run outcome used by VERIFY. Redacted evidence string only.
    experiment_outcome: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.domain, Domain):
            self.domain = Domain(self.domain)
        if self.declared_risk is not None and not isinstance(self.declared_risk, Risk):
            self.declared_risk = Risk(self.declared_risk)
        if self.scope not in VALID_SCOPES:
            raise ValueError(f"scope must be one of {sorted(VALID_SCOPES)}: {self.scope!r}")
        unknown = set(self.sensitive_categories) - SENSITIVE_CATEGORIES
        if unknown:
            raise ValueError(f"unknown sensitive_categories: {sorted(unknown)}")

    def to_safe_dict(self) -> dict[str, Any]:
        """Serialize only the safe, redacted metadata."""
        return {
            "experiment_id": self.experiment_id,
            "title": self.title,
            "domain": self.domain.value,
            "reversible": bool(self.reversible),
            "scope": self.scope,
            "declared_risk": self.declared_risk.value if self.declared_risk else None,
            "topics": list(self.topics),
            "sensitive_categories": list(self.sensitive_categories),
            "experiment_outcome": _safe_outcome(self.experiment_outcome),
        }


def _safe_outcome(outcome: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not outcome:
        return None
    # Keep only whitelisted, non-sensitive keys.
    return {
        "success": bool(outcome.get("success", False)),
        "evidence": str(outcome.get("evidence", ""))[:280],
    }


class OrchestratorState(TypedDict, total=False):
    """LangGraph state. A plain dict at runtime."""

    request: dict[str, Any]
    status: Status
    domain: Domain
    risk: Optional[Risk]
    os_alignment: Optional[str]          # "ALIGNED" | "CONFLICT" | "NONE"
    os_criterion_id: Optional[str]
    route: dict[str, Any]
    gate: Optional[str]                  # "CEO_OS" when gated
    blocked: bool
    verified: Optional[bool]
    verification: dict[str, Any]
    promotion: dict[str, Any]
    history: list[dict[str, str]]
    notes: list[str]


def initial_state(request: ExperimentRequest) -> OrchestratorState:
    return {
        "request": request.to_safe_dict(),
        "status": Status.PROPOSED,
        "domain": request.domain,
        "risk": None,
        "os_alignment": None,
        "os_criterion_id": None,
        "route": {},
        "gate": None,
        "blocked": False,
        "verified": None,
        "verification": {},
        "promotion": {},
        "history": [{"status": Status.PROPOSED.value, "node": "INTAKE_INIT"}],
        "notes": [],
    }
