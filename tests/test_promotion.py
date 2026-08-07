"""RED-first tests for PROMOTE safety.

Invariants:
  - PROMOTE only marks a candidate after a VERIFIED success.
  - PROMOTE NEVER claims the OS changed (os_changed is always False).
  - Gated / unverified experiments are never promoted.
"""
from hermes_orchestrator.enums import Domain, Risk, Status
from hermes_orchestrator.graph import run_experiment
from hermes_orchestrator.models import ExperimentRequest


def _req(**kw):
    base = dict(
        experiment_id="EXP-P",
        title="promotion",
        domain=Domain.BRAND,
        reversible=True,
        scope="small",
        declared_risk=Risk.LOW,
        topics=[],
        sensitive_categories=[],
    )
    base.update(kw)
    return ExperimentRequest(**base)


def test_verified_success_marks_candidate_only():
    state = run_experiment(
        _req(experiment_outcome={"success": True, "evidence": "ctr +3% in dry-run sample"})
    )
    assert state["status"] == Status.PROMOTED
    assert state["promotion"]["candidate"] is True
    assert state["promotion"]["os_changed"] is False
    assert state["promotion"]["requires_ceo_os_action"] is True
    assert state["promotion"]["target_repo"] == "ajseo-gp/gp-company-os"


def test_promotion_never_claims_os_changed_across_all_paths():
    # Even a fully successful promotion must report os_changed False.
    for outcome in ({"success": True, "evidence": "ok"}, {"success": False}, None):
        state = run_experiment(_req(experiment_outcome=outcome))
        assert state["promotion"].get("os_changed", False) is False


def test_gated_experiment_is_never_promoted():
    state = run_experiment(
        _req(domain=Domain.OS, experiment_outcome={"success": True, "evidence": "x"})
    )
    assert state["status"] == Status.CEO_REVIEW
    assert state["promotion"]["candidate"] is False
    assert state["promotion"]["os_changed"] is False


def test_unverified_experiment_not_promoted():
    # Approved but no outcome to verify -> stays APPROVED_FOR_EXPERIMENT.
    state = run_experiment(_req(experiment_outcome=None))
    assert state["status"] == Status.APPROVED_FOR_EXPERIMENT
    assert state["promotion"]["candidate"] is False


def test_failed_experiment_is_closed_not_promoted():
    state = run_experiment(_req(experiment_outcome={"success": False}))
    assert state["status"] == Status.CLOSED
    assert state["verified"] is False
    assert state["promotion"]["candidate"] is False
