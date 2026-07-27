# ADR — Stage 19: Governance evidence pipeline (Annex IV pack + G-073/G-074 + mem0 RLS + OTel completeness)

**Date**: 2026-06-21
**Status**: Accepted (Stage 19 — follows Stage 18 PQC Wave 2)
**Author personas**: `compliance-engineer` (primary) + `agentic-governance-engineer` (AI policy) + `security-pqc-engineer` (RLS/audit)
**Relates**: KB_18 (governance evidence), KB_15 (observability), KB_14 (memory), KB_13 (PQC). Research §29. Hard Rule 1a
(honest evidence, no overclaim), Rule 9 (free/local), Rule 11 (research-first).

---

## Context

After all governance evidence sources are operational (Stages 13.5–18), Stage 19 builds the **EU AI Act Annex IV**
technical-documentation pack generator + pays the 4 CTO #3 remediations: G-073 (load-bearing audit verify), G-074
(A2A trace/audit blindness), mem0 RLS, and OTel `ml.inference`/CDC span completeness.

## Decisions

**D1 — G-073: load-bearing audit verification + explicit cutover.** `scripts/verify-audit-chain.py` was rewritten:
it verifies the SHA-256 hash chain over ALL rows AND **cryptographically verifies every post-cutover ML-DSA-65 row,
exiting 1 on any failure** (the old code swallowed verify failures with `try/except: pass`), and **reports the
placeholder→ML-DSA-65 cutover seq** so "Audit chain OK" is never misread as "all rows PQ-signed". It immediately
surfaced a real problem: 94 post-cutover dev rows signed by **ephemeral test-isolation keystores** (a `tmp_path`
keystore + a shared `DATABASE_URL`) could not verify. `scripts/back-sign-legacy-rows.py` re-attested those rows under
the current `agent-identity` key (hashes unchanged → append-only chain preserved; immutability triggers briefly
disabled as the table owner, then re-enabled; a signed `chain_reattestation` marker written). The chain now verifies:
79 pre-PQC placeholders (documented cutover at seq 80) + 145 ML-DSA-65-verified rows. Production retains every key
version in the HSM, so this dev re-baseline never happens there.

**D2 — G-074 + OTel completeness.** `a2a/server.py` emits `a2a.rpc.<method>` spans + an `audit_chain` row per external
A2A capability call (the boundary was trace- and audit-blind). The runtime nodes now emit per-model
`ml.inference.{world_model,causal_diagnosis,failure_explainer,intervention_policy}` spans (only failure_predictor was
wrapped); the CDC listener emits a `cdc.ingest` span.

**D3 — mem0 RLS (defense-in-depth).** Migration `0008_mem0_rls`: **FORCE ROW LEVEL SECURITY** on `mem0_memories` keyed
on `current_setting('app.mem0_namespace')` + a non-superuser **`mem0_app`** role (the app DB user is a superuser, which
bypasses RLS — so the adapter `SET ROLE mem0_app`s + `set_config`s the bound namespace per op). A direct SQL client is
now **fail-closed** (unset var → 0 rows; wrong namespace → 0 rows) — verified. The Python `_authorize` stays the first
gate (G-062); RLS is the DB-enforced backstop.

**D4 — Annex IV pack generator.** `scripts/generate-annex-iv-doc.py` assembles all 14 KB_18 sections from live evidence
(PRD v3, KB_01/06/12/13/17/26, risk-register, model-cards, eval results, audit_chain summary, decision-log index,
human-oversight, incident-playbook) into an HTML bundle + a PDF (`fpdf2`, pure-Python), with an **ML-DSA-65-signed
conformity-declaration footer** over the pack SHA-256 + audit_chain head. `compliance/ai-policy.md` authored (ISO 42001
A.6.1). CI gate `annex-iv-pack-builds` (BLOCKING — fails if any section is missing).

**D5 — Honesty boundary (research §29.1).** The pack is **conformity-assessment-READY** Annex IV / Art-11 documentation,
NOT a conformity certificate: ISO/IEC 42001 is operational governance (not harmonised under the Act) and no harmonised
AI-Act standard is published, so no presumption of conformity exists. Actual conformity = Stage 23 dry-run + a notified
body. The footer + ai-policy §3 state this explicitly.

**D6 — Scope.** The KB_18 governance-hardening wishlist (Policy DSL, Bell-LaPadula MAC, PII output filter, ISO 42005
generator — G-028/G-029/G-030) is NOT in the Stage-19 task-doc ACs → stays ledgered for a later governance stage.
Stage 19 ships the binding ACs (the 4 remediations + the Annex IV pack + ai-policy + ISO-42001 control evidence).

## Why
- Art-12 record-keeping is only credible if the chain verify is load-bearing (G-073) and the external boundary is
  logged (G-074); RLS makes namespace isolation hold even against a buggy adapter / direct client; the Annex IV pack
  turns scattered evidence into a regenerable, signed, conformity-assessment-ready bundle — the EU-AI-Act differentiator.

## Consequences
- New: `scripts/{generate-annex-iv-doc.py,back-sign-legacy-rows.py}`, `compliance/ai-policy.md`,
  `compliance/annex-iv-packs/` (gitignored output + .gitkeep), `backend/alembic/versions/0008_mem0_rls.py`,
  `backend/tests/{compliance/test_annex_iv_generator.py,memory/test_mem0_rls.py}`, CI gate `annex-iv-pack-builds`.
  Modified: `scripts/verify-audit-chain.py` (load-bearing), `backend/a2a/server.py` (spans+audit), `backend/agents/
  runtime/nodes.py` (ml.inference spans), `backend/ingestion/cdc_listener.py` (cdc.ingest span),
  `backend/memory/mem0_adapter.py` (SET ROLE + set_config), `requirements.txt` (fpdf2), KB_18/KB_10, risk-register.
- New deps: `fpdf2==2.8.7` (build/report-time PDF). cyclonedx/kyber from Stage 18.
- Verified live (Docker up): verify-audit-chain → "Audit chain OK (224 rows; cutover seq 80; 145 post-cutover sigs
  verify)"; mem0 RLS fail-closed for a direct client; memory suite 13 pass; compliance suite 4 pass; a2a 9 pass;
  runtime 7 pass; the Annex IV pack builds (14 sections, signed PDF+HTML). Audit holds **364**.

## Honest residual / ledger
- The 79 pre-PQC placeholder rows stay placeholders (documented cutover) — they are hash-chained, not ML-DSA-signed
  (signing them retroactively would backdate a signature; the cutover report is the honest record).
- KB_18 wishlist (Policy DSL / MAC / PII filter / ISO 42005) = G-028/G-029/G-030, a later governance stage.
- G-021 (deep live message-cascade/latency UI) is partially served by the new spans; the deep UI render stays frontend work.

## References
- `scripts/{generate-annex-iv-doc,verify-audit-chain,back-sign-legacy-rows}.py` · `compliance/{ai-policy.md,annex-iv-packs/}`
  · `backend/alembic/versions/0008_mem0_rls.py` · `backend/a2a/server.py` · `backend/agents/runtime/nodes.py` ·
  `backend/memory/mem0_adapter.py` · `.github/workflows/ci.yml`. KB_18/15/14/13. Research §29. EU AI Act Art-11/Annex IV.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T18:08:28+00:00 -->
<!-- signature: I1vJvGg5IZXVgNkNotwYFZqI0O6zvLKx+tOWLvx8nMZ04R4FGx38vDDCyh/LnoNmIC+/GQTp1y1nM0JJStsQLoB+DRTThHigRMpjGi641Vxkfq49C0HrfkR7X5VINoao+ERVRdCtjeURZLYVOZ41XDsljn+QQVT6qoHZZjDQX0nY3yO5mOe3h0niqhg0+fs2kxf0/k/XBJS3HX3OA9A/SASS7tBJ3SOaCEsg8KGH8vS8rMjye2pM4tt/U7LdachyvFXxC20IiGZJUOhoR/Qw3YsTKWfEQRlsMlBeMFvj/GXMdqyJNDTGj7UZqAVECSz9bO0YGHNu197p2fmy1TvbeZ4EnZRG9aL0y7VCWoR72Mr+LHYBvRceSsgsZUb08PIBfGEPS0fiIGD9bwZXru+rpv0HDj/cQXGNrUbi1lX8faT9H6owFRUUdApPHSjPICsQbQeSXh4NTLOx+DduMHimCHgegoeQIGD1rAKqCzc3HHZYy/Pjf+gYdEjcMLuK36wyN2BAga5ofeqXs1bzmHxJByWb2ZKyGEEXiu5PkuROd6LT4c6iS71fqOesUrFafwuztI4EZMw7RcEaaODIRHrFoRRJCGQM/ahMnXlGxWWLqAIGtLavgtMee9r5XhZBNa1pBrmQg1Dx3fMtkkL5JDlaf/Fxiqi5oESLyEweDjATjoNLbD6pL03zrGxxL+eKhBeT5HqrhrQrlFoHcqXzJGJfRseW1juDeSnTbuOIXaXIsmV5uukaxyHsOpNyqjM5wJ0mjkgsQNFsM29F1FHf116hAD6oScPgUgwQMYMa7r+z0XkFmrHRpi7GafCGZ8I7XaGZR9pMmQmYYtnKolkK1DBv/IVZnjLr/vDdn3dhU+O2zR+P7mdZJdYPFYIa2HHgMmKOhjD0OTiFd523i7RbnSKMVAadUq+D52/H/qqNTve7gBBKSy0LQs17hwmKaJ2naXmtIRjTEu5Emxy7P5M4T1XElqtXGZbtH+ByA2UNCtOt4Z9PtUlaN/FMzMeTvLeh4hB4MaDfkKvsgUpxnyNLH8NcWgCW8zt/qO3eWHV+m1EryG4EHROTJxQ8naYjOM+T3wjUS9lgte+OqwGUsj+cvy+q/7PuG9nyqVXVryXoiMfd+drKSO6hjWL9oJhu+IzMJ0g0ucwnAv3PVcjoBcVk8M8fEIl2jn0KhflD53hFxxMhEjYssYke4/RJFtAmVvatxIb2zXStMk5srIvgsE7yG0kIH0iVDCG1zejWFKHDV++AmQ8goGXvGknPxbND38dSUduF2EZ/XeUPYXmdWIXwDx1y3Jfy7uPs5nf6yZJkCvzvVWnJfkCkui3nPVj+drNUg28Hs2AmlLc4y6WA4tY1fCbhN6e7wCuYjrAW7Bm4b7UHmcwt2QBBIc9lrt00Rkgb9+0oOjjKtyXdCpo1jIur0pCoVLFBnvOefP+bWbH4dreiWj8JpstH1lcG6r0JXS1+4B04pQjsyLIf6lU9kHRC5GaSKokFn64DiAEVFiOSiXBrSY3eJyuC7JTbtKl8rQf3tZ3wf1w40Rp8rgZw1VblyWazoaq6w6M4I7wdb9dh9jvF7QcNnNl3JlZVpKCaCDjvnkObtBBHsAl/cAxKRZgwA5OdBgJWVI8WI3T9IzivW7/ZXi7TCZwZk/eo2F2EfX2oEsbxd+eJRQixUZR1a517VQRD3UrSRYCmHlrgIC8G8qi1/zHAaZ8ZGgz7aXFzgBDDlqZXQImOCXi9w+J2ofnfopxBJBARiOG1CAyTdsP7zeXgcenCL0IJ8TtlOk0FTzcjMwso7SL4dDuEpBQ3DKlLpYubYHmDpw2FHiXCKcYS0pNiP7HTaDLCyEG4Pm4JSXLDm9/gIpgQ2/W7aW64MJ/JArkzX2qZOjZlDFbAVWOe+DSQs58Tn0Y0bHVYiyD8stmQ31nROnGy1GJpJ3/MUOuAAqJ8OcXwDKm1xYK3LXBs6cd1ri3/jzUk9jEwbnHVNknVy8aFo9HTk4ZOvrQOFB1wLsr0Qb7vzzXEJcSkKdM5umyFK//ClkOPf9YgbmMoozKwcy6fBEQ6xGgqK0w61sFZXRCqGS6vEz+cMMc98iP0l2JvJI1AxEG1S7zQPQT0YWtjOnjaCSmwtkJvxrxKez80rT+gGrJyYfJau+zWGjcRW+uv8pinMpROvPziuy6SJDL1rXdfPHT5Hnq/qmp9FzIu9Ur6oQJCqHt6T2aH/lAVz20tMvAYqhW0DeQXgKp0KTiBWzBbm5AttWcUMS9WJF5tVga+UPm2jkk3N185XfScc/Lw59X0C8/8qVwk6trjasdopSw5+d4MzN80LodyC8OFONJYqQx+PYGocqaNdOpH4sIPRTj5AGv8bwix3PVZwiwHkibf3bAgjYniMF7QEHUwYGxh8z83w9Bye7s/tHe1ysAt5FuPWHXu4ZFgIblcURqf6WzVm3gcXqc/ez7Fnyn2k6S0qS7gZxZNFLrACC+tJDv3/NVJgzl9Kc+9f3e5RbVNPBpLKdo7gQaHLnMe5iJMwHpcPTZZHuYloPyHff6Yr+QNp0KXbooIMI26qvAjQKqfiS+ModUlVU+Fuamat1IaV/CJ8hYP5P4Hyw5itFvuQH/cNTJ4u61PEBQpDtLpls1U7ESp813tMNH3jpP4+qSWMw1LLJN9FLb2gFrMT8QewGIWkHwEeIDNs+14ZBvBuflZ7snPnME7m7+6ADo7VQ/ORd+cwJgU5pmexrwSB25r+lzOOrCr9kvXI4eiNS+auq46E25/YzoMQBzkzavox0H1kA7xufDmCXy7LJ4KPNDHN6VifnIpgx+wpP0m4fsvhTYVkL7HV2Fl0jMCjikQ+I/Rms5FGjnaUldokZjv+54ZPE+N+koWJAQ5gATbSr9JUxqlPZHqVYrB34s8ucdYjx3m38slNwCrpWvNzIodd8MTar2Xz4j1nv2YdW1B5PYYRV4anD9/u4JCOFRI5nWJ1+bXk7bQrEXAFD6w7IjIWM6x1xD/sH7QXY98av0P0W42G+UenjuVoz6V0R3Bp47xhEhPNMa5CHPSaVeWVorKeFvg5k1hfJRi0x1BqDlXgcQrZcpx975A5Yk1531RV+dXR74Bwcf/11/B3NJpYbQZHoH3nF/6hp4d9fjaJnAK7ogU1aZeX1WnfJvVnbDtBzberQ0fThUB2nMQ1fRTtqw9uJ9dEQ5yim5Y9Dv0HGC3prew2UfZPu5OA4ykergOsIzWUJ6U2CvbHkW5KguBlafqoP7OFAycuNx2falKwcnjIp+Me/sqX4vtzODHiAw3+OYraW8a0DXxIBS4yfNyWlsISQeLx/teWl/+Xb7i/Woj4afH0YYRTjlhg5d7LF1VIU2KDm21XBu+ghrtGDe5CWO3Cei/0TpFdQU01T3MlF3lQbpce8NXQpBVi/3epVbwv9LJREniG+2i5x//MIeR6kX1wXJ+fN85f3jYV7fUENMJocwzh/0GgeE2EeA6lxeroVDuBXEvWa9wKMEBU82bJDCSyD/BfIk7d13Sen7gAs1SQ37fFUKd4Gb0CcQXc2oAs0hd+jl7nE+oM50gB7f1I/FrT275xe92ySsHgWZclLgW4HZpQi32qTlJwLXNwoz7819nZpoQEB/V7roBJdt+sAcdrJMS4GD/IuDAnf8GhVuOJoZdsa1Wt7TaGas0nazjVnqQmG3WwVg9coDLZozsuhO0d8VjN7E4Y8PCL3l6HO9CAcASZDY8fX41DK1JYjgBkZRKbP93xqxc956jAEKtToQgDYfat+8qeAWHVsb/e+10k1dxtLl2p6j/9E7I71F8u9isQsHpONnRVkgbM+rlflzH3LsOxNRKkKKL1LfUT6PYY0MeBCf+Xk1qEWjVwqUOGbSeVcR2K9jalVQuhRkXmZMek2w5W8dBN8obWx0MkfYY7zwkxHypmUql/OZHH6wp4pKCp0Uhx84SbSJtKgJ2SYizEQ8MRKlZ2yH1xGKsr7BxaHz9u7Umhxsux2LAMqynC3BRVo8EPmTlG9MTS3XHb3oKazv/lQZRYhzyUdznODs4mP4OWTQnyKWeBYBGSiTeOQVci3Bz+224JOz0bYJAXQeayW8ObLweohXR190VZIKPtxdePnhOC9iE/KTpFO9vWmvxjSujPgNVqJp2zu6CPrxQMblhLCs6BF/gPm0tDUykmtR9gfJv6vHEQ1F/jn4u8D6UHM32wOWszOicGCW6KkEOoGtIqR+aMwU/o+4pCytv4BZyZji9Sr9HP3HUvk1FsefBhja5HfrSnUuaB/fu6kGLnGwjghcws52VrYSvb1TUY7eBieBSIpLfuS+jdoaSgLfM7BsI3gZW6Yq+U+gxYm+Xmx92bA7dYyoOHh89baH0MGVmfZKlBFOVxOsJDlBmttkAIC9KVllqp7nQAzI6d64AAAAAAAAAAAAAAAAAAAAABw0SGCIn -->
