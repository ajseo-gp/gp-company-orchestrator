"""RED-first tests for the minimal local experiment registry.

The registry stores ONLY safe/redacted experiment metadata locally. It must
never persist sensitive payloads and never writes to any production system.
"""
from hermes_orchestrator.enums import Domain, Risk, Status
from hermes_orchestrator.graph import run_experiment
from hermes_orchestrator.models import ExperimentRequest
from hermes_orchestrator.registry import ExperimentRegistry


def _req(**kw):
    base = dict(
        experiment_id="EXP-R1",
        title="registry test",
        domain=Domain.BRAND,
        reversible=True,
        scope="small",
        declared_risk=Risk.LOW,
        topics=["brand-messaging-test"],
        sensitive_categories=[],
    )
    base.update(kw)
    return ExperimentRequest(**base)


def test_record_and_read_back(tmp_path):
    reg = ExperimentRegistry(tmp_path / "registry.json")
    run_experiment(_req(), registry=reg)
    rows = reg.all()
    assert len(rows) == 1
    row = rows[0]
    assert row["experiment_id"] == "EXP-R1"
    assert row["status"] == Status.APPROVED_FOR_EXPERIMENT.value
    assert row["domain"] == "BRAND"
    assert row["os_changed"] is False


def test_registry_persists_to_disk(tmp_path):
    path = tmp_path / "registry.json"
    reg = ExperimentRegistry(path)
    run_experiment(_req(), registry=reg)
    assert path.exists()
    # A fresh instance reads the same data.
    reg2 = ExperimentRegistry(path)
    assert len(reg2.all()) == 1


def test_registry_rejects_sensitive_keys(tmp_path):
    reg = ExperimentRegistry(tmp_path / "registry.json")
    run_experiment(_req(sensitive_categories=["customer_data"]), registry=reg)
    blob = (tmp_path / "registry.json").read_text()
    # Only the category FLAG may appear; never raw customer/recipe/cost payloads.
    for banned in ("recipe", "price", "email", "phone", "credential", "secret"):
        assert banned not in blob.lower()
