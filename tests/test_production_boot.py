from pathlib import Path

import yaml

from hermes_orchestrator.production import REQUIRED_BOOT_ITEMS, boot_gentlepapa_ep02, route_contract


def _complete_hub(root: Path) -> None:
    for refs in REQUIRED_BOOT_ITEMS.values():
        for ref in refs:
            path = root / ref
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("검증용 한국어 정본\n", encoding="utf-8")
    registry = {
        "workers": {
            "GP-CREATOR-01": {
                "roles": ["image_generation", "video_generation", "comfyui", "upscale", "modern_model", "i2v"],
                "health": "healthy", "availability": "available",
            },
            "GP-AI-WORKER-01": {
                "roles": ["whisper", "ffmpeg", "frame_extraction", "embedding", "media_analysis", "batch_processing"],
                "health": "healthy", "availability": "available",
            },
        }
    }
    path = root / "brands/gentlepapa/production/founder-story/WORKER-REGISTRY.yaml"
    path.write_text(yaml.safe_dump(registry, allow_unicode=True), encoding="utf-8")


def _contract(path: Path, task_type: str, hint: str) -> None:
    value = {
        "run_id": "EP02-S04-I2V-003", "episode": "EP02", "scene": "S04",
        "task_type": task_type,
        "input_refs": ["brands/gentlepapa/production/founder-story/EP02.md"],
        "approved_anchor": "evidence://EP01/approved/S04-anchor",
        "routing_hint": hint,
        "allowed_changes": ["4초 I2V 후보 2개 생성"],
        "forbidden_changes": ["캐릭터 변경", "다음 컷 진행"],
        "expected_outputs": ["candidate-01.mp4", "candidate-02.mp4", "run-result.yaml"],
        "stop_condition": "후보 2개와 증거 기록 후 즉시 중지",
        "requires_atlas_review": True,
    }
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_clean_session_blocks_when_any_requirement_is_missing(tmp_path):
    result = boot_gentlepapa_ep02(tmp_path)
    assert result["boot_status"] == "BLOCKED"
    assert result["production_enabled"] is False
    assert all(check["status"] == "FAIL" for check in result["checks"])


def test_ready_then_routes_creator_contract_to_atlas_review(tmp_path):
    _complete_hub(tmp_path)
    contract = tmp_path / "contract.yaml"
    _contract(contract, "video_generation", "GP-CREATOR-01")
    assert boot_gentlepapa_ep02(tmp_path)["boot_status"] == "READY"
    result = route_contract(contract, tmp_path)
    assert result["worker"] == "GP-CREATOR-01"
    assert result["dispatched"] is False
    assert result["next_state"] == "ATLAS_REVIEW_REQUIRED"


def test_ready_routes_media_processing_to_1080ti_worker(tmp_path):
    _complete_hub(tmp_path)
    contract = tmp_path / "contract.yaml"
    _contract(contract, "ffmpeg", "GP-AI-WORKER-01")
    result = route_contract(contract, tmp_path)
    assert result["worker"] == "GP-AI-WORKER-01"
    assert result["next_state"] == "ATLAS_REVIEW_REQUIRED"


def test_contract_cannot_bypass_failed_boot(tmp_path):
    contract = tmp_path / "contract.yaml"
    _contract(contract, "video_generation", "GP-CREATOR-01")
    result = route_contract(contract, tmp_path)
    assert result["status"] == "BLOCKED"
    assert result["worker"] is None
    assert result["dispatched"] is False

