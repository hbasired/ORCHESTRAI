# ADR — Stage 14: A2A protocol surface (signed agent cards + JSON-RPC federation)

**Date**: 2026-06-15
**Status**: Accepted (Stage 14 — follows Stage 13.5 `2026-06-15_stage13_5_pqc_foundations.md`)
**Author personas**: `security-pqc-engineer` (primary) + `backend-engineer`
**Relates**: KB_16 (A2A/MCP contract), KB_13 (PQC). Research §24. Follows Hard Rule 1a (real signatures, honest
deferrals), Rule 9 (free/local), Rule 11 (research-first), Rule 2 (ML-DSA-65 signing, no classical). Begins paying
the zero-trust agent-identity work (G-064): agents now have ML-DSA-65 non-human identities (signed cards).

---

## Context

Stage 13.5 gave us a real ML-DSA-65 signer. Stage 14 builds the **external** agent-to-agent boundary (KB_16): a
signed **agent card** for discovery, a **JSON-RPC 2.0** capability endpoint, pinned-root + revocation trust, and a
peer state machine — the horizontal federation surface, deliberately separate from the internal MCP tool surface.

## Decisions

**D1 — Hand-roll the real A2A wire format, NOT a2a-sdk (research §24).** A2A is the Linux-Foundation standard (agent
cards + JSON-RPC 2.0; complementary to MCP). `a2a-sdk` 1.1.0 requires **httpx≥0.28.1** but our stack is pinned
**httpx 0.27.2** (shared by fastapi/starlette/mcp/langfuse — the same version-skew that bit langchain-mcp-adapters/mcp
this build) and it pulls google-api-core/protobuf. Our agent card is also **PQC-specific** (ML-DSA-65 public key,
`supported_kems`/`supported_signatures`, JCS-canonicalised signature). So we hand-roll a genuinely A2A-conformant
surface (KB_16's documented fallback) with our real Stage-13.5 ML-DSA-65 card signing — full control, no httpx churn,
no extra footprint. `a2a-sdk` adoption ledgered (G-070) for when the httpx pin is bumped.

**D2 — Signed agent card + JSON-RPC trust boundary.** `a2a/agent_card.py` (the KB_16 schema; `sign_card` sets the
ML-DSA-65 public key + signs the **JCS RFC-8785** canonical card-minus-signature; `verify_card` checks revocation →
expiry → signature → pinned-roots — any failure returns False, never a partial trust decision). `a2a/server.py`:
`GET /.well-known/agent.json` (signed card) + `POST /a2a/v1/rpc` (JSON-RPC 2.0). **The trust asymmetry is enforced
+ tested:** the dispatch serves ONLY `a2a.skills.SKILLS` (the deliberate capability subset, e.g. `forecast_oee` →
real OEE); a method that is an MCP tool (`predict_failure`) returns JSON-RPC `-32601` — external peers reach
capabilities, NEVER the MCP tools (KB_16).

**D3 — Revocation + peer state.** `a2a/revocation.py` (5-min poller; fail-safe — an unreachable list keeps the last
cached set, never clears a known-revoked key; bounded-thread shutdown — the Stage-11/13 lesson). `a2a/peer_state.py`
(active/quarantine/revoked; only ACTIVE peers may call). Migration `0007_a2a_peers` persists peers + last cards.

**D4 — Hybrid TLS is Stage 18, honestly deferred.** Per KB_13's matrix the ML-KEM-768+X25519 mTLS sidecar is Stage 18
(PQC Wave 2). `a2a/transport_tls.py` + `docker-compose.pqc.yml` are the sidecar scaffold/config; the live PQC TLS is
NOT claimed running (`transport_tls.status()['live_pqc_tls'] = False`). The two-instance Docker federation
(`docker-compose.a2a.yml`) is provided but Docker-gated (host Docker down — G-069); the in-process two-identity
federation proves the logic infra-free.

## Why
- A2A gives our agents real **non-human identities** (signed cards) — the foundation of the zero-trust posture
  (G-064) and the federation use cases (a customer MES querying `forecast_oee`; KB_16). The trust asymmetry
  (capabilities, not tools) is the security property that makes federation safe — so it is enforced + tested, not
  assumed. Hand-rolling keeps the frozen runtime pins intact while shipping a conformant, PQC-signed surface.

## Consequences
- New: `backend/a2a/` (`__init__,agent_card,server,revocation,peer_state,transport_tls` + `skills/{__init__,
  forecast_oee}`), `backend/alembic/versions/0007_a2a_peers.py`, `backend/tests/a2a/` (3 files, 9 tests), the
  `a2a-conformance` CI job, `docker/docker-compose.{pqc,a2a}.yml`, this ADR, the explainer, KB_TASK_LOG entry, ledger
  G-070. Modified: `main.py` (mount the A2A router), KB_16/KB_13, risk-register. **No new dependencies** (hand-rolled;
  `jcs` already present from Stage 13.5).
- Verified (infra-free — A2A crypto needs no Docker): **9 A2A tests pass / 1 skipped** (card sign/verify/tamper/
  expiry/revoke/pinned-roots; two-identity in-process federation [distinct keys → exchange → verify → revoke]; the
  served card is genuinely ML-DSA-65 verifiable; JSON-RPC exposes the capability but refuses the MCP tool). `main.py`
  imports cleanly with the routes mounted. Audit holds **364** (real crypto + JSON-RPC, no grep-counted theatre).

## Honest residual / ledger
- **G-070** — adopt `a2a-sdk` when the httpx pin is bumped (the hand-rolled surface is conformant in the meantime).
- Hybrid ML-KEM-768 mTLS sidecar = Stage 18 (KB_13); the two-instance Docker federation run = when Docker is up (G-069).
- Live mTLS client-identity → `peer_state` binding lands with the Stage-18 sidecar (the header-based gate is wired now).

## References
- `backend/a2a/*.py` · `backend/a2a/skills/*` · `backend/tests/a2a/*` · `backend/alembic/versions/0007_a2a_peers.py`
  · `backend/main.py` · `docker/docker-compose.{pqc,a2a}.yml` · `.github/workflows/ci.yml` (a2a-conformance).
  KB_16/13. Research §24.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:31+00:00 -->
<!-- signature: /zm9AgK7HYzBCx+H72Qd+dqe1EDmw1ZWvDFClEgFmqbxJdGPPRSZgsSoSWBB+pLdTtqewbEopSolt4lCJpp6G4W9GXPVoQn6gXwhsEEE+0GVdS34AYiMhDvsXBzyeaaE2mvnbm81AEuL8hdkyssNVAOO2ZYaSudbmI60HyO2Z7VVV5QdXBjSbCMMuiIVK1Hh+SHRQDi+hn3J6AoMpakrTQ7mwJHrxCL79wqJc3brufsIC6u6SuECd+AUF1q7MSHfW/vOEy82pTKjPJ6ntFfa6Sbi1Kr76h/9K270m5y+/4OAmVadSRisCXqgV5iMzONniSf/YfEIH28pJWX6qosizU/7maUaQxs8wNpAk7Z5q+BfhVJ8WKgauoldQyw+G7JI177bqG4sDfMKefR4ydlQT7Shr6A2XWmKjFp3dUddqmV6yYq8QvRErIdPNfqoA/OHOZ4yKCVuRdGx9e0G7LL6qtWjZfTfiSdWJRe3pxJ5zBagrXxlYuuOLHdfKYqHrY64t2GdszamM4wi1MJmd76rcZT8Klx1ei7qwXbtbvIpQ0JR9eJFPTr37ul9tyl5N1LOV8zVfWQ7ikAlvXsspy5ykafmFA2sqQ8Hqtb9sKmfiyi4q9hjha4UDQ/qeFvjJ8CGoW0aQNSIZrdSi7atv5T3CNZoR5Os4CdWX8syWmm/rBoIUozJ9A3f6BKs2sosoMCQ4HMlUl78CRMRIwUV5rKczHP6k4c10klsoO9wJljLlpxYVhkDY/Ad/6VeC4WRr+mZlAhWp7K46baHKI5Zm9zxTy1ZsdTi9ileMc9HnzvmJO4N0dgqMKjnBluCdH8/QD6HJ78kX20Dr1VuhhQmbjsIqJDqzPdWNn7yMEMKpF45FmkSsjFwLv4uWQfaoTWCwPNtUGEIsuSlwCH1WVKE6e5tulduxg0txcNNZ9wfCrO66jXf2dCc2Dbk7reRq+nfbGwAKcOs+Gw9nSA2xGg6HApFkmuZGfWRHm6JGcGppcXhruJIjD1w+VJgRcO6uxuQWsruqwevHt9IRuq/JCG5P2zwMRPb5If1OY443YuydPzghh94OAZ9O9ZVYBlWKxaOrC3I2hAqhz31SmEX5DwRUKetc/ckeAlHygujs3F3t5RM3csKw7LGQFdu8L2eI+PiR1R2zwk2vVJkgBhNeVPL5sFaB+21CyC5KaFWUMSvopf4LUFuXCzKqfNkEhhGWjB67InblDeBXeW5+Dt1CRIkwQWBgkM+r70W+C0eITPFjP5Z6ZyaganjdVBwSqjXu6CHGbxKO1blroK+0rY9pK6jlbqLGHxA9zgT/c3Nl8nE/4JeZgLCxY1LG7xPAobJOJogQ9k2o0/b9IWR44VU90me9ljHWMUJbh1ktyiHIPwfDVC3y/Qar4sJwXEECE/rqgbPio4Q76d1A8CrZsz/sgFeZCPa011xaGkfjT8MGU0uNw7BaIX4sedcNlkHlcxW5UzdrogYT7QYyWsfOGKwxloAJR+cA/T4uf/DgApMPf0BTQtJqcZtwPvCQ53Qy9EVZw8ddxpoz3mMXON/W9TE1gRxpg2MtIPhD1dlwFnvNigtunSxj66HLGKiVc5HSOjAlDhTS1PFyRDuvwgRdHR4N+IgciJb2INDRnm+D4f+z9vPOu9oTSiyaNQ6tZo3bVYu6NN0g5CJI4848tMcofZyb/cxETtGlxNCIixPC+zN+voUiM7BTpSklQdGCQV9Hr1Cd5iAA6tgJepfdli2J7NmrXKBV2zXKFGOBtlaIjq7HrXqWLUDsoHm2B1tmCK5SfVAKiefoubr8ygwC6P4EU6X0Mp2ZIAJToQlS3w0qAV8Yjq5M06LqCJ4/19QyXTl6CY3GXdOM++VxKFRAfemenpexZUh+l8KLesTJTjlCTy37tZe/+Uvw8keu5q2R8m0JKQA3+WKuDJcKbrDygeh6JND2cZgUO0W8ZLB2rlU9XlA15/8xJXc8ENPdnFMeamoHXnBgIRg/VLLES25SVc/qZepD1c68N/xX+nK9Zx/OLvGzobWojefFpoXuEjDVGEhALL3UiTXEfZTzAuFnjXiwTEHmJtLxv4rCrt1FPnk0X1MTYNDZ+3mW0jQ4kK6x5ph4BPhAfr41kRGylI7mZMHaGHb3a58DoNKItpaCSRh2Qe28d1ptBJx4W1TIis659qNlFbL1I4N9/I4zXrbuhu2wU9MT00UNF6yaYI7MQoIUHnAElM8j2ue72my1GrUfpq77nakjhvoQxSuIgD2zfDZETcaT0YtBDFYVu9sq5fho0L9QryLG7VAoyxs98YSFBONpCiFW+xL+gg0DzLjSZ5u0axGXLB0su/T0JfWS55JGEl8YTxn2yPDDcMVtqEVB8aCXPVMqhb6utv0GF+dpJPgcYy0rPWlYV9+aIUSjpciaYUlFI7ejQSzyACfnU6HG9GFt0a9rcu2b+B5sH+/uIhPgXRLpWC2+fX2+DDg1++YWy+6dsjgc/rSNz05q46fyOA9yF76f1fmSvvfOjELcxZ3AeF7SG0FpZ5sl/P0aPA+S3igWBMUXgBBfE6tB3niSm4VkLlLZgLOlTlnH/IyX9iM+nD64iXRYyI7BoyBJImz4hORHnLydAoqfZGAbYWjNfOk39Tqrb9qui7Kg7AHk7JHSj/BbjcZwqj1S6DuEtTo90c+zx6p/8AXhewVLivLsZ12FvFngkTud6is/2fQYS9fRK7rhu6ahEFs94sQe+dbxoy8ZIfELMT8yA56jJs2skEvsftPaSGwj5TIOhblgvZgCLAjg37ptXwT6sh0A3lVdL4F/6MQ0yYMN/X01TtMLF/xTSZfrDkIH8owE1zJyrfrtZVqEPX3CHkf55Y3d/oP0crb4dP/G8nfZ23Oq08IHW901LYN7B90Cxy2573Z4LFOuljuBSHZ64/SH5MPIumWIbOp31yCSrytXKrlXcbcOXmW51+Jo+j8UlnBmAiZsUuHo989QWzjZe8PTBz4tp1snLWwS+ZRis1Eg1cbDYXojyVETS3Chk4ZpjRNrdIcyqoQr3/LK8IwCRLJXZVXV2xPOjxTofkDEAzxuCRZ0shkqnXTydvVn8dqHO3p01E1fZWMihjHHR/Ow9MiKQeS5FKkQGtgpQqBtBii+Jh4bmyB7SFARFb2CPVb9pWThEXruIuxTNNZU/UugVYOMaWQO2FUAbuaHy0/fOBbuwyjqMffE7uWerB9JP2mAsCECf0Y42nmptnmb3nWG7DPw+JDb7+LlVrvqUq9wfGwNQSyxCoVuyGuQXhDrOjtEfguGO3iEXULSUipVIzTBUd3huUN0eFniXdsHKobr/8SdRKy4aw9Y1u+jAk4UKfsN3gt/xkvYkutUgSfYPTZ+tHrGsLaOlbDpiwFPh41VO3SIpNgJ6U2YtIjaDXCyoD+lrg8JlXtRELkVXQRSCcpkpDKz+B1bcsnq9+uwLUentXfM/GjM/vyCsJBOkZZH1ynIBi+KObyKf+R9qEdb8bdyQApEoINmC7o84zIvOr7bTX6vXIl4y3RlSK5LA6Py9XxYsMgXG0KeSEmj6OQq3QJ7/rDG/smGIbaqWnaWzeFco1/HWB4HK2Gj8qfyAvjKogqlEVPpFO3uhVTfqUpJQxaxxSfp8jSCmaok7FvU622IXhObYAikbARuEwmoxvWnveXNH5546V0ssu+JEjV2CZ+fq0pay44arK5djaYw2186ILIGuuORmyz/DcFpNwezFl+JLw+eYWPmDAex9OmC7Yh9BL1b3WT+Lupl+DC1gCVkuJfHN6JGQoHV7NrFE5mzdOxHJxUpFlJXyjEKZiChwrnMfVhM5P3qQu4IXE0xBynw8J7Umhy9BK/zl8x1B7Gksb4dBK+2ITsXAtUZHqmdW/nKv7rApQpN7llpwGVVh8f0s8GyVE3kNLGnUS+2ugewp50StldGejP26wdJ4s51ZAd3HRr89ASRwRIE/QRL5mRs3c26JCBqOK678oc6Bo1Uj9G18Ch+KE1vQ3sYmCHcYwXQ/WpF9PUNwYnUz4yASeb6/9TyoHk2gx6nl8SRce7lSJ3hs7AeYqGAc+0vAZFMM3XINLGvkgNbeh8vBVszHVYUHvNzHimYOMsuau1mfZ0vYITrxeESIJgsDea7vFtHdG0ktc3zl5FtWXSsEREvgmiVai1GzkK7hPCahv/2+T9SVanyeNI1MPDUHPqZgiJrYExtsSVJyxZTrNHqQ5mwasQyJaoMA6gzdgdAo+5HAh8FWx/1Pu/YTHuBg+7/7yCEc63aHQZap/Wqh/UcleU1NAQ098GfY1JPCMtsKvUjnSUifKtU83Owr/arB/Utt0S4wWsCawG9bOX2k0poM+mpx1kmuUImxkMNXvBxOkJHVNn0CUwNlRYY3uju83R9/waY5qbpMMGekRRU2jNAAAAAAAAAAAAAAAAAAAAAAAABgsYHiAl -->
