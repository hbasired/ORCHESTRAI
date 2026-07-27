---
status: done
stage: 21.5
slug: cto_checkpoint_4
created: 2026-05-18
---

# Stage 21.5 — CTO Checkpoint #4

> After Stages 15–21 (OT/IT bridge, VDA 5050, functional safety wrapper, PQC Wave 2, governance evidence pipeline, red-team evals, DR/HA/chaos) — fourth CTO checkpoint. The system is now production-shaped; this checkpoint asks "could we run a pilot tomorrow?"

## Pre-requisites

- Stages 15, 16, 17, 18, 19, 20, 21 closed.

## Acceptance criteria

- [x] `audits/CTO_4_review.md` exists per template (DYNAMIC, fresh different-agent review), with explicit assessment of:
  - Functional safety coverage — trace-pairing invariant load-bearing; `sil_bridge` forgeable-by-default (G-075, not-yet-live) noted.
  - PQC posture — host-verified hybrid TLS + SLH-DSA; A2A live-mTLS binding still deploy-wiring (G-4); CI runs the shallow leg (Cross-cutting #3).
  - Annex IV completeness vs Article 11 — 14-section signed pack; conformity-assessment-READY ≠ certified.
  - Red-team pass rates — OWASP-LLM01 0.9935 hybrid / 0.758 heuristic CI / NIST 14/14 reproduced live; G-077 residuals noted.
  - DR drill outcomes — restore-verify row+audit_chain parity + chaos honest-degradation reproduced; G-078/G-079 fixed in-stage.
  - "Could a notified body audit us tomorrow?" — **NOT YET, but honest** (evidence machinery real + self-attesting; conformity = Stage 23 + notified body).
- [x] `audits/CTO_4_remediation_map.json` exists (12 remediations R1–R12).
- [x] Routed remediations: R10 → Stage 23 (`STAGE_23_conformity_dryrun.md`, appended); R1–R9/R11/R12 → Stage 22 (persist in the map; surfaced by `start-task.sh 22` — Stage 22 not yet seeded).
- [x] Verifies CTO #3 remediations honoured — **scorecard 10 honored / 1 not-yet-due / 0 skipped** (review §2).
- [x] **Bonus (G-1 immediate fix):** live audit_chain re-attested to green (`verify-audit-chain.py` exit 0; 417 rows, all 338 post-cutover sigs verify); durable test-isolation fix → Stage 22 (R1).

## Files / KB / role / audit target

Same shape as Stage 3.5 / 10.5 / 14.5.

## Hand-off

- CTO #4 remediations route to Stages 22 (pilot runbook), 23 (conformity dry-run), 24 (GA).
