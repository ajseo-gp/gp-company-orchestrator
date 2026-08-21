# GP Company Experiment Orchestrator (Hermes) — V0.1

An **experiment layer** built on **LangGraph** that routes experiment proposals
through an enforced pipeline and, on verified success, emits an **OS-change
candidate** for a human/CEO to consider.

This repository is **NOT** a policy source and **NOT** the OS. The
[`gp-company-os`](https://github.com/ajseo-gp/gp-company-os) repository remains
the single source of truth (SSOT) and is treated as **read-only**.

- **OS ref (pinned, read-only):** `60bcdb2ec8ee88287e3664bf0b1b31a287fa246d`
  (`ajseo-gp/gp-company-os`)
- **Python:** 3.11 · **Package/deps:** `uv` · **Runtime deps:** `langgraph`,
  `pyyaml` (standard library otherwise). **No network runtime behavior.**

## Architecture

```
                       config/*.yaml  (POLICY DATA)
                       ├── risk_matrix.yaml        → CLASSIFY
                       ├── domain_router.yaml      → ROUTE
                       ├── promotion_rules.yaml    → PROMOTE
                       └── os_active_index.yaml    → CHECK_OS  (synthetic/redacted)
                                   │
   ExperimentRequest ──▶ LangGraph enforced pipeline ──▶ final state ──▶ (local) registry
                                   │
        INTAKE → CLASSIFY → CHECK_OS → ROUTE → VERIFY → PROMOTE
```

Policy is enforced by **graph code + YAML** (`src/hermes_orchestrator/policy.py`
and `nodes.py` reading `config/*.yaml`) — **never** by skill text. The
`skills/hermes-orchestrator/SKILL.md` file is a usage manual only.

### Flow (the six enforced nodes)

Every experiment traverses all six nodes; gated experiments pass through
`VERIFY`/`PROMOTE` as safe no-ops.

| Node | Responsibility | Source of truth |
|------|----------------|-----------------|
| **INTAKE** | Accept redacted proposal (safe metadata only) | — |
| **CLASSIFY** | Assign `Domain`, compute `Risk` (max of default/declared/sensitive floor) | `risk_matrix.yaml` |
| **CHECK_OS** | Read-only alignment: `ALIGNED` / `CONFLICT` / `NONE` | `os_active_index.yaml` |
| **ROUTE** | `EXPERIMENT` vs `CEO_OS_GATE` | `domain_router.yaml` |
| **VERIFY** | Verify dry-run outcome → `PREVIEW_READY` on success | — |
| **PROMOTE** | Mark an OS-change **candidate** (`os_changed=false`) | `promotion_rules.yaml` |

### Routing precedence (ROUTE)

1. `CHECK_OS` **ACTIVE conflict** → **blocked** CEO/OS gate
2. **OS domain** → CEO/OS gate (candidate-only, never executed here)
3. **Sensitive category** → CEO/OS gate (no execution route)
4. `CHECK_OS` **ACTIVE aligned** → experiment allowed
5. **Fast route**: `BRAND`/`CONTENT` + `LOW` + reversible + small scope → `APPROVED_FOR_EXPERIMENT`
6. **No ACTIVE criterion** → decide from **risk + reversibility** (LOW/MEDIUM & reversible → experiment; else gate)

Sensitive categories forcing the CEO/OS gate: authorization, automatic
publishing, ad-claim safety, money/pricing, customer data, production state
transition, agent roles, security, external permission change.

### Enums

- **Domain:** `WORKBENCH, BRAND, CONTENT, AUTOMATION, MANUFACTURING, OEM, INFRA, OS`
- **Risk:** `LOW, MEDIUM, HIGH`
- **Status:** `PROPOSED, CLASSIFIED, APPROVED_FOR_EXPERIMENT, IMPLEMENTING, PREVIEW_READY, CEO_REVIEW, PROMOTED, REJECTED, CLOSED`

## Startup / test commands

```bash
uv sync --extra dev          # install (langgraph, pyyaml, pytest)
uv pip install -e .          # editable install of the package
uv run pytest -q             # run the test suite

# Dry-run smoke (default: no persistence, no external side effects)
uv run hermes run --id EXP-0001 --title "brand headline A/B" \
    --domain BRAND --risk LOW --reversible --scope small \
    --topics brand-messaging-test

# GentlePapa 제작 부팅은 로컬 Hub checkout을 읽기 전용으로 검증한다.
uv run hermes production boot --hub-root ../gp-company-hub

# READY 뒤 Atlas가 승인한 작은 계약 1개만 dry-run 라우팅한다.
uv run hermes production route --hub-root ../gp-company-hub \
    --contract ../gp-company-hub/brands/gentlepapa/production/founder-story/contracts/EP02-S04-I2V-003.yaml
```

`production` 명령은 생성·외부 dispatch·Hub 쓰기를 수행하지 않는다. 필수 정본이나 근거가
하나라도 없으면 종료 코드 2와 `BLOCKED`를 반환하며, 라우팅 결과의 다음 상태는 항상
`ATLAS_REVIEW_REQUIRED`다.

## Operational boundaries

- `gp-company-os` is **read-only** and only at the pinned ref above.
- The local registry (`registry.py`) stores **only safe/redacted metadata**
  locally (JSON). It is not a production datastore.
- **PROMOTE** produces an OS-change **candidate** only — a pointer for a
  human/CEO to act on in the OS repo. It records `os_changed=false`.

## Hard prohibitions

- **Do NOT** modify/write `gp-company-os`, `gp-company-hub`, `gpcompany-lab`,
  production data, Slack, GitHub Issues, or any external system.
- **Do NOT** claim the OS changed. This layer never edits the OS.
- **Do NOT** copy real customer / recipe / cost / credential data.
- **Do NOT** merge or deploy from this layer.
- **No network runtime behavior.**

