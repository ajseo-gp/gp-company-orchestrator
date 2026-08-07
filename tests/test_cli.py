"""RED-first tests for the dry-run CLI smoke tool."""
import json

from hermes_orchestrator.cli import main


def test_cli_dry_run_brand_low_prints_experiment(capsys):
    rc = main([
        "run", "--id", "EXP-CLI-1", "--title", "cli brand test",
        "--domain", "BRAND", "--risk", "LOW", "--reversible", "--scope", "small",
        "--topics", "brand-messaging-test",
    ])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["dry_run"] is True
    assert out["status"] == "APPROVED_FOR_EXPERIMENT"
    assert out["promotion"]["os_changed"] is False


def test_cli_os_domain_gates(capsys):
    rc = main([
        "run", "--id", "EXP-CLI-2", "--title", "cli os test",
        "--domain", "OS", "--risk", "LOW", "--reversible",
    ])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "CEO_REVIEW"
    assert out["gate"] == "CEO_OS"


def test_cli_is_dry_run_by_default_no_registry(tmp_path, capsys):
    main([
        "run", "--id", "EXP-CLI-3", "--title", "no persist",
        "--domain", "CONTENT", "--risk", "LOW", "--reversible",
    ])
    # Default run must not create any registry file in cwd.
    assert not (tmp_path / "registry.json").exists()
    out = json.loads(capsys.readouterr().out)
    assert out["persisted"] is False


def test_cli_persist_writes_registry_when_asked(tmp_path, capsys):
    path = tmp_path / "reg.json"
    rc = main([
        "run", "--id", "EXP-CLI-4", "--title", "persist",
        "--domain", "BRAND", "--risk", "LOW", "--reversible",
        "--persist", str(path),
    ])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["persisted"] is True
    assert path.exists()
