"""GentlePapa 제작 부팅 게이트와 읽기 전용 계약 라우터.

이 모듈은 생성 작업을 실행하지 않는다. Hub checkout을 읽어 정본·근거·현재 상태가
모두 준비됐는지 확인하고, Atlas가 승인한 작은 Execution Contract의 대상 Worker만
결정한다. 결과는 언제나 Atlas 검수 대기 상태로 끝난다.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


PRODUCTION_ROOT = Path("brands/gentlepapa/production/founder-story")

REQUIRED_BOOT_ITEMS = {
    "skill_production_rules": (
        "brands/gentlepapa/AGENTS.md",
        "brands/gentlepapa/CONTENT-RULES.md",
    ),
    "gentlepapa_world_brand_canon": (
        "brands/gentlepapa/WORLD-BIBLE.md",
        "brands/gentlepapa/BRAND-CANON.md",
        "brands/gentlepapa/DO-NOT-BREAK.md",
    ),
    "character_bible": ("brands/gentlepapa/CHARACTER-BIBLE.md",),
    "ep01_visual_canon": (
        "brands/gentlepapa/VISUAL-WORLD.md",
        str(PRODUCTION_ROOT / "EP01.md"),
    ),
    "ep01_approved_evidence": (str(PRODUCTION_ROOT / "EP01-APPROVED-EVIDENCE.md"),),
    "ep02_storyboard_story": (str(PRODUCTION_ROOT / "EP02.md"),),
    "current_handoff": (str(PRODUCTION_ROOT / "CURRENT-HANDOFF.md"),),
    "reject_log": (str(PRODUCTION_ROOT / "REJECT-LOG.md"),),
    "worker_registry": (str(PRODUCTION_ROOT / "WORKER-REGISTRY.yaml"),),
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


def _usable(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def boot_gentlepapa_ep02(hub_root: str | Path) -> dict[str, Any]:
    """검증 항목 하나라도 없으면 production_enabled=False로 닫힌 채 실패한다."""
    root = Path(hub_root).resolve()
    checks: list[BootCheck] = []
    for item, refs in REQUIRED_BOOT_ITEMS.items():
        missing = tuple(ref for ref in refs if not _usable(root / ref))
        checks.append(BootCheck(item, "PASS" if not missing else "FAIL", refs, missing))
    ready = all(check.status == "PASS" for check in checks)
    return {
        "project": "GentlePapa Founder Story EP02",
        "control_plane": "ATLAS_CHATGPT",
        "execution_plane": ["WORK", "CLAUDE", "ORCA", "HERMES", "GPU_WORKERS"],
        "boot_status": "READY" if ready else "BLOCKED",
        "production_enabled": ready,
        "checks": [asdict(check) for check in checks],
        "next_state": "ATLAS_READY" if ready else "BOOT_REQUIREMENTS_MISSING",
    }


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML 객체가 필요합니다: {path}")
    return value


def load_contract(path: str | Path) -> dict[str, Any]:
    contract = _load_yaml(Path(path))
    required = {
        "run_id", "episode", "scene", "task_type", "input_refs", "approved_anchor",
        "routing_hint", "allowed_changes", "forbidden_changes", "expected_outputs",
        "stop_condition", "requires_atlas_review",
    }
    missing = sorted(required - set(contract))
    if missing:
        raise ValueError(f"Execution Contract 필수 필드 누락: {missing}")
    if contract["episode"] != "EP02" or contract["requires_atlas_review"] is not True:
        raise ValueError("EP02 계약은 requires_atlas_review=true여야 합니다")
    if not contract["approved_anchor"]:
        raise ValueError("Atlas 승인 anchor/reference가 필요합니다")
    return contract


def route_contract(
    contract_path: str | Path,
    hub_root: str | Path,
) -> dict[str, Any]:
    """READY인 경우에만 Worker를 고르고, 실제 실행 없이 Atlas Review로 반환한다."""
    boot = boot_gentlepapa_ep02(hub_root)
    if not boot["production_enabled"]:
        return {
            "status": "BLOCKED",
            "reason": "SESSION_BOOT_GATE_NOT_READY",
            "worker": None,
            "dispatched": False,
            "next_state": "BOOT_REQUIREMENTS_MISSING",
        }

    contract = load_contract(contract_path)
    registry_path = Path(hub_root) / PRODUCTION_ROOT / "WORKER-REGISTRY.yaml"
    registry = _load_yaml(registry_path)
    workers = registry.get("workers", {})
    if not isinstance(workers, dict):
        raise ValueError("WORKER-REGISTRY.yaml의 workers는 객체여야 합니다")

    task_type = str(contract["task_type"])
    hint = contract.get("routing_hint")
    candidates = []
    for worker_id, worker in workers.items():
        if task_type not in set(worker.get("roles", [])):
            continue
        if worker.get("health") != "healthy" or worker.get("availability") != "available":
            continue
        candidates.append(worker_id)
    if hint in candidates:
        worker_id = hint
    elif candidates:
        worker_id = sorted(candidates)[0]
    else:
        return {
            "run_id": contract["run_id"],
            "status": "BLOCKED",
            "reason": "NO_HEALTHY_AVAILABLE_WORKER_FOR_ROLE",
            "worker": None,
            "dispatched": False,
            "next_state": "ATLAS_REVIEW_REQUIRED",
        }

    # 최소 연결은 dispatch 계획까지만 만든다. 생성·외부 호출은 수행하지 않는다.
    return {
        "run_id": contract["run_id"],
        "worker": worker_id,
        "task_type": task_type,
        "status": "ROUTED_DRY_RUN",
        "dispatched": False,
        "generation_task": task_type in GENERATION_TASKS,
        "input_refs": contract["input_refs"],
        "expected_outputs": contract["expected_outputs"],
        "errors": [],
        "warnings": ["실제 Worker 연결 전이므로 실행하지 않은 라우팅 검증입니다."],
        "next_state": "ATLAS_REVIEW_REQUIRED",
        "requires_atlas_review": True,
    }

