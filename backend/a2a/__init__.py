"""Stage 14 — A2A (agent-to-agent) external federation boundary (KB_16).

The horizontal boundary: external agents discover us via a **signed agent card** (`/.well-known/agent.json`) and call
a **deliberate capability subset** via **JSON-RPC 2.0** (`/a2a/v1/rpc`) — they do NOT get our internal MCP tool
surface. Cards are signed with the Stage-13.5 **ML-DSA-65** KeyProvider; trust = pinned roots + a revocation list.
Hand-rolled per KB_16's documented fallback (a2a-sdk needs httpx>=0.28.1 vs our pinned 0.27.2; research §24). Hybrid
ML-KEM-768 mTLS is Stage 18 (KB_13); this stage ships the card/JSON-RPC/revocation/peer-state/federation layer.
"""
