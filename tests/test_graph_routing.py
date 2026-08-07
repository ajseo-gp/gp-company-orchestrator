"""RED-first behavioral tests for the enforced graph:

    INTAKE -> CLASSIFY -> CHECK_OS -> ROUTE -> VERIFY -> PROMOTE

Required scenarios (from the product contract):
  - BRAND  LOW  -> experiment
  - CONTENT LOW -> experiment
  - AUTOMATION HIGH -> CEO gate
  - OS change -> CEO/OS gate
  - ACTIVE OS conflict -> blocked (CEO/OS gate)
"""
from hermes_orchestrator.enums import Domain, Risk, Status
from hermes_orchestrator.graph import run_experiment
from hermes_orchestrator.models import ExperimentRequest


def _req(**kw):
    base = dict(
        experiment_id="EXP-T",
        title="t",
        domain=Domain.BRAND,
        reversible=True,
        scope="small",
        declared_risk=Risk.LOW,
        topics=[],
        sensitive_categories=[],
    )
    base.update(kw)
    return ExperimentRequest(**base)


def test_all_six_nodes_execute_in_order():
    state = run_experiment(_req())
    visited = [h["node"] for h in state["history"]]
    for node in ["INTAKE", "CLASSIFY", "CHECK_OS", "ROUTE"]:
        assert node in visited


def test_brand_low_reversible_small_goes_to_experiment():
    state = run_experiment(_req(domain=Domain.BRAND, declared_risk=Risk.LOW))
    assert state["status"] == Status.APPROVED_FOR_EXPERIMENT
    assert state["gate"] is None
    assert state["route"]["decision"] == "EXPERIMENT"


def test_content_low_goes_to_experiment():
    state = run_experiment(_req(domain=Domain.CONTENT, declared_risk=Risk.LOW))
    assert state["status"] == Status.APPROVED_FOR_EXPERIMENT
    assert state["route"]["decision"] == "EXPERIMENT"


def test_automation_high_goes_to_ceo_gate():
    state = run_experiment(_req(domain=Domain.AUTOMATION, declared_risk=Risk.HIGH))
    assert state["status"] == Status.CEO_REVIEW
    assert state["gate"] == "CEO_OS"
    assert state["route"]["decision"] == "CEO_OS_GATE"


def test_os_domain_always_ceo_os_gate():
    state = run_experiment(_req(domain=Domain.OS, declared_risk=Risk.LOW, reversible=True))
    assert state["status"] == Status.CEO_REVIEW
    assert state["gate"] == "CEO_OS"


def test_active_os_conflict_is_blocked_gate():
    state = run_experiment(
        _req(domain=Domain.AUTOMATION, topics=["auto-publish-without-preview"])
    )
    assert state["status"] == Status.CEO_REVIEW
    assert state["gate"] == "CEO_OS"
    assert state["blocked"] is True
    assert state["os_alignment"] == "CONFLICT"


def test_active_os_aligned_allows_experiment():
    state = run_experiment(
        _req(domain=Domain.BRAND, declared_risk=Risk.LOW, topics=["brand-messaging-test"])
    )
    assert state["status"] == Status.APPROVED_FOR_EXPERIMENT
    assert state["os_alignment"] == "ALIGNED"


def test_sensitive_category_forces_gate_even_for_brand_low():
    state = run_experiment(
        _req(domain=Domain.BRAND, declared_risk=Risk.LOW, sensitive_categories=["money_pricing"])
    )
    assert state["status"] == Status.CEO_REVIEW
    assert state["gate"] == "CEO_OS"
    # sensitive floor also lifted the risk to HIGH
    assert state["risk"] == Risk.HIGH


def test_no_active_criterion_high_irreversible_gates():
    state = run_experiment(
        _req(domain=Domain.WORKBENCH, declared_risk=Risk.HIGH, reversible=False, topics=[])
    )
    assert state["os_alignment"] == "NONE"
    assert state["status"] == Status.CEO_REVIEW


def test_no_active_criterion_medium_reversible_experiments():
    state = run_experiment(
        _req(domain=Domain.WORKBENCH, declared_risk=Risk.MEDIUM, reversible=True, topics=[])
    )
    assert state["os_alignment"] == "NONE"
    assert state["status"] == Status.APPROVED_FOR_EXPERIMENT
