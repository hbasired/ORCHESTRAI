# Pilot Charter Template (Stage 32)

> The spine of a disciplined pilot. Research §43.1: ~60% of AI pilots never reach production, the most common reason
> being **no predefined success criteria**. This charter fixes scope, success criteria + thresholds, decision gates,
> and a hard deadline BEFORE the pilot starts — agreed by both technical and business leaders. Copy per engagement.
>
> **Honesty note.** Every "sim-proven" number below is from THIS project's SimWorld / benchmark studies (cited), NOT a
> real deployment — the pilot's job is to convert them to real-world evidence. The real pilot + published A/B remain
> honestly deferred (G-035/G-043, buyer-blocked). See `capability-readiness-matrix.md`.

## 1. Scope & intended purpose

- **Site / customer:** ____
- **Intended purpose (EU-AI-Act Annex-IV term):** ____ (e.g. "decision-support for predictive maintenance +
  supply-chain coordination on a multi-vendor AMR + CNC line; human-on-the-loop; no autonomous SIL-rated actuation in
  the pilot").
- **In-scope capabilities (pick from the readiness matrix):** ____
- **Out of scope (explicit):** autonomous actuation beyond the agreed autonomy level; any capability marked
  "real-data-blocked" in the readiness matrix until its data-intake is satisfied.
- **Autonomy level for the pilot (Stage-28 ladder):** default **shadow** → promote per §5 gates. Never starts above
  shadow.

## 2. Predefined success criteria + thresholds (the graduation bar)

Graduation gates centre on **business impact**, not technical metrics (research §43.1). Fill the threshold column
with the customer BEFORE go-live. The "sim precursor" is the number this build measured — the pilot tests whether it
holds on real data.

| # | Metric (primary) | Sim precursor (this build) | Pilot threshold (agree w/ customer) | Measurement |
|---|---|---|---|---|
| S1 | Unplanned-downtime reduction (repair dispatch + self-healing) | repair A/B −47.9% (CI [7696,12733]s, Stage 30); slice A/B −201 min/8h (Stage 6/11) | e.g. ≥ 15% vs baseline | A/B §pilot-ab-protocol |
| S2 | Stockout / service-level improvement (supply chain) | −51% stockouts, −98% bullwhip (Stage 26 A/B) | e.g. ≥ 20% stockout reduction | A/B |
| S3 | Operator adoption / trust (calibrated-trust UX) | trust-calibration UX shipped (Stage 28) | e.g. ≥ 60% of recommendations reviewed; NPS ≥ threshold | adoption telemetry + survey |
| S4 | Grounded-answer usefulness ("ask the factory") | grounded/honest-empty/citation-precision 1.0 on SOP corpus (Stage 28/29) | e.g. ≥ 80% answers rated useful + correctly-cited by operators | labelled operator review |
| S5 | Safety: zero unsafe actuations | 100% actuator paths validator-gated + trace-paired (CI-enforced) | **hard gate: 0 unsafe actuations** | audit_chain + safety spans |
| S6 | Evidence integrity | audit chain verifies (10k+ rows, exit 0) | **hard gate: chain verifies throughout** | `verify-audit-chain.py` |

**Guardrail metrics (must not regress):** throughput, cycle time, quality/defect rate, energy — the pilot must not
buy S1/S2 by hurting these.

## 3. Data-production-readiness gate (pre-pilot)

The pilot cannot start until the data-intake spec (`pilot-onboarding-kit.md §2` + this stage's addendum) is met for
each in-scope capability — a real-data dependency the readiness matrix names per capability (G-035). A "No-Go" here is
terminal for that capability until resolved.

## 4. Timeline

- **Baseline window:** ____ (record the site's pre-agent baseline before the agent influences anything).
- **Value-demonstration window:** 4–6 weeks (8-week ceiling); AI-agent PoC 8–12 weeks (Gartner) — long enough to see
  real process behaviour, short enough to prevent scope creep.
- **Decision date (hard deadline):** ____.

## 5. Decision gates (Scale / Iterate / Pivot / Stop)

Evaluated at the decision date against §2 (research §43.1):

- **SCALE (→ production):** all primary success criteria meet threshold AND both hard gates (S5, S6) hold AND no
  guardrail regressed.
- **ITERATE (targeted redesign, re-decide):** a No-Go in **adoption / integration / ROI** only — fix and revisit.
- **PIVOT:** the value is real but in a different use-case than scoped — re-charter.
- **STOP:** a No-Go in **technical performance, business value, OR data-production-readiness** — a single such signal
  terminates the production commitment (do not sink further cost).

## 6. Roles & oversight (EU-AI-Act Art-26 deployer obligations)

- **Human overseers named + trained** (pilot-deployment-runbook §3); authority to override/stop.
- **Business owner** (owns the success criteria) + **technical owner** (owns integration + evidence).
- **Incident escalation** path + the post-market monitoring plan (`post-market-monitoring-plan.md`) active.

## 7. Sign-off

Technical lead: ______   Business lead: ______   Date: ______  (both signatures REQUIRED before go-live.)

---
*Stage 32 · research §43.1 · pairs with `pilot-ab-protocol.md` + `capability-readiness-matrix.md` +
`pilot-onboarding-kit.md` + `pilot-deployment-runbook.md`. The real pilot is buyer-blocked (G-035/G-043).*
