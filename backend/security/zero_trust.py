"""Stage 17 — adopt a NAMED zero-trust framework + compose the agentic ZT controls (CTO #3 G-063/G-064).

**Framework: NIST SP 800-207 (Zero Trust Architecture)**, extended for agents by the **CSA Agentic Trust Framework**,
**CSA MAESTRO** (threat modelling), and the **OWASP Non-Human-Identity Top-10** (research §27.2). NIST ZT is
"necessary but insufficient" for agentic AI — agents interpret goals, chain tools, retry — so we map its 5 pillars
onto our system and add per-agent identity + continuous tool authorization.

`ZeroTrustGateway` composes the controls into one decision: tool-manifest integrity (no rogue tool) → per-agent
capability authz + argument sanitisation + rate-limiting.
"""
from __future__ import annotations

from typing import Any, Optional

from security.mcp_authz import MCPToolAuthz
from security.tool_manifest import diff_against_live, verify_manifest

FRAMEWORK = "NIST SP 800-207 (+ CSA Agentic Trust Framework / CSA MAESTRO / OWASP NHI Top-10 agentic extension)"

# The 5 NIST SP 800-207 pillars mapped to THIS system (what is live now vs. deferred).
PILLARS: dict[str, dict[str, str]] = {
    "Identity": {
        "nist": "no implicit trust; every subject has a verified identity",
        "ours": "per-internal-agent ML-DSA-65 non-human identity (security/agent_identity.py) + the org agent-identity "
                "key; A2A peers carry ML-DSA-65 signed cards (backend/a2a)",
        "status": "LIVE",
    },
    "Device": {
        "nist": "device/workload posture before access",
        "ours": "container/workload identity; hybrid ML-KEM-768 mTLS host attestation",
        "status": "Stage 18 (PQC Wave 2)",
    },
    "Network": {
        "nist": "encrypt + authenticate all traffic; micro-segmentation",
        "ours": "A2A pinned-root + revocation trust (LIVE); hybrid ML-KEM-768+X25519 mTLS sidecar binding "
                "X-A2A-Peer-Key -> peer_state",
        "status": "PARTIAL — pinned-roots LIVE; live mTLS = Stage 18",
    },
    "Application/Workload": {
        "nist": "least-privilege per-resource authorization, continuous",
        "ours": "MCP tool capability authz + argument sanitisation + rate-limiting (security/mcp_authz.py) + an "
                "ML-DSA-65 signed tool manifest (security/tool_manifest.py)",
        "status": "LIVE",
    },
    "Data": {
        "nist": "classify + protect data; audit access",
        "ours": "append-only SHA-256 hash-chained + ML-DSA-65-signed audit_chain; Mem0 namespace isolation "
                "(cross-namespace reads forbidden)",
        "status": "LIVE",
    },
}


def describe_framework() -> dict:
    return {"framework": FRAMEWORK, "pillars": PILLARS}


class ZeroTrustGateway:
    """One authorization decision for an MCP tool call: manifest integrity → capability authz + sanitisation + rate."""

    def __init__(self, authz: MCPToolAuthz, signed_manifest: dict, *, manifest_alias: Optional[str] = None) -> None:
        self.authz = authz
        self.manifest = signed_manifest
        self.manifest_alias = manifest_alias

    def authorize_tool_call(self, agent_id: str, tool: str, args: Any,
                            live_tools: list[dict]) -> dict:
        # 1. tool-manifest integrity — a tampered manifest OR a rogue (unpinned) tool is refused.
        if not verify_manifest(self.manifest, alias=self.manifest_alias):
            return {"allowed": False, "reason": "tool_manifest signature invalid", "agent_id": agent_id, "tool": tool}
        drift = diff_against_live(self.manifest, live_tools)
        if (tool_server_pair := next((p for p in drift["rogue"] if p[1] == tool), None)) is not None:
            return {"allowed": False, "reason": f"rogue tool not in signed manifest: {tool_server_pair}",
                    "agent_id": agent_id, "tool": tool}
        # 2. least-privilege capability authz + arg sanitisation + rate-limiting.
        d = self.authz.authorize(agent_id, tool, args)
        return {"allowed": d.allowed, "reason": d.reason, "agent_id": agent_id, "tool": tool}


__all__ = ["FRAMEWORK", "PILLARS", "describe_framework", "ZeroTrustGateway"]
