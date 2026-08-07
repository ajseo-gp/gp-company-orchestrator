"""RED-first tests for the enums and request/state models."""
from hermes_orchestrator.enums import Domain, Risk, Status


def test_domain_enum_exact_members():
    assert {d.value for d in Domain} == {
        "WORKBENCH", "BRAND", "CONTENT", "AUTOMATION",
        "MANUFACTURING", "OEM", "INFRA", "OS",
    }


def test_risk_enum_exact_members():
    assert {r.value for r in Risk} == {"LOW", "MEDIUM", "HIGH"}


def test_status_enum_exact_members_and_order():
    assert [s.value for s in Status] == [
        "PROPOSED", "CLASSIFIED", "APPROVED_FOR_EXPERIMENT", "IMPLEMENTING",
        "PREVIEW_READY", "CEO_REVIEW", "PROMOTED", "REJECTED", "CLOSED",
    ]


def test_risk_ordering_helper():
    assert Risk.LOW < Risk.MEDIUM < Risk.HIGH
    assert Risk.max_of(Risk.LOW, Risk.HIGH) is Risk.HIGH


def test_experiment_request_builds_initial_state():
    from hermes_orchestrator.models import ExperimentRequest, initial_state

    req = ExperimentRequest(
        experiment_id="EXP-0001",
        title="Test brand headline variant",
        domain=Domain.BRAND,
        declared_risk=Risk.LOW,
        reversible=True,
        scope="small",
        topics=["brand-messaging-test"],
        sensitive_categories=[],
    )
    state = initial_state(req)
    assert state["status"] == Status.PROPOSED
    assert state["request"]["experiment_id"] == "EXP-0001"
    # No production data may ever be stored on the request/state.
    assert "customer_data" not in state["request"]
