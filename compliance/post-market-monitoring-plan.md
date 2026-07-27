# Post-Market Monitoring (PMM) Plan — EU AI Act Article 72 (Stage 22)

> The Article-72 post-market-monitoring plan for the high-risk AI system. Art-72 requires the plan to be **part of the
> Annex IV technical documentation** — it is ingested by `scripts/generate-annex-iv-doc.py` (Stage 19 pack). The PMM
> system "actively and systematically collects, documents and analyses" performance + incident data across the system's
> lifetime to evaluate **continuous compliance** with Chapter III §2. Free/OSS/local data sources (Rule 9). Research §32.

## 1. Purpose & scope

Continuously evaluate, after the system is placed on the market / put into pilot service, that it still meets the
high-risk requirements (risk management, data governance, accuracy/robustness/cybersecurity, human oversight, logging).
Scope: the agent control-plane (predict→diagnose→reason→verify→intervene loop) + its safety, crypto, memory, and
governance subsystems.

## 2. What is monitored, the data source, and the threshold

| Dimension (Chapter III §2) | Monitored signal | Data source (already built) | Threshold / trigger |
|---|---|---|---|
| Accuracy / performance | RUL/defect/decision quality; agentic tool-selection / action-completion / reasoning-coherence | `ml.inference.*` spans; `training/evals/agentic_metrics.py`; model `*.metrics.json` | drift below the model-card baseline → review |
| Robustness (adversarial) | Prompt-injection refusal; agentic attack-block rate | `nightly-evals.yml` (OWASP-LLM01 + NIST) → `training/evals/results/*.json` | OWASP refusal < 0.99, or any NIST block < 1.0 → investigate |
| Cybersecurity | Audit-chain integrity; PQC signing; zero-trust/tool-manifest | `verify-audit-chain.py` (scheduled); `tool_manifest` drift | verify exit ≠ 0, or a rogue tool detected → suspend + investigate |
| Human oversight | HITL approve/override rate on SIL-1+ | `runtime/hitl.py` + `audit_chain` rows | oversight bypassed / override rate spikes → review |
| Functional safety | STO/SS1 trips; every `actuator.*` preceded by `safety.validate.*` | safety spans + CI trace-pairing invariant | any unpaired actuator span → STOP, root-cause |
| Logging / traceability | Audit-chain append rate + ≥6-month retention (Art-12) | `audit_chain` + OTel evidence sink | retention/append gap → fix |
| Data governance | Cross-namespace memory isolation | mem0 `_authorize` + Postgres RLS (Stage 19/22) | any cross-namespace read → security incident |

## 3. Cadence

- **Continuous / per-decision:** spans + `audit_chain` rows (every loop iteration).
- **Per-PR (CI):** `phoenix-evals` (deterministic red-team subset), `safety-contract-tests`, `dr-backup-restore`, `sbom`.
- **Nightly:** full hybrid red-team eval (`nightly-evals.yml`); scheduled `verify-audit-chain.py`.
- **Per pilot milestone:** restore-verify + chaos drill (Stage 21); runbook re-validation; this plan reviewed.
- **Quarterly:** dependency bump + full-live re-test (G-055/G-056); risk-register full refresh (every CTO checkpoint).

## 4. Collection, analysis & feedback loop

Signals land in two stores (KB_15 two-store split): mutable traces (Langfuse/Phoenix via the OTel collector) for
debugging/eval review, and the immutable `audit_chain` (SHA-256 chained, ML-DSA-65 signed) for regulator evidence.
Results feed back into: the risk register (new/updated rows), the Annex IV pack (regenerated), and — on a serious
finding — the Article-26 incident-reporting path (`compliance/incident-playbook.md`).

## 5. Serious-incident handling (Art-72 → Art-73)

On a serious incident or a malfunction that could breach Chapter-III obligations: suspend the affected function (safety
layer drives to a safe state), capture the `audit_chain` slice + traces as evidence, notify per the deployer obligations
(runbook §3 / incident playbook), and root-cause before resuming. The post-market data that revealed it is retained.

## 6. Ownership & honest status

- **Owner:** compliance-engineer (plan) + devops-sre (pipelines) + security-pqc-engineer (chain/crypto signals).
- **BUILT:** every data source above exists and is exercised (spans, evals, audit-chain verify, DR drills, RLS).
- **PLANNED (post-build / pilot):** an operator-facing PMM dashboard rendering these signals over time (the spans exist;
  the cascade/latency UI is G-021); a real-deployment incident feed (needs the live pilot). Honestly deferred, ledgered.
