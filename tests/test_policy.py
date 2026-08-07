"""RED-first tests for the YAML-driven policy engine.

Policy enforcement MUST come from graph + YAML, never from skill text. These
tests pin the pure-function policy behavior the nodes rely on.
"""
from hermes_orchestrator.enums import Domain, Risk
from hermes_orchestrator.policy import load_policy


def test_policy_loads_all_yaml_files():
    p = load_policy()
    assert p.risk_matrix["version"]
    assert p.domain_router["version"]
    assert p.promotion_rules["version"]
    assert p.os_active_index["os_ref"] == "60bcdb2ec8ee88287e3664bf0b1b31a287fa246d"


def test_classify_risk_uses_domain_default():
    p = load_policy()
    assert p.classify_risk(Domain.BRAND, None, []) is Risk.LOW
    assert p.classify_risk(Domain.MANUFACTURING, None, []) is Risk.HIGH


def test_classify_risk_respects_declared_when_higher():
    p = load_policy()
    assert p.classify_risk(Domain.BRAND, Risk.HIGH, []) is Risk.HIGH


def test_classify_risk_sensitive_category_forces_high_floor():
    p = load_policy()
    # BRAND default is LOW, but customer_data forces HIGH.
    assert p.classify_risk(Domain.BRAND, Risk.LOW, ["customer_data"]) is Risk.HIGH


def test_check_os_aligned_conflict_none():
    p = load_policy()
    assert p.check_os(Domain.BRAND, ["brand-messaging-test"])[0] == "ALIGNED"
    assert p.check_os(Domain.AUTOMATION, ["auto-publish-without-preview"])[0] == "CONFLICT"
    assert p.check_os(Domain.BRAND, ["totally-unknown-topic"])[0] == "NONE"


def test_check_os_conflict_takes_precedence_over_aligned():
    p = load_policy()
    alignment, _ = p.check_os(Domain.BRAND, ["brand-messaging-test", "halt-growth-program"])
    assert alignment == "CONFLICT"
