"""Stage 17 — agentic zero-trust (CTO #3 G-063/G-064; NIST SP 800-207 + CSA Agentic Trust; research §27.2).

- `zero_trust.py` — adopts NIST SP 800-207 as the named framework; maps its 5 pillars to this agentic system.
- `agent_identity.py` — a verified, auditable **per-internal-agent ML-DSA-65 non-human identity** (who owns it, its
  purpose, its granted capabilities) — extends the single Stage-13.5 `agent-identity` alias to per-agent aliases.
- `tool_manifest.py` — an ML-DSA-65-signed MCP tool manifest (a rogue/injected tool is detected).
- `mcp_authz.py` — per-tool capability authorization + argument sanitisation + rate-limiting (least privilege).

The A2A interim `X-A2A-Peer-Key` gate → real mTLS-client-cert→peer_state binding lands with the Stage-18 hybrid-TLS
sidecar (KB_13) — honestly deferred.
"""
