"""Tiny dry-run CLI smoke tool.

Runs a single synthetic experiment through the graph and prints a redacted JSON
summary. Dry-run by DEFAULT: it never persists, never touches any external
system, and never writes the OS. Use --persist to write a LOCAL registry file.

Example:
    hermes run --id EXP-1 --title "brand headline A/B" \
        --domain BRAND --risk LOW --reversible --scope small \
        --topics brand-messaging-test
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional, Sequence

from .enums import Domain, Risk
from .graph import run_experiment
from .models import ExperimentRequest
from .registry import ExperimentRegistry


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hermes", description="GP Experiment Orchestrator (dry-run smoke)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run one synthetic experiment (dry-run by default)")
    r.add_argument("--id", required=True, dest="experiment_id")
    r.add_argument("--title", required=True)
    r.add_argument("--domain", required=True, choices=[d.value for d in Domain])
    r.add_argument("--risk", choices=[x.value for x in Risk], default=None)
    r.add_argument("--reversible", action="store_true")
    r.add_argument("--scope", choices=["small", "large"], default="small")
    r.add_argument("--topics", nargs="*", default=[])
    r.add_argument("--sensitive", nargs="*", default=[], help="sensitive category FLAGS only")
    r.add_argument("--outcome-success", action="store_true",
                   help="simulate a successful dry-run outcome for VERIFY/PROMOTE")
    r.add_argument("--persist", default=None, metavar="PATH",
                   help="write a LOCAL redacted registry file (off by default)")
    return p


def _summary(state: dict[str, Any], *, persisted: bool) -> dict[str, Any]:
    status = state["status"]
    return {
        "dry_run": True,
        "persisted": persisted,
        "experiment_id": state["request"]["experiment_id"],
        "domain": state["domain"].value,
        "risk": state["risk"].value if state.get("risk") else None,
        "status": status.value if hasattr(status, "value") else status,
        "os_alignment": state.get("os_alignment"),
        "gate": state.get("gate"),
        "blocked": state.get("blocked", False),
        "route": state.get("route", {}),
        "verified": state.get("verified"),
        "promotion": state.get("promotion", {}),
        "note": "EXPERIMENT LAYER — OS is read-only; PROMOTE yields a candidate only, os_changed=false.",
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    outcome = {"success": True, "evidence": "dry-run simulated success"} if args.outcome_success else None
    request = ExperimentRequest(
        experiment_id=args.experiment_id,
        title=args.title,
        domain=Domain(args.domain),
        reversible=bool(args.reversible),
        scope=args.scope,
        declared_risk=Risk(args.risk) if args.risk else None,
        topics=list(args.topics),
        sensitive_categories=list(args.sensitive),
        experiment_outcome=outcome,
    )

    registry = ExperimentRegistry(args.persist) if args.persist else None
    state = run_experiment(request, registry=registry)

    print(json.dumps(_summary(state, persisted=bool(args.persist)), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
