"""Founder Story 시리즈 부팅 게이트와 읽기 전용 계약 라우터."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

SERIES_ROOTS = {"founder-story": Path("brands/gentlepapa/production/founder-story")}
VALID_PHASES = frozenset({"PLANNING", "PRE_PRODUCTION", "PRODUCTION", "POST_PRODUCTION", "COMPLETE"})
EPISODE_PATTERN = re.compile(r"^EP\d{2,}$")
SERIES_REQUIREMENTS = {
    "skill_production_rules": ("brands/gentlepapa/AGENTS.md", "brands/gentlepapa/CONTENT-RULES.md"),
    "gentlepapa_world_brand_canon": (
        "brands/gentlepapa/WORLD-BIBLE.md", "brands/gentlepapa/BRAND-CANON.md",
        "brands/gentlepapa/DO-NOT-BREAK.md",
    ),
    "character_bible": ("brands/gentlepapa/CHARACTER-BIBLE.md",),
    "visual_world": ("brands/gentlepapa/VISUAL-WORLD.md",),
}
PHASE_REQUIREMENTS = {
    "PLANNING": (),
    "PRE_PRODUCTION": ("story", "current_handoff", "reject_log", "contracts", "runs"),
    "PRODUCTION": ("story", "approved_evidence", "current_handoff", "reject_log", "contracts", "runs"),
    "POST_PRODUCTION": ("story", "approved_evidence", "current_handoff", "reject_log", "contracts", "runs"),
    "COMPLETE": ("story", "approved_evidence"),
}
GENERATION_TASKS = frozenset(
    {"image_generation", "video_generation", "comfyui", "upscale", "modern_model", "i2v"}
)


@dataclass(frozen=True)
class BootCheck:
    item: str
    status: str
    refs: tuple[str, ...]
    missing: tuple[str, ...]


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML 객체가 필요합니다: {path}")
    return value


def _usable_file(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    head = path.read_text(encoding="utf-8", errors="replace")[:1000]
    return "상태: TEMPLATE" not in head and "status: TEMPLATE" not in head


def _check_all(root: Path, item: str, refs: tuple[str, ...]) -> BootCheck:
    missing = tuple(ref for ref in refs if not _usable_file(root / ref))
    return BootCheck(item, "PASS" if not missing else "FAIL", refs, missing)


def _check_any(root: Path, item: str, refs: tuple[str, ...], *, directory: bool = False) -> BootCheck:
    found = [ref for ref in refs if (root / ref).is_dir()] if directory else [ref for ref in refs if _usable_file(root / ref)]
    return BootCheck(item, "PASS" if found else "FAIL", refs, () if found else refs)


def _episode_refs(series_root: Path, episode: str, kind: str, *, next_episode: str | None = None) -> tuple[str, ...]:
    modern, legacy = series_root / episode, series_root
    mapping = {
        "story": (modern / f"{episode}.md", legacy / f"{episode}.md"),
        "approved_evidence": (modern / "APPROVED-EVIDENCE.md", legacy / f"{episode}-APPROVED-EVIDENCE.md"),
        "current_handoff": (modern / "CURRENT-HANDOFF.md", legacy / "CURRENT-HANDOFF.md"),
        "reject_log": (modern / "REJECT-LOG.md", legacy / "REJECT-LOG.md"),
        "contracts": (modern / "contracts", legacy / "contracts"),
        "runs": (modern / "runs", legacy / "runs"),
    }
    if kind == "handoff_to_next":
        if not next_episode:
            raise ValueError("handoff 대상 episode가 필요합니다")
        values = (modern / f"HANDOFF-TO-{next_episode}.md", legacy / f"{episode}-HANDOFF-TO-{next_episode}.md")
    else:
        values = mapping[kind]
    return tuple(str(path) for path in values)


def _resolve_series_state(root: Path, series: str, episode: str | None) -> tuple[Path, str, str | None, str]:
    if series not in SERIES_ROOTS:
        raise ValueError(f"지원하지 않는 series입니다: {series}")
    series_root = SERIES_ROOTS[series]
    state = _load_yaml(root / series_root / "SERIES-STATE.yaml")
    selected = episode or state.get("active_episode")
    if not isinstance(selected, str) or not EPISODE_PATTERN.fullmatch(selected):
        raise ValueError("SERIES-STATE.yaml 또는 --episode에 EPxx 형식의 회차가 필요합니다")
    episodes = state.get("episodes", {})
    episode_state = episodes.get(selected, {}) if isinstance(episodes, dict) else {}
    if episode and not episode_state and episode != state.get("active_episode"):
        raise ValueError(f"SERIES-STATE.yaml에 명시적 회차가 등록되지 않았습니다: {episode}")
    previous = episode_state.get("previous_episode", state.get("previous_episode"))
    phase = episode_state.get("phase", state.get("phase", state.get("status")))
    if phase not in VALID_PHASES:
        raise ValueError(f"지원하지 않는 production phase입니다: {phase}")
    return series_root, selected, previous, phase


def boot_founder_story(
    hub_root: str | Path, episode: str | None = None, *, series: str = "founder-story"
) -> dict[str, Any]:
    """Active Episode 또는 명시한 회차를 phase-aware 규칙으로 부팅한다."""
    root = Path(hub_root).resolve()
    try:
        series_root, selected, previous, phase = _resolve_series_state(root, series, episode)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        return {
            "series": series, "episode": episode, "boot_status": "BLOCKED",
            "production_enabled": False, "generation_enabled": False, "checks": [],
            "reason": str(exc), "next_state": "BOOT_REQUIREMENTS_MISSING",
        }

    checks = [_check_all(root, item, refs) for item, refs in SERIES_REQUIREMENTS.items()]
    checks.extend([
        _check_all(root, "series_canon", (str(series_root / "SERIES-CANON.md"),)),
        _check_all(root, "atlas_execution_contract", (str(series_root / "ATLAS-EXECUTION-CONTRACT.md"),)),
        _check_all(root, "worker_registry", (str(series_root / "WORKER-REGISTRY.yaml"),)),
        _check_all(root, "series_state", (str(series_root / "SERIES-STATE.yaml"),)),
    ])
    if previous:
        checks.extend([
            _check_any(root, "previous_episode_story", _episode_refs(series_root, previous, "story")),
            _check_any(root, "previous_episode_approved_evidence", _episode_refs(series_root, previous, "approved_evidence")),
            _check_any(root, "previous_episode_handoff", _episode_refs(series_root, previous, "handoff_to_next", next_episode=selected)),
        ])
    for kind in PHASE_REQUIREMENTS[phase]:
        checks.append(_check_any(
            root, f"active_episode_{kind}", _episode_refs(series_root, selected, kind),
            directory=kind in {"contracts", "runs"},
        ))

    ready = all(check.status == "PASS" for check in checks)
    generation_enabled = ready and phase in {"PRODUCTION", "POST_PRODUCTION"}
    return {
        "project": "GentlePapa Founder Story", "series": series, "episode": selected,
        "previous_episode": previous, "phase": phase, "control_plane": "ATLAS_CHATGPT",
        "execution_plane": ["WORK", "CLAUDE", "ORCA", "HERMES", "GPU_WORKERS"],
        "boot_status": "READY" if ready else "BLOCKED", "production_enabled": ready,
        "generation_enabled": generation_enabled, "checks": [asdict(check) for check in checks],
        "next_state": "ATLAS_READY" if ready else "BOOT_REQUIREMENTS_MISSING",
    }


def load_contract(path: str | Path, *, episode: str) -> dict[str, Any]:
    contract = _load_yaml(Path(path))
    required = {
        "run_id", "episode", "scene", "task_type", "input_refs", "approved_anchor",
        "routing_hint", "allowed_changes", "forbidden_changes", "expected_outputs",
        "stop_condition", "requires_atlas_review",
    }
    missing = sorted(required - set(contract))
    if missing:
        raise ValueError(f"Execution Contract 필수 필드 누락: {missing}")
    if contract["episode"] != episode:
        raise ValueError(f"선택한 회차({episode})와 계약 회차({contract['episode']})가 다릅니다")
    if contract["requires_atlas_review"] is not True:
        raise ValueError("모든 계약은 requires_atlas_review=true여야 합니다")
    if not contract["approved_anchor"]:
        raise ValueError("Atlas 승인 anchor/reference가 필요합니다")
    return contract


def route_contract(
    contract_path: str | Path, hub_root: str | Path, episode: str | None = None,
    *, series: str = "founder-story",
) -> dict[str, Any]:
    """READY인 회차의 계약만 Worker에 dry-run 라우팅한다."""
    boot = boot_founder_story(hub_root, episode, series=series)
    if not boot["production_enabled"]:
        return {
            "status": "BLOCKED", "reason": "SESSION_BOOT_GATE_NOT_READY", "series": series,
            "episode": boot.get("episode"), "worker": None, "dispatched": False,
            "next_state": "BOOT_REQUIREMENTS_MISSING",
        }
    contract = load_contract(contract_path, episode=boot["episode"])
    if contract["task_type"] in GENERATION_TASKS and not boot["generation_enabled"]:
        return {
            "run_id": contract["run_id"], "status": "BLOCKED",
            "reason": "GENERATION_NOT_ALLOWED_IN_CURRENT_PHASE", "worker": None,
            "dispatched": False, "next_state": "ATLAS_REVIEW_REQUIRED",
        }
    registry = _load_yaml(Path(hub_root) / SERIES_ROOTS[series] / "WORKER-REGISTRY.yaml")
    workers = registry.get("workers", {})
    if not isinstance(workers, dict):
        raise ValueError("WORKER-REGISTRY.yaml의 workers는 객체여야 합니다")
    task_type, hint = str(contract["task_type"]), contract.get("routing_hint")
    candidates = [
        worker_id for worker_id, worker in workers.items()
        if task_type in set(worker.get("roles", [])) and worker.get("health") == "healthy"
        and worker.get("availability") == "available"
    ]
    worker_id = hint if hint in candidates else (sorted(candidates)[0] if candidates else None)
    if not worker_id:
        return {
            "run_id": contract["run_id"], "status": "BLOCKED",
            "reason": "NO_HEALTHY_AVAILABLE_WORKER_FOR_ROLE", "worker": None,
            "dispatched": False, "next_state": "ATLAS_REVIEW_REQUIRED",
        }
    return {
        "run_id": contract["run_id"], "series": series, "episode": boot["episode"],
        "worker": worker_id, "task_type": task_type, "status": "ROUTED_DRY_RUN",
        "dispatched": False, "generation_task": task_type in GENERATION_TASKS,
        "input_refs": contract["input_refs"], "expected_outputs": contract["expected_outputs"],
        "errors": [], "warnings": ["실제 Worker 연결 전이므로 실행하지 않은 라우팅 검증입니다."],
        "next_state": "ATLAS_REVIEW_REQUIRED", "requires_atlas_review": True,
    }

