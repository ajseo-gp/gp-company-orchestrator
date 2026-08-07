---
name: hermes-orchestrator
description: Usage manual for running the GP Company Experiment Orchestrator (Hermes) V0.1 graph. NOT a policy source.
---

# Hermes Experiment Orchestrator — Usage Manual

> **This document is a USAGE MANUAL, not policy.**
> It is **NOT** the policy SSOT and **NOT** the OS SSOT.
> Policy is enforced by the **graph code + YAML** (`config/*.yaml` +
> `src/hermes_orchestrator/`). If anything here disagrees with the code/YAML or
> with `gp-company-os`, the code/YAML and the OS win. Do not encode routing,
> risk, or promotion rules in this file.

## What this is

An **experiment layer** over the **read-only** `gp-company-os` SSOT. It helps
route an experiment proposal through an enforced pipeline and, on verified
success, produce an **OS-change candidate** for a human/CEO to consider.

It never edits the OS, never publishes, and never touches production systems.

## The enforced graph

```
INTAKE → CLASSIFY → CHECK_OS → ROUTE → VERIFY → PROMOTE
```

Every experiment traverses all six nodes. Gated experiments pass through
`VERIFY`/`PROMOTE` as safe no-ops.

- **INTAKE** — accept a redacted proposal (safe metadata only).
- **CLASSIFY** — assign `Domain` and `Risk` (from `risk_matrix.yaml`).
- **CHECK_OS** — read-only alignment vs ACTIVE OS criteria
  (`os_active_index.yaml`): `ALIGNED` / `CONFLICT` / `NONE`.
- **ROUTE** — decide `EXPERIMENT` vs `CEO_OS_GATE` (`domain_router.yaml`).
- **VERIFY** — verify a dry-run outcome; on success → `PREVIEW_READY`.
- **PROMOTE** — mark an OS-change **candidate** (`promotion_rules.yaml`).
  `os_changed` is always `false`.

## How to run (dry-run only by default)

```bash
uv run hermes run \
  --id EXP-0001 --title "brand headline A/B" \
  --domain BRAND --risk LOW --reversible --scope small \
  --topics brand-messaging-test
```

Add `--outcome-success` to simulate a verified success (drives VERIFY/PROMOTE).
Add `--persist var/registry.json` to write a **local** redacted registry. There
is no non-dry-run mode: this tool never calls external systems.

Programmatic:

```python
from hermes_orchestrator.graph import run_experiment
from hermes_orchestrator.models import ExperimentRequest
from hermes_orchestrator.enums import Domain, Risk

state = run_experiment(ExperimentRequest(
    experiment_id="EXP-0001", title="…", domain=Domain.BRAND,
    reversible=True, scope="small", declared_risk=Risk.LOW,
    topics=["brand-messaging-test"],
))
print(state["status"], state["route"]["decision"])
```

## Hard prohibitions (operational boundaries)

- Do **not** write to `gp-company-os`, `gp-company-hub`, `gpcompany-lab`,
  production data, Slack, GitHub Issues, or any external system.
- Do **not** claim the OS changed. PROMOTE yields a **candidate** only.
- Do **not** copy real customer / recipe / cost / credential data. Only safe,
  redacted metadata and abstract topic flags may enter the registry.
- Do **not** merge or deploy from this layer.
- Treat `gp-company-os` as **read-only** at the pinned ref only.
