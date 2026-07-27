# Stage 21 — Independent Review (Disaster Recovery, HA posture & backups)

**Reviewer:** independent `task-auditor` persona (a DIFFERENT agent than the Stage-21 implementer).
**Date:** 2026-06-26
**Mode:** **DYNAMIC** — Docker stack UP (ai-agent-postgres @5544→5432, ai-agent-neo4j, ai-agent-redis). Every backup /
restore / chaos / determinism script was **executed live**, including two **adversarial corruption/mismatch tests** on
restore-verify and a deliberate `backup-all` neo4j-restart observation.
**Scope:** `scripts/backup/{lib.sh,backup-all.sh,backup-postgres.sh,pg-basebackup.sh,backup-neo4j.sh,backup-redis.sh}`,
`scripts/restore/restore-verify.sh`, `scripts/chaos/kill-postgres-drill.sh`, `compliance/dr-runbook.md`,
`docker/docker-compose.yml` (PITR block), `.github/workflows/ci.yml` (`dr-backup-restore`),
`backend/tests/agents/runtime/test_runtime_determinism.py`, ADR `2026-06-22_stage21_dr_ha_backups.md`, ledger
G-066/G-004, risk-register data-loss row, research §31/§31.5, explainer `research/stage-explainers/STAGE_21/index.html`.

---

## VERDICT: **PASS-WITH-GAPS**

The core binding deliverable — the **tested restore-verify** — is genuinely **load-bearing**: I proved it exits
nonzero on a row-count drift AND on a corrupt archive (not a rubber-stamp). Backups, the PITR base backup, the chaos
drill, and the determinism test all PASS live with real assertions and no theatre. The honesty discipline in the ADR /
runbook / ledger / risk-register is strong (G-066 honestly split DR-vs-horizontal-scale; PITR honestly OFF-by-default;
HA honestly deferred; RPO/RTO measured/target-tagged; free-cost respected). **No actuator path added; audit holds 364.**

The gaps are real but **not fabrication/theatre** and **none block the DR claim being honest**:
- **G-078 (medium, NEW):** on this Windows/Docker-Desktop host, `backup-neo4j.sh` / `backup-all.sh` **left the Neo4j
  container DOWN after the offline-dump stop→start cycle** (entrypoint "Neo4j is already running (pid:7)" /
  NEO4J_AUTH re-init conflict on `docker start`), yet `backup-all` reported `neo4j -> OK` / `=== backup-all OK ===`.
  The script's restart trap issues `docker start` but **does not verify** Neo4j recovered, so a failed restart is
  silent. The dumps themselves were produced correctly and data survived a container recreate.
- **G-079 (low, NEW):** the chaos drill's secondary assertion ("verify-audit-chain.py FAILs with PG down ⇒ honest")
  is **not load-bearing**: `verify-audit-chain.py` exits 1 even when PG is UP (pre-existing invalid-signature rows,
  G-073-adjacent), so that leg is always-true regardless of the fault. The drill's PRIMARY assertion (the probe →
  empty when PG down, `OK:N` when up) IS genuine and load-bearing.
- **Doc nit:** `backup-all`'s SHA-256 manifest leaves the **neo4j checksum column blank** (the artefact is a directory,
  `sha256sum` no-ops) — the "(-0) 0 errors / SHA-256 manifest" claim is partially unmet for the graph store.

---

## Per-criterion evidence

| AC | Claim | Independently confirmed? | Evidence |
|---|---|---|---|
| AC1 Postgres backup | `pg_dump -Fc` + `pg_restore --list` integrity; `pg-basebackup` PITR anchor; WAL-archive config OFF | **YES** | `backup-postgres.sh` → 2,174,561-byte dump, "archive integrity OK"; `pg-basebackup.sh` → `base.tar.gz` (7.5 MB) + `pg_wal.tar.gz` + `backup_manifest`. compose lines 71–83 = PITR block OFF-by-default with the bad-`archive_command`→full-disk rationale. |
| AC2 Neo4j + Redis backup | offline `neo4j-admin database dump` (neo4j+system); Redis RDB; backup-all + manifest + retention | **PARTIAL** | `backup-all` produced `neo4j.dump` (30,820 B) + `system.dump` (18,343 B) + `dump_*.rdb` (88 B) + a manifest with pg/redis SHA-256 sums. **GAP G-078:** Neo4j container left `Exited(1)` after the run; **GAP (nit):** neo4j manifest checksum blank (dir, not file). |
| AC3 Tested restore (BINDING) | restore to scratch DB + row-count + audit_chain head parity; nonzero on mismatch | **YES — provably load-bearing** | PASS live: 22 public tables, `audit_chain` head `382:\x95d3cc73...`, RTO ~4 s. **Adversarial #1:** added a drift table to the live DB → restore-verify printed the diff and **exited 1**. **Adversarial #2:** corrupted the dump header → `pg_restore --list` gate caught it, **exited 1** before touching the scratch DB. Cleaned up; live DB back to 22 tables. |
| AC4 Chaos drill (G-004) | kill PG → honest degradation (no fabrication) → recovery | **YES (primary leg)** | PASS live: probe `OK:382` → empty while down → `OK:382` after restart. **GAP G-079:** the `verify-audit-chain.py`-FAILs leg is weak (it fails even with PG up). |
| AC5 DR runbook | RPO/RTO, recovery steps, 3-2-1, honest scope | **YES** | `compliance/dr-runbook.md` — RPO ≤60 s (PITR), RTO <5 min target (measured ~4 s), §5 step-by-step PG/Neo4j/Redis recovery, §7 honest single-node boundary, multi-node HA deferred. |
| AC6 Determinism (CTO #3) | two runs same incident → identical trajectory + decisions | **YES** | `pytest tests/agents/runtime/test_runtime_determinism.py -q` → **1 passed** (NOT skipped) in 8.87 s; test asserts `traj1==traj2`, non-empty traj, `dec1==dec2`. Real assertion, predictor available. |
| AC7 CI gate `dr-backup-restore` | named PG → seed schema → backup + restore-verify; fail on mismatch | **YES (static)** | ci.yml:497–524 — named `ai-agent-postgres` (pgvector:pg16), seeds incidents/decisions/audit_chain, runs `backup-postgres.sh` + `restore-verify.sh`, uploads manifest. Exercises the real docker-exec path. Not executed in CI here; the restore-verify it calls is dynamically proven above. |
| AC8 Tests + audit | determinism passes; audit holds 364 | **YES** | determinism 1 passed; `scripts/audit.sh` = **364** (= baseline; additive scripts + 1 test outside the theatre tree; `--no-baseline-drop` justified). |

## Hard-rule checks

- **Rule 1/1a (no theatre/fabrication):** PASS. Grep for `random.uniform|random.choice|Math.random|generateMockState|
  _get_demo_|RESPONSES = {|MODELS = [|actuator.` over `scripts/backup`, `scripts/restore`, and the determinism test →
  **no matches**. The chaos drill's degradation check is REAL (probe genuinely returns empty under fault, not a fake).
- **Rule 9 (free/OSS/local):** PASS. Only `pg_dump`/`pg_restore`/`pg_basebackup`/`neo4j-admin` (Community)/`redis-cli`
  via `docker exec`. Neo4j Community offline dump only (no Enterprise). Off-site is `rclone` **config-only**, not
  exercised. No paid cloud, no committed keys. New deps: **none**.
- **Rule 11 (research-first):** PASS. `research/initial-research.md` §31 (SOTA) + §31.5 (exact mechanics) dated
  2026-06-22, BEFORE implementation. Explainer `research/stage-explainers/STAGE_21/index.html` present (6,466 B).
- **No actuator path:** PASS — DR scripts touch only the data tier; no `actuator.*` / `safety.validate` surface added.
- **Baseline discipline:** holds 364 with justified `--no-baseline-drop` (additive infra stage). Acceptable.

## Honesty audit of claims vs reality

- **G-066 honestly split:** YES — ledger row 104 explicitly states "G-066 was mis-tagged 'DR/HA' but its real content
  is HORIZONTAL SCALE … the horizontal-scale hardening REMAINS → Stage 22"; risk-register row 108 echoes this. The
  Stage delivered the **DR half** and says so plainly. Good honesty.
- **PITR / WAL-archiving honestly OFF:** YES — compose lines 71–83 + ADR D1 + runbook §2/§5 all describe it as
  config-provided/OFF-by-default with the full-WAL-disk rationale; never claimed "active." Honest.
- **Multi-node HA honestly deferred:** YES — ADR D5, runbook §7, risk-register row 109 all defer to pilot/cloud.
- **RPO/RTO measured vs target:** YES — RTO ~4 s is tagged *measured* (restore-verify timing I reproduced); RPO ≤60 s
  is tagged *target* (depends on enabling PITR). Not fabricated.
- **Overclaim found:** the chaos-drill / KB_TASK_LOG line "verify-audit-chain.py FAIL … honest degradation" overstates
  the load-bearingness of that leg (it fails regardless of PG state — G-079). Minor; the probe leg carries the claim.

## DYNAMIC verification log (commands actually run)

```
bash scripts/backup/backup-postgres.sh                  → OK, dump 2,174,561 B, integrity OK  (exit 0)
bash scripts/restore/restore-verify.sh                  → PASS, 22 tables + audit_chain head 382  (exit 0)
# adversarial: drift table added to LIVE db
bash scripts/restore/restore-verify.sh                  → "row-count MISMATCH", prints diff  (exit 1)  ← CATCHES drift
# adversarial: corrupted dump header
bash scripts/restore/restore-verify.sh <corrupt.dump>   → "pg_restore --list failed — corrupt archive"  (exit 1)  ← CATCHES corruption
bash scripts/backup/backup-all.sh                       → "=== backup-all OK ===" (exit 0) BUT neo4j left Exited(1) — G-078
bash scripts/backup/pg-basebackup.sh                    → base.tar.gz 7.5 MB + pg_wal.tar.gz + manifest (exit 0)
PROMPT_GUARD_EMBED_MODEL=... bash scripts/chaos/kill-postgres-drill.sh → PASS, OK:382→down→OK:382 (exit 0)
verify-audit-chain.py (PG UP)                           → exit 1 (pre-existing invalid sigs) — basis of G-079
pytest tests/agents/runtime/test_runtime_determinism.py → 1 passed (exit 0)
bash scripts/audit.sh                                   → 364 (= baseline)
# recovery: neo4j container recreated from docker_neo4j-data volume → healthy, 47 nodes intact, no data lost
```

## NEW gaps (appended to OPEN_GAPS_LEDGER.md)

- **G-078 (medium → Stage 22):** `backup-neo4j.sh`/`backup-all.sh` does not verify Neo4j restarted healthy after the
  offline-dump stop; on Docker-Desktop/Windows the NEO4J_AUTH re-init makes plain `docker start` fail, leaving the
  graph store DOWN while `backup-all` reports OK. Fix: wait-for-health + pidfile/auth-conflict handling after restart,
  fail the run if the container isn't healthy.
- **G-079 (low → Stage 21.5/maintenance):** the chaos drill's `verify-audit-chain.py`-FAILs leg is not load-bearing
  because the script exits nonzero even with PG up (invalid-signature rows; G-073-adjacent). Either fix the underlying
  invalid sigs or make the drill's app-layer assertion fault-specific. Also: `backup-all` manifest leaves the neo4j
  store's SHA-256 blank (directory artefact) — checksum the individual `.dump` files for the 0-errors claim.

## Bottom line

A solid DR stage. The one deliverable that had to be real — **restore-verify** — is provably real (catches both drift
and corruption, exits nonzero). Backups, base backup, chaos drill, and determinism all pass live with honest assertions.
Honesty discipline around deferrals/PITR/G-066-split is exemplary. The PASS-WITH-GAPS is for the silent Neo4j-restart
failure (G-078) and the weak chaos secondary assertion (G-079) — both ledgered, neither undermining the honest DR claim.
