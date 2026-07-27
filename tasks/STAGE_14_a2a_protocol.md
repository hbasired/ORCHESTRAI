---
status: done
stage: 14
slug: a2a_protocol
created: 2026-05-18
---

# Stage 14 — A2A Protocol Surface

> External boundary for agent-to-agent federation. Signed agent cards (ML-DSA-65); ML-KEM-768 + X25519 hybrid mTLS at the oqs-provider sidecar; pinned root trust + revocation list. See KB_16.

## Pre-requisites

- Stage 13.5 closed (ML-DSA-65 signer available).

## Acceptance criteria

- [ ] `backend/a2a/server.py` mounts `/.well-known/agent.json` (signed agent card) and `/a2a/v1/rpc` (JSON-RPC dispatch).
- [ ] `backend/a2a/agent_card.py` defines the Pydantic agent card model; `sign_card()` / `verify_card()` work end-to-end.
- [ ] `backend/a2a/transport_tls.py` configures the oqs-provider sidecar (haproxy / stunnel) for ML-KEM-768 + X25519 hybrid mTLS.
- [ ] `backend/a2a/revocation.py` polls a configurable URL on a 5-min cycle.
- [ ] `docker/docker-compose.a2a.yml` runs two instances for federation testing.
- [ ] `backend/tests/a2a/test_federation.py` — two instances fetch each other's cards, verify signatures, invoke a capability, revoke, re-verify.
- [ ] CI gate `a2a-conformance` runs on every PR.
- [ ] Alembic `0004_a2a_peers.py` creates peer + agent-card storage.
- [ ] `KB_16_A2A_MCP_Protocols.md` agent card schema matches code.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/a2a/__init__.py` | Package marker |
| `backend/a2a/server.py` | FastAPI mount points |
| `backend/a2a/agent_card.py` | Pydantic model + sign/verify |
| `backend/a2a/transport_tls.py` | Sidecar config helpers |
| `backend/a2a/revocation.py` | Revocation list poller |
| `backend/a2a/peer_state.py` | Peer state machine (active / quarantine / revoked) |
| `backend/a2a/skills/<name>.py` | One file per A2A-exposed capability (request_pickup_window, etc.) |
| `backend/alembic/versions/0004_a2a_peers.py` | Peers + cards storage |
| `docker/docker-compose.a2a.yml` | Federation test peer |
| `docker/docker-compose.pqc.yml` | OpenSSL 3.5 + oqs-provider sidecar |
| `docker/secrets/a2a_roots/` | Pinned root keys directory |
| `backend/tests/a2a/test_federation.py` | End-to-end federation test |
| `backend/tests/a2a/test_agent_card.py` | Sign + verify + tampering tests |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/main.py` | Mount A2A routes |
| `backend/requirements.txt` | Add `a2a-sdk` (Python) — pin version; if SDK lags, hand-roll JSON-RPC server (KB_16 documents fallback) |
| `docker/docker-compose.yml` | Include pqc + a2a overlays |
| `compliance/risk-register.md` | A2A peer compromise row marked implemented |

## KB files this stage updates

- `KB_16_A2A_MCP_Protocols.md`
- `KB_13_PQC_Crypto_Strategy.md` (ML-KEM hybrid TLS first deployment)
- `KB_TASK_LOG.md`

## Verification commands

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.pqc.yml -f docker/docker-compose.a2a.yml up -d
cd backend && pytest tests/a2a/ -v
curl -k https://localhost:8443/.well-known/agent.json | jq .
```

## Audit target

- Strict decrease.

## Role

- Primary: `security-pqc-engineer` + `backend-engineer`

## Risks / unknowns

- `a2a-sdk` Python may not be GA; fallback documented in KB_16.
- oqs-provider sidecar tuning — start with haproxy 2.9+ built against OpenSSL 3.5.

## Hand-off

- What is now true: external agents can federate; trust boundary enforced.
- Next stage (14.5) is CTO Checkpoint #3 — audits Stages 11–14 (runtime + MCP + memory + observability + CDC + PQC + A2A).
