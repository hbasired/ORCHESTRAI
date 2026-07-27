# ISO/IEC 42001 Internal Audit — 2026-Q4 (Stage 23 dry-run)

> Internal audit of the AI Management System (AIMS) against **ISO/IEC 42001** Annex-A controls (38 controls / 9 control
> objectives), conducted BEFORE any external certification audit to find nonconformities early (research §33.3). Scope:
> the agent control plane (Stages 0–22). Auditor: internal (agentic-governance + compliance personas) — this is a
> self-audit dry-run, NOT an accredited certification. Method: verify conformance to the clauses + Annex-A controls
> against LIVE evidence (cite real file paths); rate each Conformant (C) / Partial (P) / Nonconformity (NC); route NCs
> to Stage 24.

## Management-system clauses (4–10) — summary

| Clause | Requirement | Status | Evidence |
|---|---|---|---|
| 4 Context | Scope, interested parties, AIMS boundary | C | `PRD-ai-embodied-agent-v3.md`, KB_26 (market/ICP), risk-register row 1 (Annex-III classification) |
| 5 Leadership | AI policy, roles, commitment | C | `compliance/ai-policy.md` (ISO 42001 A.6.1, Stage 19); role personas `.claude/skills/*` |
| 6 Planning | Risk + impact assessment, objectives | C | `compliance/risk-register.md` (refreshed every CTO checkpoint); §A.5 below (impact) |
| 7 Support | Resources, competence, documented info | C | KB_* knowledge base; model cards; `audit_chain` documented info |
| 8 Operation | AI lifecycle, risk treatment | C | KB_25 self-healing loop; Stage-17 safety; Stage-20 evals |
| 9 Performance eval | Monitoring, internal audit, mgmt review | P | this audit + `post-market-monitoring-plan.md`; **mgmt-review record owed (NC-1)** |
| 10 Improvement | Nonconformity + corrective action | C | `audits/OPEN_GAPS_LEDGER.md` (the carry-forward register IS the NC/CAPA log) |

## Annex-A control objectives (9) — control-by-control

### A.2 Policies related to AI — **C**
- AI policy documented + approved: `compliance/ai-policy.md` (Stage 19). Aligned with org objectives + reviewed at checkpoints. **C.**

### A.3 Internal organization (roles, responsibilities, reporting of concerns) — **C**
- Roles defined (`.claude/skills/<role>/SKILL.md`); decision authority + segregation (builder ≠ independent reviewer ≠ CTO). Concern-reporting via the incident playbook + ledger. **C.**

### A.4 Resources for AI systems (data, tooling, system, human, compute) — **C**
- Data: DVC-tracked datasets + CARDs (KB_03). Tooling: pinned deps + SBOM (Stage 18). Compute: free/local (Rule 9). Human: HITL oversight. **C.**

### A.5 Assessing impacts of AI systems (ISO 42005) — **P**
- Impact considerations in the risk register (safety, rights, environment-of-use) + the ISO 10218 RA (`compliance/iso-10218-risk-assessment.md`). **Partial: a standalone ISO 42005 AI-system-impact-assessment document is not yet authored (NC-2 → Stage 24).** The inputs exist (risk register + RA + intended-purpose); they need consolidating into the 42005 format.

### A.6 AI system life cycle — **C**
- Responsible dev objectives (Hard Rules 1/9/11 — no theatre, free-cost, depth-first); design (KB_24 HLD/LLD + system-designer ADRs); V&V (per-stage audit + independent review + CI gates); deployment (`pilot-deployment-runbook.md`); operation/monitoring (`post-market-monitoring-plan.md`). Every stage: research → implement → audit → independent review → close. **C.**

### A.7 Data for AI systems (provenance, quality, preparation) — **C**
- Dataset CARDs + provenance (C-MAPSS/NEU-CLS/AI4I benchmarks documented honestly as proxies); real-fleet re-fit plan for site data (`pilot-onboarding-kit.md`); mem0 namespace isolation + Postgres RLS (Stage 19/22) for data segregation. **C.**

### A.8 Information for interested parties (transparency, documentation) — **C**
- Annex IV technical-documentation pack (Stage 19, 14 sections, signed); decision explanations (SHAP/DiCE, Stage 10); model cards; transparency to deployers via the runbook. **C.**

### A.9 Use of AI systems (intended use, oversight, monitoring) — **C**
- Intended-use envelope documented; Art-26 deployer checklist (runbook §3); HITL human oversight; post-market monitoring. **C.**

### A.10 Third-party & customer relationships — **P**
- Third-party deps: SBOM + dependency-exceptions (Stage 18). A2A external-peer trust boundary (Stage 14) + governance L0-peer confinement (Stage 23 RBAC). **Partial: customer/pilot agreements + a supplier-AI-responsibility register are pending a real pilot (NC-3 → Stage 24, needs a buyer — G-035/G-043).**

## Access-control / governance (Stage 23 additions, strengthening A.3/A.7/A.9)
- **Bell-LaPadula MAC** (`backend/governance/mac.py`) — confidentiality no-read-up / no-write-down, audited.
- **Agent-hierarchy function-scoped RBAC** (`backend/governance/rbac.py`) — L3→L0 least-privilege; L0 peer confined.
- **Total traceability** (`backend/governance/traceability.py`) — state_snapshot(pre/post) + decision → audit_chain (Art-12 / A.6). *Audit-wiring verified live when Docker is up (pure logic tested now: 9/9).*

## Nonconformities (routed to Stage 24)
- **NC-1 (minor):** no documented **management-review** record (clause 9.3) — author a management-review minute. → Stage 24.
- **NC-2 (minor):** **ISO 42005** AI-system-impact-assessment not yet a standalone doc (A.5) — consolidate from existing inputs. → Stage 24.
- **NC-3 (minor, blocked):** **customer/supplier AI-responsibility** records (A.10) need a real pilot engagement (G-035/G-043). → Stage 24 / pilot.
- **OBS:** governance MAC/RBAC audit-wiring is verified live only when Docker is up (pure logic tested) — re-verify at Stage 24.

## Verdict
**AIMS substantially conformant** for a pre-certification internal audit: 7/9 objectives Conformant, 2 Partial with minor
NCs, 0 major NCs. The evidence machinery is real + self-attesting. Honest: this is a self-audit dry-run, not an accredited
certification; the 3 minor NCs + the external-assessor engagement remain before a real ISO 42001 certification.
