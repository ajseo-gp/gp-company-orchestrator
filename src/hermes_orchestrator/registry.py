"""Minimal persistent local registry for experiment metadata.

Stores ONLY safe, redacted metadata as a local JSON array. This is NOT a
production datastore: it never writes to gp-company-os, gp-company-hub,
gpcompany-lab, Slack, GitHub, or any external system. It records the outcome of
a graph run for local auditability.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .enums import Status

# The only fields ever persisted. Any other key is dropped by construction.
_SAFE_FIELDS = (
    "experiment_id",
    "title",
    "domain",
    "risk",
    "status",
    "os_alignment",
    "os_criterion_id",
    "route_decision",
    "route_lane",
    "gate",
    "blocked",
    "verified",
    "candidate",
    "os_changed",
    "sensitive_categories",
)


def _redact(state: dict[str, Any]) -> dict[str, Any]:
    req = state.get("request", {})
    route = state.get("route", {})
    promo = state.get("promotion", {})
    status = state.get("status")
    return {
        "experiment_id": req.get("experiment_id"),
        "title": str(req.get("title", ""))[:120],
        "domain": req.get("domain"),
        "risk": state["risk"].value if state.get("risk") else None,
        "status": status.value if isinstance(status, Status) else status,
        "os_alignment": state.get("os_alignment"),
        "os_criterion_id": state.get("os_criterion_id"),
        "route_decision": route.get("decision"),
        "route_lane": route.get("lane"),
        "gate": state.get("gate"),
        "blocked": bool(state.get("blocked", False)),
        "verified": state.get("verified"),
        "candidate": bool(promo.get("candidate", False)),
        # HARD invariant surfaced in the record: this layer never changes the OS.
        "os_changed": False,
        "sensitive_categories": list(req.get("sensitive_categories", [])),
    }


class ExperimentRegistry:
    def __init__(self, path: Path | str = "var/registry.json") -> None:
        self.path = Path(path)

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8")) or []
        except json.JSONDecodeError:
            return []

    def record(self, state: dict[str, Any]) -> dict[str, Any]:
        row = _redact(state)
        # Defensive: only ever keep whitelisted keys.
        row = {k: row[k] for k in _SAFE_FIELDS if k in row}
        assert row["os_changed"] is False, "registry must never record an OS change"
        rows = self._read()
        rows.append(row)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        return row

    def all(self) -> list[dict[str, Any]]:
        return self._read()
