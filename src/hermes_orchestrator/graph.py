"""LangGraph V0.1 graph wiring.

Enforced linear pipeline — every experiment traverses all six nodes:

    INTAKE -> CLASSIFY -> CHECK_OS -> ROUTE -> VERIFY -> PROMOTE

Gated experiments still pass through VERIFY and PROMOTE, where those nodes
become safe no-ops. No node performs network I/O and no node writes the OS.
"""
from __future__ import annotations

from typing import Any, Optional

from langgraph.graph import END, START, StateGraph

from . import nodes
from .models import ExperimentRequest, OrchestratorState, initial_state
from .policy import Policy, load_policy

NODE_ORDER = ["INTAKE", "CLASSIFY", "CHECK_OS", "ROUTE", "VERIFY", "PROMOTE"]


def build_graph(policy: Optional[Policy] = None):
    """Construct and compile the enforced LangGraph pipeline."""
    policy = policy or load_policy()

    def _wrap(fn):
        return lambda state: fn(state, policy)

    g = StateGraph(OrchestratorState)
    g.add_node("INTAKE", _wrap(nodes.intake_node))
    g.add_node("CLASSIFY", _wrap(nodes.classify_node))
    g.add_node("CHECK_OS", _wrap(nodes.check_os_node))
    g.add_node("ROUTE", _wrap(nodes.route_node))
    g.add_node("VERIFY", _wrap(nodes.verify_node))
    g.add_node("PROMOTE", _wrap(nodes.promote_node))

    g.add_edge(START, "INTAKE")
    g.add_edge("INTAKE", "CLASSIFY")
    g.add_edge("CLASSIFY", "CHECK_OS")
    g.add_edge("CHECK_OS", "ROUTE")
    g.add_edge("ROUTE", "VERIFY")
    g.add_edge("VERIFY", "PROMOTE")
    g.add_edge("PROMOTE", END)
    return g.compile()


def run_experiment(
    request: ExperimentRequest,
    *,
    policy: Optional[Policy] = None,
    registry: Any = None,
) -> OrchestratorState:
    """Run one experiment through the graph and return the final state.

    If `registry` is provided, a safe/redacted record is persisted after the
    run. Purely local; no production write, no external system.
    """
    policy = policy or load_policy()
    app = build_graph(policy)
    final = app.invoke(initial_state(request))
    if registry is not None:
        registry.record(final)
    return final
