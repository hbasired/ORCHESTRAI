# Pilot A/B / Proof-of-Value Protocol (Stage 32)

> How the pilot turns the sim-proven numbers (`capability-readiness-matrix.md`) into a defensible, published
> real-world A/B — the "we would have prevented X" counterfactual (PRD §prove). Research §43.2. Predefine EVERYTHING
> here with the customer BEFORE the baseline window (a metric chosen after seeing data is not evidence).
>
> **Honesty:** the design mirrors the paired-seed A/Bs this build already ran (Stage 6 slice, Stage 26 supply, Stage 30
> repair) — same statistics, now on real data. The real A/B is buyer-blocked (G-035/G-043).

## 1. Design principles (fixed before data)
- **Controlled comparison against the site's own baseline** — either (a) a pre/post design with a recorded baseline
  window, or (b) a concurrent control (matched lines/shifts/cells) where the plant allows. State which, and why.
- **Assignment unit:** the line / cell / shift (name it) — avoid contamination between arm A and arm B.
- **Primary metric + guardrails predefined** per capability (below). ONE primary per hypothesis; the rest are
  guardrails that must not regress.
- **Statistical test + CI predefined:** paired where the design allows (paired-diff + 95% t-CI, as in the sim A/Bs);
  otherwise a two-sample test with a pre-registered effect size + power. Report the CI, not just a point estimate.
- **Baseline window recorded BEFORE the agent influences anything** (shadow mode, Stage-28 autonomy ladder).

## 2. Per-capability A/B hypotheses (predefine the threshold with the customer)

| Hyp | Capability | Arm A (control) | Arm B (agent) | Primary metric | Guardrails | Sim precursor |
|---|---|---|---|---|---|---|
| H1 | Repair dispatch + self-healing | passive recovery / current practice | agent dispatch + self-healing loop | unplanned-downtime minutes / period | throughput, quality, energy | −47.9% (Stage 30); −201 min/8h (Stage 6/11) |
| H2 | Supply-chain coordination | current re-order policy | multi-agent Contract-Net | stockout-hours (or service level) | holding cost, order count | −51% stockouts, −98% bullwhip (Stage 26) |
| H3 | Predictive maintenance | run-to-failure / calendar PM | RUL-driven preventive maintenance | crack/unplanned breakdowns prevented | PM labour, false-alarm rate | 92% crack breakdowns prevented (Stage 6) |
| H4 | Operator adoption | pre-agent workflow | trust-calibrated UX + "ask the factory" | % recommendations reviewed / acted; operator usefulness rating | override rate, time-per-decision | UX shipped (Stage 28/29) |
| H5 | Detector efficacy | — (monitoring only) | learned injection tier + behavioural monitor | detection / FPR on the site's real inputs | legitimate-request block rate | 0.9935→1.0 / FPR→0 held-out (Stage 31) |

## 3. Hard gates (not hypotheses — must hold throughout)
- **G-safety:** 0 unsafe actuations — every `actuator.*` span preceded by a passing `safety.validate` (CI-enforced;
  audit_chain evidence). A single breach STOPS the pilot.
- **G-evidence:** the PQC-signed `audit_chain` verifies end-to-end throughout (`verify-audit-chain.py` exit 0).

## 4. Measurement mechanics (reuse the build's real machinery)
- **Downtime / throughput / quality / energy:** from the OT historian (Stage-15 OPC UA / Sparkplug ingest) + the
  ISA-95 graph — the same signals the sim A/Bs used, now real.
- **Counterfactual "prevented X":** the Stage-6/26/30 A/B harness pattern (`scripts/run_slice_ab.py`,
  `run_supply_ab.py`, `run_repair_ab.py`) is the template — port the arms to real data.
- **Adoption:** the Stage-28 adoption telemetry (recommendations reviewed/acted, trust calibration) + an operator
  survey.
- **Every decision + outcome is already logged** to the Art-12 signed `audit_chain` — the A/B reads from the same
  evidence a conformity assessor sees (no separate, un-auditable analytics path).

## 5. Reporting (the published A/B — G-043)
- Pre-registered protocol (this doc, filled) → results with CIs → an honest write-up: what met threshold, what didn't,
  guardrails, and the limitations (single site, N, confounders). A negative or null result is reported as-is (the
  same discipline as the sim A/Bs, where a losing arm is reported).
- The result graduates the pilot per the charter gates (`pilot-charter-template.md §5`).

## 6. What this protocol does NOT claim
- It is a TEMPLATE + the sim precursors — **no real A/B has been run** (no buyer/fleet yet; G-035/G-043). The sim
  numbers are the hypotheses' priors, not evidence of real-world effect.
- Real-data re-fit of each model (readiness matrix) is a prerequisite, not part of the A/B itself.

---
*Stage 32 · research §43.2 · pairs with `pilot-charter-template.md` + `capability-readiness-matrix.md`. Reuses the
Stage-6/26/30 A/B harnesses. Buyer-blocked: G-035 / G-043.*
