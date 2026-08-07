"""YAML-driven policy engine.

Policy enforcement is code + YAML ONLY. No skill text is consulted at runtime.
The pure functions here are called by the graph nodes; keeping them pure makes
the policy independently testable and auditable.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from .enums import Domain, Risk


def _default_config_dir() -> Path:
    env = os.environ.get("HERMES_CONFIG_DIR")
    if env:
        return Path(env)
    # src/hermes_orchestrator/policy.py -> repo_root/config
    repo_config = Path(__file__).resolve().parents[2] / "config"
    if repo_config.is_dir():
        return repo_config
    return Path.cwd() / "config"


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"policy file is not a mapping: {path}")
    return data


@dataclass
class Policy:
    risk_matrix: dict[str, Any]
    domain_router: dict[str, Any]
    promotion_rules: dict[str, Any]
    os_active_index: dict[str, Any]

    # ---- CLASSIFY -------------------------------------------------------
    def classify_risk(
        self,
        domain: Domain,
        declared_risk: Optional[Risk],
        sensitive_categories: list[str],
    ) -> Risk:
        default = Risk(self.risk_matrix["domain_defaults"].get(domain.value, self.risk_matrix["default_risk"]))
        risk = Risk.max_of(default, declared_risk) if declared_risk else default
        floors = self.risk_matrix.get("risk_floors", {})
        for cat in sensitive_categories:
            if cat in floors:
                risk = Risk.max_of(risk, Risk(floors[cat]))
        return risk

    # ---- CHECK_OS -------------------------------------------------------
    def check_os(self, domain: Domain, topics: list[str]) -> tuple[str, Optional[str]]:
        """Return (alignment, criterion_id).

        alignment is one of ALIGNED | CONFLICT | NONE. CONFLICT with any ACTIVE
        criterion takes precedence over ALIGNED.
        """
        topic_set = set(topics or [])
        aligned_hit: Optional[str] = None
        for crit in self.os_active_index.get("criteria", []):
            if crit.get("stance") != "ACTIVE":
                continue
            if topic_set & set(crit.get("conflict_topics", [])):
                return "CONFLICT", crit.get("id")
            if aligned_hit is None and topic_set & set(crit.get("aligned_topics", [])):
                aligned_hit = crit.get("id")
        if aligned_hit is not None:
            return "ALIGNED", aligned_hit
        return "NONE", None

    # ---- ROUTE helpers --------------------------------------------------
    def sensitive_gate_categories(self) -> frozenset[str]:
        return frozenset(self.domain_router["ceo_os_gate"].get("sensitive_categories", []))

    def ceo_os_gate_domains(self) -> frozenset[str]:
        return frozenset(self.domain_router["ceo_os_gate"].get("domains", []))

    def fast_route(self) -> dict[str, Any]:
        return self.domain_router["fast_route"]

    def risk_route(self) -> dict[str, Any]:
        return self.domain_router["risk_route"]


def load_policy(config_dir: Optional[Path | str] = None) -> Policy:
    base = Path(config_dir) if config_dir else _default_config_dir()
    return Policy(
        risk_matrix=_load_yaml(base / "risk_matrix.yaml"),
        domain_router=_load_yaml(base / "domain_router.yaml"),
        promotion_rules=_load_yaml(base / "promotion_rules.yaml"),
        os_active_index=_load_yaml(base / "os_active_index.yaml"),
    )
