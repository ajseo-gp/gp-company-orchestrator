"""Graph node implementations.

Each node takes the mutable orchestrator state dict and a Policy, applies the
policy, records status transitions, and returns the updated state. All policy
decisions come from `policy` (code + YAML) — never from skill text.
"""
from __future__ import annotations

from typing import Any

from .enums import Domain, Risk, Status
from .policy import Policy
from .transitions import transition

State = dict[str, Any]


def intake_node(state: State, policy: Policy) -> State:
    """Accept the proposal. Validate shape only; never mutate the OS."""
    req = state.get("request")
    if not req or not req.get("experiment_id"):
        raise ValueError("INTAKE requires a request with an experiment_id")
    if state["status"] != Status.PROPOSED:
        raise ValueError("INTAKE expects PROPOSED status")
    state.setdefault("notes", []).append(f"INTAKE accepted {req['experiment_id']}")
    state.setdefault("history", []).append({"status": state["status"].value, "node": "INTAKE"})
    return state


def classify_node(state: State, policy: Policy) -> State:
    req = state["request"]
    domain = Domain(req["domain"])
    declared = Risk(req["declared_risk"]) if req.get("declared_risk") else None
    sensitive = list(req.get("sensitive_categories", []))
    risk = policy.classify_risk(domain, declared, sensitive)
    state["domain"] = domain
    state["risk"] = risk
    state["notes"].append(f"CLASSIFY domain={domain.value} risk={risk.value}")
    transition(state, Status.CLASSIFIED, node="CLASSIFY")
    return state


def check_os_node(state: State, policy: Policy) -> State:
    """Read-only alignment check against the synthetic ACTIVE OS index."""
    domain = state["domain"]
    topics = list(state["request"].get("topics", []))
    alignment, crit_id = policy.check_os(domain, topics)
    state["os_alignment"] = alignment
    state["os_criterion_id"] = crit_id
    state["notes"].append(
        f"CHECK_OS alignment={alignment}" + (f" ({crit_id})" if crit_id else "")
    )
    # CHECK_OS never writes the OS and never advances status; record traversal.
    state["history"].append({"status": state["status"].value, "node": "CHECK_OS"})
    return state


def route_node(state: State, policy: Policy) -> State:
    domain: Domain = state["domain"]
    risk: Risk = state["risk"]
    req = state["request"]
    reversible = bool(req.get("reversible"))
    scope = req.get("scope", "small")
    sensitive = list(req.get("sensitive_categories", []))
    alignment = state["os_alignment"]

    decision, gate, lane, reason, blocked = _decide_route(
        policy, domain, risk, reversible, scope, sensitive, alignment
    )

    state["route"] = {
        "decision": decision,   # "EXPERIMENT" | "CEO_OS_GATE"
        "lane": lane,           # human-readable routing lane
        "reason": reason,
        "gate": gate,
    }
    state["gate"] = gate
    state["blocked"] = blocked
    state["notes"].append(f"ROUTE decision={decision} lane={lane} :: {reason}")

    if decision == "EXPERIMENT":
        transition(state, Status.APPROVED_FOR_EXPERIMENT, node="ROUTE")
    else:
        transition(state, Status.CEO_REVIEW, node="ROUTE")
    return state


def _decide_route(policy, domain, risk, reversible, scope, sensitive, alignment):
    """Pure routing decision. Precedence documented in domain_router.yaml."""
    # 1. ACTIVE OS conflict -> blocked CEO/OS gate.
    if alignment == "CONFLICT":
        return ("CEO_OS_GATE", "CEO_OS", "os_active_conflict",
                "conflicts with an ACTIVE OS criterion", True)

    # 2. OS domain -> always CEO/OS gate (candidate only, never executed here).
    if domain.value in policy.ceo_os_gate_domains():
        return ("CEO_OS_GATE", "CEO_OS", "os_domain",
                "OS-domain changes are candidate-only and require the CEO/OS gate", False)

    # 3. Sensitive category -> CEO/OS gate (no execution route).
    hit = sorted(set(sensitive) & policy.sensitive_gate_categories())
    if hit:
        return ("CEO_OS_GATE", "CEO_OS", "sensitive_category",
                f"sensitive categories require the CEO/OS gate: {hit}", False)

    # 4. ACTIVE-aligned -> can experiment.
    if alignment == "ALIGNED":
        return ("EXPERIMENT", None, "os_aligned",
                "aligned with an ACTIVE OS criterion", False)

    # 5. Fast route: BRAND/CONTENT + LOW + reversible + small scope.
    fr = policy.fast_route()
    if (
        domain.value in fr["domains"]
        and risk <= Risk(fr["max_risk"])
        and (reversible or not fr.get("require_reversible", True))
        and (scope == "small" or not fr.get("require_small_scope", True))
    ):
        return ("EXPERIMENT", None, "fast_route",
                "BRAND/CONTENT low-risk reversible small-scope fast lane", False)

    # 6. No ACTIVE criterion -> decide from risk + reversibility.
    rr = policy.risk_route()
    allow = rr.get("allow_if", {})
    if risk <= Risk(allow.get("max_risk", "MEDIUM")) and (
        reversible or not allow.get("require_reversible", True)
    ):
        return ("EXPERIMENT", None, "risk_route",
                "low/medium reversible risk permits experiment", False)

    return ("CEO_OS_GATE", "CEO_OS", "risk_route",
            "high or irreversible risk requires the CEO/OS gate", False)


def verify_node(state: State, policy: Policy) -> State:
    """Verify a dry-run experiment outcome. No effect on gated experiments."""
    if state["status"] != Status.APPROVED_FOR_EXPERIMENT:
        state["verified"] = False
        state["verification"] = {"ran": False, "reason": "not on an experiment route"}
        state["notes"].append("VERIFY skipped (gated / not approved)")
        return state

    outcome = state["request"].get("experiment_outcome")
    if not outcome:
        state["verified"] = None
        state["verification"] = {"ran": False, "reason": "no dry-run outcome provided"}
        state["notes"].append("VERIFY: nothing to verify yet")
        return state

    if outcome.get("success"):
        transition(state, Status.IMPLEMENTING, node="VERIFY")
        transition(state, Status.PREVIEW_READY, node="VERIFY")
        state["verified"] = True
        state["verification"] = {
            "ran": True,
            "success": True,
            "evidence": str(outcome.get("evidence", ""))[:280],
        }
        state["notes"].append("VERIFY: success, preview ready")
    else:
        transition(state, Status.CLOSED, node="VERIFY")
        state["verified"] = False
        state["verification"] = {"ran": True, "success": False}
        state["notes"].append("VERIFY: experiment did not succeed, closed")
    return state


def promote_node(state: State, policy: Policy) -> State:
    """Mark an OS-change CANDIDATE after verified success. NEVER writes the OS."""
    rules = policy.promotion_rules
    require_status = Status(rules.get("require_status", "PREVIEW_READY"))

    ok = (
        state["status"] == require_status
        and (state.get("verified") is True or not rules.get("require_verified", True))
    )

    if not ok:
        state["promotion"] = {
            "candidate": False,
            "os_changed": False,  # invariant: this layer NEVER changes the OS
            "reason": f"promotion requires verified success at {require_status.value}",
        }
        state["notes"].append("PROMOTE: no candidate created")
        return state

    candidate = {
        "candidate": True,
        "os_changed": False,  # HARD invariant — see promotion_rules.yaml
        "requires_ceo_os_action": True,
        "target_repo": rules.get("os_change_target_repo"),
        "os_ref": rules.get("os_ref"),
        "summary": f"Promotion candidate for {state['request']['experiment_id']}",
    }
    # Enforce the never-claim-OS-changed invariant defensively.
    assert candidate["os_changed"] is False, "PROMOTE must never claim OS changed"
    state["promotion"] = candidate
    transition(state, Status.PROMOTED, node="PROMOTE")
    state["notes"].append("PROMOTE: OS-change CANDIDATE marked (OS unchanged)")
    return state
