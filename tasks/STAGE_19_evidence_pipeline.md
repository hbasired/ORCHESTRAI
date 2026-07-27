---
status: done
stage: 19
slug: evidence_pipeline
created: 2026-05-18
---

# Stage 19 — Governance Evidence Pipeline (Annex IV Doc-Pack Generator)

> ISO/IEC 42001 control mapping + EU AI Act Annex IV technical-documentation pack auto-generator. Pulls from risk register + model cards + audit_chain summary + decision logs + Phoenix eval results + standards map + KB_13 PQC posture + human-oversight + incident playbook into a single conformity-assessment-ready bundle.

## Pre-requisites

- Stages 13.5, 14, 15, 16, 17, 18 closed (all governance evidence sources operational).

## Acceptance criteria

- [ ] (CTO remediation) Add DB-level tenant isolation (Postgres RLS) on mem0_memories as defense-in-depth behind the adapter's Python _authorize (a direct SQL client currently bypasses namespace isolation; adequate today with one in-process reader, but RLS is needed once multi-tenant)

- [ ] (CTO remediation) Close the regulator-grade evidence gaps for EU AI Act Art-12: back-sign (or formally document the cutover for) the 79 legacy placeholder-sha256 audit_chain rows, and build the live message-cascade/latency observability surface (G-021)

- [ ] (CTO remediation) Instrument the uninstrumented OTel layers: add a2a.rpc.<method> spans + an audit_chain row per A2A capability call (G-074, the external trust boundary is currently trace- and audit-blind); add per-model ml.inference.* spans for the world-model/diagnose/explain/decide nodes (only failure_predictor is wrapped today); add a CDC ingestion span

- [ ] (CTO remediation) Make scripts/verify-audit-chain.py signature verification load-bearing: fail (exit 1) on any non-placeholder audit_chain row whose ML-DSA-65 signature does not verify, and report the placeholder->ML-DSA-65 cutover seq explicitly so 'Audit chain OK' is not read as 'all rows post-quantum-signed' (G-073)

- [ ] `scripts/generate-annex-iv-doc.py` produces a complete PDF (and HTML bundle) covering all 14 sections enumerated in KB_18 §"Annex IV technical-documentation pack generator".
- [ ] Output bundles into `compliance/annex-iv-packs/<YYYY-MM-DD>_annex_iv.pdf` (latest also at `compliance/annex-iv-packs/latest.pdf`).
- [ ] Pack includes ML-DSA-65 signed conformity-declaration footer.
- [ ] `audits/STAGE_19_audit.md` includes the pack as evidence.
- [ ] `compliance/ai-policy.md` authored (ISO/IEC 42001 A.6.1 requirement).
- [ ] ISO/IEC 42001 control table in KB_18 marked `shipped` for every control with evidence.
- [ ] CI gate `annex-iv-pack-builds` runs the generator on every PR; fails on incomplete output.

## Files to CREATE

| Path | Purpose |
|---|---|
| `scripts/generate-annex-iv-doc.py` | The generator |
| `compliance/ai-policy.md` | ISO/IEC 42001 A.6.1 AI policy |
| `compliance/annex-iv-packs/` | Output directory (gitignored except .gitkeep) |
| `compliance/annex-iv-packs/template.html` | HTML template for the bundle |
| `backend/tests/compliance/test_annex_iv_generator.py` | Generator coverage tests |

## Files to MODIFY

| Path | Change |
|---|---|
| `knowledge-base/KB_18_Governance_Evidence.md` | Control mapping table marked `shipped` per control |
| `.github/workflows/ci.yml` | Add `annex-iv-pack-builds` job |
| `compliance/risk-register.md` | All rows reviewed and updated |

## KB files this stage updates

- `KB_18_Governance_Evidence.md`
- `KB_10_Production_Hardening.md`
- `KB_TASK_LOG.md`

## Verification commands

```bash
python scripts/generate-annex-iv-doc.py
ls -la compliance/annex-iv-packs/latest.pdf
cd backend && pytest tests/compliance/ -v
```

## Audit target

- Non-reducing acceptable (governance-only stage); close with `--no-baseline-drop "governance evidence pipeline"`.

## Role

- Primary: `compliance-engineer`
- Secondary: `agentic-governance-engineer` (ADR for AI policy)

## Hand-off

- What is now true: Annex IV pack can be regenerated on demand; ISO/IEC 42001 controls have evidence anchors.
- Next stage (20) adds the red-team eval harness that the pack references.
