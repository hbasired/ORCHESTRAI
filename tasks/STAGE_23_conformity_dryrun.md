---
status: done
stage: 23
slug: conformity_dryrun
created: 2026-05-18
---

# Stage 23 — Conformity Assessment Dry-Run

> Internal rehearsal of an external notified-body / TÜV conformity assessment. Generate the full Annex IV pack; produce ISO 10218 risk assessment document; collate ISO/IEC 42001 internal audit evidence. Hands the bundle to a sympathetic external reviewer (not the real notified body yet) for a dry-run.

## Pre-requisites

- Stages 19 (Annex IV generator), 20 (red-team evals), 21 (DR/HA), 22 (pilot runbook) closed.

## Acceptance criteria

- [ ] (CTO remediation) Conformity dry run: run the Annex IV pack + risk register + safety case through a mock notified-body assessment; close the KB_18 governance wishlist (Policy DSL / Bell-LaPadula MAC / PII filter / ISO 42005 — G-028/G-029/G-030) that the Annex IV stage scoped out; obtain/define the SIL-certification + certified-PLC integration path — G-011.

- [ ] `compliance/annex-iv-packs/<YYYY-MM-DD>_dry_run.pdf` generated via `scripts/generate-annex-iv-doc.py`.
- [ ] `compliance/iso-10218-risk-assessment.md` authored per ISO 10218-2:2025 §6 requirements.
- [ ] `compliance/iso-42001-internal-audit/2026-Q4_audit.md` authored covering all ISO/IEC 42001 controls.
- [ ] External reviewer engaged; their feedback captured in `audits/STAGE_23_external_review.md`.
- [ ] Gaps from external review routed as Stage 24 remediations.
- [ ] `compliance/decision-logs/<date>_stage_23_dry_run_outcome.md` ADR.

## Files to CREATE

| Path | Purpose |
|---|---|
| `compliance/iso-10218-risk-assessment.md` | ISO 10218-2:2025 §6 risk assessment |
| `compliance/iso-42001-internal-audit/2026-Q4_audit.md` | ISO/IEC 42001 internal audit |
| `audits/STAGE_23_external_review.md` | External reviewer feedback |

## Files to MODIFY

| Path | Change |
|---|---|
| `compliance/risk-register.md` | Any new risks surfaced by dry-run |
| `knowledge-base/KB_18_Governance_Evidence.md` | Status of each control after dry-run |

## KB files this stage updates

- `KB_18_Governance_Evidence.md`
- `KB_17_Functional_Safety_Wrapper.md`
- `KB_TASK_LOG.md`

## Audit target

- Non-reducing. Close with `--no-baseline-drop "conformity dry-run; doc-only"`.

## Role

- Primary: `compliance-engineer`
- Secondary: `agentic-governance-engineer` (overall coordination), `robotics-integration-engineer` (ISO 10218 specifics)

## Hand-off

- What is now true: the system has been rehearsed for external conformity assessment; gaps surfaced before the real one.
- Next stage (24) is GA release; Stage 24.5 is CTO #5 final audit.
