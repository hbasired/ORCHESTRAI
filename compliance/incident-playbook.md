# Incident Playbook

> EU AI Act Article 26 (deployer obligations) + NIST AI RMF Agentic Profile + OWASP LLM Top 10 evidence. The runbook the on-call follows when something goes wrong.

## Scope

Three classes of incident:
1. **Operational** — service degradation, latency budget breach, model accuracy regression.
2. **Safety** — agent took (or nearly took) an action outside safe bounds.
3. **Security** — prompt injection, data exfiltration, unauthorized access.

## Severity matrix

| Sev | Trigger | Response time | Pager |
|---|---|---|---|
| SEV1 | Customer-facing outage; agent halted production; safety constraint violated | 15 min | On-call + CEO |
| SEV2 | Latency SLA breach; model accuracy >5pp regression; security alert triggered | 1 hour | On-call |
| SEV3 | Drift detector trips; non-blocking warning; non-critical log gap | next business day | Engineering team |

## SEV1 — Operational outage runbook

1. **Acknowledge** — page on-call; post in incident channel; create incident ticket.
2. **Stabilize** — flip system mode to `Halted` from `/embodied-agent` (operator override surface). Agent stops; sim freezes.
3. **Diagnose** — check Grafana (latency, throughput, model inference time); check Loki (recent error logs); check Jaeger trace of the most recent failed cycle.
4. **Fallback** — if backend is the issue, frontend falls back to `getMockState()` with the "Offline" banner. Customer can continue to operate manually.
5. **Restore** — fix or roll back; verify with the `scripts/audit.sh` baseline check.
6. **Postmortem** — within 5 business days. Add to `decision-logs/YYYY-MM-DD_postmortem_<incident>.md`.

## SEV1 — Safety incident runbook

(Agent took, or attempted to take, an action that violated a Stage 7 safety constraint, or caused real-world harm.)

1. **Halt immediately** — flip system mode to `Halted`. Suspend any pilot integration via `human-oversight.md` controls.
2. **Preserve evidence** — `decision_logs` retention is 6 months by default; for safety incidents, the incident's row(s) are flagged `do-not-purge`.
3. **Notify** — within 24 hours, notify affected personnel + the customer's compliance contact. Within 72 hours for EU pilots, notify the relevant Member State authority (per Article 26).
4. **Root cause** — distinguish: model defect, training data defect, sensor / input defect, simulator-real divergence, operator misuse.
5. **Mitigation** — implement before any restart: tighten the relevant safety constraint, gate the failing action class behind operator approval, retrain affected models if input-distribution drift was the cause.
6. **Postmortem** — within 5 business days; add to `compliance/decision-logs/`.
7. **Regulator follow-up** — file the full incident report with the notified body (EU) within 15 days; comparable timeline for other regulators.

## SEV1 — Security incident runbook

### Prompt injection (LLM01)

1. Identify the injected tool output (DB row, external API response, operator input).
2. Halt agent action immediately; switch to recommend-only mode.
3. Audit `decision_logs` for any action taken since the injection began; flag for review.
4. Sanitize: tighten the prompt-injection sanitizer (Stage 11) to catch the new pattern; add a unit test reproducing the attack.
5. Restore: re-enable autonomous mode only after the new sanitizer passes a red-team exercise.

### Sensitive data disclosure (LLM06)

1. Identify what was disclosed (operator name, customer-specific data, weights / hyperparameters).
2. Revoke any tokens / credentials exposed.
3. Notify affected parties per applicable regulation (GDPR if EU customer data; per-customer contract otherwise).
4. Tighten the output filter; audit logs.

### Excessive agency (LLM08)

1. Identify the action the agent took that exceeded its scope.
2. If the action is reversible (e.g. revert a supplier order), revert immediately.
3. Tighten the safety-constraint layer (Stage 7); reduce the agent's action-class permissions until reviewed.
4. Re-train or fine-tune as needed; update `risk-register.md`.

### Cross-session memory leak (NIST RMF Agentic Profile)

1. Identify which sessions cross-contaminated.
2. Clear all agent memory; rotate the memory-namespace salt.
3. Notify any operators whose incidents may have been exposed in another session.
4. Tighten namespacing in Stage 11; add a unit test reproducing the leak.

## OWASP LLM Top 10 controls (per-PR checklist)

| ID | Risk | Control |
|---|---|---|
| LLM01 | Prompt injection | Sanitizer on every tool output before LLM context; red-team test |
| LLM02 | Insecure output handling | All LLM outputs are JSON-schema-validated before they reach a tool / DB write |
| LLM03 | Training data poisoning | DVC pinning + provenance; CI rejects un-versioned data |
| LLM04 | Model denial of service | Rate limiting on `/api/decision`; circuit breaker on LLM calls |
| LLM05 | Supply-chain vulnerabilities | SBOM generated per image (Stage 14); deps pinned + audited |
| LLM06 | Sensitive information disclosure | Output filter; operator UI shows reasoning *summary*, not raw prompts |
| LLM07 | Insecure plugin design | All tool calls go through the embodied-agent coordinator; no direct LLM → tool calls |
| LLM08 | Excessive agency | Safety constraint layer (Stage 7); operator override always available |
| LLM09 | Overreliance | Operator UI shows confidence; recommend-only mode is default for new pilots |
| LLM10 | Model theft | Weights in Git LFS with access controls; pilot deploys ship Triton with auth |

## Notification matrix

| Audience | When | How |
|---|---|---|
| On-call engineer | SEV1, SEV2 | Pager + incident channel |
| Engineering team | SEV3 | Incident ticket |
| Customer compliance contact | SEV1 (safety, security) | Within 24 hours, email + call |
| EU notified body | SEV1 (safety) in EU pilot | Within 15 days, formal report |
| GDPR DPA | Personal-data breach in EU pilot | Within 72 hours |
| Other regulators | Per-jurisdiction | Per-jurisdiction timeline |

## Review

This playbook is reviewed annually and after every SEV1 incident. New attack patterns and new failure modes update the relevant runbook section.

## SEV1 — PQC key compromise runbook (Stage 13.5+, PRD v2.0)

(Suspected or confirmed compromise of `agent-identity-<env>` ML-DSA-65 key, `agent-tls-<env>` ML-KEM-768 + X25519 hybrid key, `firmware-policy-<env>` SLH-DSA-SHA2-128s key, or `ot-msg-integrity-<env>` HMAC-SHA-384 key.)

1. **Halt + isolate** — flip system mode to `Halted`. Disconnect the compromised env from A2A peer federation (revoke our own agent card; we cease to be a trustable peer until rotation completes).
2. **Determine scope** — which key, which env (dev / staging / pilot / prod), suspected vector (Vault/SoftHSM breach, leaked key file, side-channel). Identify time window of exposure.
3. **Forced rotation (emergency)** — `scripts/rotate-pqc-keys.sh --key-type=<type> --grace-hours=0` performs an immediate rotation with no overlap window. Old key marked revoked in `backend/a2a/revocation.py`'s published list.
4. **Audit chain inventory** — for `agent-identity-<env>` compromise: every `audit_chain` row signed in the exposure window is suspect. Mark these rows with a `key_compromise` annotation row (signed by new key). Notify auditors that the affected rows have known-compromised signatures (the chain hash remains valid for tamper detection; the signatures are no longer trusted attestation).
5. **A2A federation re-bootstrap** — re-emit agent card with new key; notify all peers via their revocation list polling cycle. Manual notification to high-value peers within 1 hour.
6. **OT layer (`ot-msg-integrity` compromise)** — re-key all Sparkplug B + OPC UA MAC computations; force re-birth on all Sparkplug B nodes; rotate OPC UA cert chain.
7. **Firmware (`firmware-policy` compromise)** — invalidate all signed policy bundles; require operator re-sign of any deployed bundles before re-acceptance.
8. **Postmortem** — within 5 business days; ADR in `compliance/decision-logs/YYYY-MM-DD_pqc_key_compromise_<env>.md`. Include: root cause, time of exposure, scope, mitigation, customer notification log.
9. **Regulator notification** — if pilot env affected, customer compliance contact within 24 hours; EU notified body within 15 days if EU pilot; GDPR DPA within 72 hours if personal data was protected by the compromised key.

## SEV2 — A2A peer revocation / suspicious behavior runbook (Stage 14+, PRD v2.0)

(A peer agent's behavior triggers a flag: malformed agent card, signature verify failure on a reply, anomalous request patterns, capability invocation outside declared scope.)

1. **Soft revoke** — mark the peer as `quarantine` in `backend/a2a/peer_state.py`. In-flight requests from the peer drain; no new requests accepted.
2. **Diagnose** — diff the peer's current agent card against the cached version; check the peer's revocation list; query `audit_chain` for all `a2a.*` rows naming this peer in the last 24 h.
3. **Hard revoke** (if compromise suspected) — add the peer's `public_key_b64` to our revocation list; push to all our agent peers (so they know to refuse the bad actor too); notify the peer's listed contact.
4. **Audit** — flag every `audit_chain` row attributed to that peer in the exposure window for compliance review.
5. **Re-establish** (if false positive) — peer re-signs a fresh agent card with explicit replay-protection nonce; we re-verify; mark peer `active` again.
6. **Postmortem** — within 5 business days for confirmed compromises; logged in `compliance/decision-logs/YYYY-MM-DD_a2a_peer_revoke_<peer>.md`.

## Audit chain integrity failure (SEV1)

If `scripts/verify-audit-chain.py` reports a broken chain:

1. **Halt all `audit_chain.append` writes** — by design the chain is broken; further writes don't help.
2. **Determine break point** — `python scripts/verify-audit-chain.py` (full, not `--quick`) reports the lowest `seq` where the hash chain broke.
3. **Investigate** — was the underlying DB tampered with (against pgaudit log)? Was a row written without ML-DSA-65 signature? Was the canonical-payload encoding incorrect?
4. **Notify** — regulator notification within 15 days; affected customers within 24 hours. A broken audit chain is a Material Compliance Incident under EU AI Act Art. 12.
5. **Repair** — append a single `chain_repair` row signed by the active key; the row's payload documents the break point and the investigation. The chain hash from this row forward is fresh; pre-break rows remain individually verifiable but the cross-row chain is broken below this seq.

## Review history

- 2026-05-11 — Stage 0 refresh. Initial playbook written. Will be expanded in Stage 14 with concrete tooling for SBOM generation, drift alerts, and on-call rotation.
- 2026-05-18 — PRD v2.0 expansion: added PQC key compromise runbook, A2A peer revocation runbook, audit chain integrity failure runbook. Mapping to Stage 13.5 (PQC) + Stage 14 (A2A) + Stage 19 (governance evidence).
