from pathlib import Path

import pytest
import yaml

from hermes_orchestrator.production import boot_founder_story, route_contract

SERIES_ROOT = Path("brands/gentlepapa/production/founder-story")


def _write(root: Path, relative: str, content: str = "검증용 한국어 정본\n") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _complete_hub(root: Path, phase: str = "PRODUCTION") -> None:
    for ref in (
        "brands/gentlepapa/AGENTS.md", "brands/gentlepapa/CONTENT-RULES.md",
        "brands/gentlepapa/WORLD-BIBLE.md", "brands/gentlepapa/BRAND-CANON.md",
        "brands/gentlepapa/DO-NOT-BREAK.md", "brands/gentlepapa/CHARACTER-BIBLE.md",
        "brands/gentlepapa/VISUAL-WORLD.md",
    ):
        _write(root, ref)
    for ref in ("SERIES-CANON.md", "ATLAS-EXECUTION-CONTRACT.md"):
        _write(root, str(SERIES_ROOT / ref))
    state = {
        "series": "founder-story", "active_episode": "EP03", "previous_episode": "EP02",
        "phase": phase, "episodes": {
            "EP02": {"phase": "COMPLETE", "previous_episode": "EP01"},
            "EP03": {"phase": phase, "previous_episode": "EP02"},
        },
    }
    _write(root, str(SERIES_ROOT / "SERIES-STATE.yaml"), yaml.safe_dump(state))
    registry = {"workers": {
        "GP-CREATOR-01": {"roles": ["video_generation"], "health": "healthy", "availability": "available"},
        "GP-AI-WORKER-01": {"roles": ["ffmpeg"], "health": "healthy", "availability": "available"},
    }}
    _write(root, str(SERIES_ROOT / "WORKER-REGISTRY.yaml"), yaml.safe_dump(registry))
    for ref in (
        "EP02/EP02.md", "EP02/APPROVED-EVIDENCE.md", "EP02/HANDOFF-TO-EP03.md",
        "EP03/EP03.md", "EP03/APPROVED-EVIDENCE.md", "EP03/CURRENT-HANDOFF.md",
        "EP03/REJECT-LOG.md", "EP03/contracts/README.md", "EP03/runs/README.md",
    ):
        _write(root, str(SERIES_ROOT / ref))


def _contract(path: Path, task_type: str, hint: str, episode: str = "EP03") -> None:
    value = {
        "run_id": f"{episode}-S01-TEST-001", "episode": episode, "scene": "S01",
        "task_type": task_type, "input_refs": [f"{episode}/{episode}.md"],
        "approved_anchor": "evidence://atlas/approved/anchor", "routing_hint": hint,
        "allowed_changes": ["후보 생성"], "forbidden_changes": ["정본 변경", "다음 장면 진행"],
        "expected_outputs": ["run-result.yaml"], "stop_condition": "결과 기록 후 즉시 중지",
        "requires_atlas_review": True,
    }
    path.write_text(yaml.safe_dump(value, allow_unicode=True), encoding="utf-8")


def test_missing_series_state_blocks_clean_session(tmp_path):
    result = boot_founder_story(tmp_path)
    assert result["boot_status"] == "BLOCKED"


def test_active_episode_is_detected_from_series_state(tmp_path):
    _complete_hub(tmp_path)
    result = boot_founder_story(tmp_path)
    assert result["boot_status"] == "READY"
    assert (result["episode"], result["previous_episode"]) == ("EP03", "EP02")


def test_explicit_episode_override_uses_registered_episode(tmp_path):
    _complete_hub(tmp_path, phase="PRE_PRODUCTION")
    result = boot_founder_story(tmp_path, "EP03")
    assert (result["episode"], result["phase"]) == ("EP03", "PRE_PRODUCTION")


def test_previous_handoff_template_does_not_pass_continuity(tmp_path):
    _complete_hub(tmp_path)
    _write(tmp_path, str(SERIES_ROOT / "EP02/HANDOFF-TO-EP03.md"), "상태: TEMPLATE\n")
    result = boot_founder_story(tmp_path)
    assert result["boot_status"] == "BLOCKED"
    assert any(c["item"] == "previous_episode_handoff" and c["status"] == "FAIL" for c in result["checks"])


def test_planning_does_not_require_active_episode_evidence(tmp_path):
    _complete_hub(tmp_path, phase="PLANNING")
    for name in ("EP03.md", "APPROVED-EVIDENCE.md", "CURRENT-HANDOFF.md", "REJECT-LOG.md"):
        (tmp_path / SERIES_ROOT / "EP03" / name).unlink()
    result = boot_founder_story(tmp_path)
    assert result["boot_status"] == "READY"
    assert result["generation_enabled"] is False


def test_preproduction_blocks_generation_even_when_boot_ready(tmp_path):
    _complete_hub(tmp_path, phase="PRE_PRODUCTION")
    contract = tmp_path / "contract.yaml"
    _contract(contract, "video_generation", "GP-CREATOR-01")
    result = route_contract(contract, tmp_path)
    assert result["reason"] == "GENERATION_NOT_ALLOWED_IN_CURRENT_PHASE"
    assert result["next_state"] == "ATLAS_REVIEW_REQUIRED"


def test_production_routes_workers_and_returns_to_atlas(tmp_path):
    _complete_hub(tmp_path)
    contract = tmp_path / "contract.yaml"
    _contract(contract, "video_generation", "GP-CREATOR-01")
    result = route_contract(contract, tmp_path, series="founder-story")
    assert (result["worker"], result["episode"]) == ("GP-CREATOR-01", "EP03")
    assert result["dispatched"] is False
    assert result["next_state"] == "ATLAS_REVIEW_REQUIRED"


def test_contract_episode_must_match_selected_episode(tmp_path):
    _complete_hub(tmp_path)
    contract = tmp_path / "contract.yaml"
    _contract(contract, "ffmpeg", "GP-AI-WORKER-01", episode="EP02")
    with pytest.raises(ValueError, match="계약 회차"):
        route_contract(contract, tmp_path)

