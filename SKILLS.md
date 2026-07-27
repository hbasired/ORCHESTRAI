# SKILLS.md — Role Persona Index

> Twelve role personas under `.claude/skills/<role>/SKILL.md`. CLAUDE.md §3 has the decision tree for picking one per task. This index is the quick lookup.

## Default

| Role | Purpose | Trigger | File |
|---|---|---|---|
| **agentic-governance-engineer** | Cross-cutting work; planning; governance; default if nothing else matches | Always-available default | [.claude/skills/agentic-governance-engineer/SKILL.md](.claude/skills/agentic-governance-engineer/SKILL.md) |

## Per-domain

| Role | Triggered by edits to… | File |
|---|---|---|
| **backend-engineer** | `backend/` (FastAPI, Alembic, services, agents — non-ML, non-crypto, non-safety, non-integrations) | [.claude/skills/backend-engineer/SKILL.md](.claude/skills/backend-engineer/SKILL.md) |
| **frontend-engineer** | `frontend-nextjs/` | [.claude/skills/frontend-engineer/SKILL.md](.claude/skills/frontend-engineer/SKILL.md) |
| **ml-engineer** | `backend/ml/`, `backend/training/`, weights, evals, model cards | [.claude/skills/ml-engineer/SKILL.md](.claude/skills/ml-engineer/SKILL.md) |
| **devops-sre** | `docker/`, `.github/`, observability, DR, infra | [.claude/skills/devops-sre/SKILL.md](.claude/skills/devops-sre/SKILL.md) |
| **security-pqc-engineer** | `backend/crypto/`, `backend/a2a/`, TLS, key rotation, signed bundles | [.claude/skills/security-pqc-engineer/SKILL.md](.claude/skills/security-pqc-engineer/SKILL.md) |
| **compliance-engineer** | `compliance/`, evidence pipeline, Annex IV pack, risk register | [.claude/skills/compliance-engineer/SKILL.md](.claude/skills/compliance-engineer/SKILL.md) |
| **robotics-integration-engineer** | `backend/integrations/` (VDA 5050, OPC UA, Sparkplug B, ROS 2), `backend/safety/` | [.claude/skills/robotics-integration-engineer/SKILL.md](.claude/skills/robotics-integration-engineer/SKILL.md) |
| **system-designer** | System design focus — HLD/LLD, component boundaries, interfaces, data/control flow, trade-offs (BEFORE implementation); owns `KB_24_System_Design_HLD_LLD.md` | [.claude/skills/system-designer/SKILL.md](.claude/skills/system-designer/SKILL.md) |
| **product-manager** | Market/product strategy — research, PRD stewardship (new-version files only), GTM/pricing/ICP, positioning + claim discipline, `research/*/index.html` viability artifacts; owns `KB_26_Product_Market_Strategy.md`. Never code. | [.claude/skills/product-manager/SKILL.md](.claude/skills/product-manager/SKILL.md) |

## Special

| Role | Triggered by… | File |
|---|---|---|
| **cto-reviewer** (read-only) | CTO checkpoint task doc (`STAGE_*_cto_checkpoint_*.md`); invoked via `scripts/cto-review.sh` | [.claude/skills/cto-reviewer/SKILL.md](.claude/skills/cto-reviewer/SKILL.md) |
| **task-auditor** (read-only) | Independent per-stage audit by a DIFFERENT agent than the implementer; invoked via `scripts/independent-audit.sh <stage>` | [.claude/skills/task-auditor/SKILL.md](.claude/skills/task-auditor/SKILL.md) |

The `cto-reviewer` persona is the only role allowed for CTO checkpoint stages (every 10 stages, whole-system). Its only write target is `audits/CTO_<N>_review.md`.

The `task-auditor` persona runs at **every** code-touching stage close (operator mandate, 2026-05-31): a fresh agent that did **not** build the stage independently re-runs its tests and reads its code adversarially, writing `audits/STAGE_<NN>_independent_review.md`. The builder must not audit their own work; a PASS verdict is required before `scripts/close-task.sh`. Both review personas are read-only — a follow-up implementer session fixes what they surface.
