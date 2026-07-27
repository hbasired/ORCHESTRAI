"""Stage 27 — Kagenti/kagent-compatible AgentCard export (research §35.1/§38.2).

Kagenti (github.com/kagenti) indexes agents via **AgentCard CRDs**; the A2A spec (LF) defines a JSON AgentCard at
`/.well-known/agent-card.json`. This module re-shapes OUR native `AgentCard` (KB_16, ML-DSA-65-signed) into both
external shapes so our agent can be discovered/orchestrated INSIDE a CNCF agent platform or IBM watsonx Orchestrate
(the channel-fit play) — WITHOUT abandoning our evidence spine:

  * the A2A-spec AgentCard JSON (name/description/url/version/skills/securitySchemes);
  * a Kagenti-style AgentCard-CRD dict (apiVersion/kind/spec) referencing the SPIFFE workload identity.

The DUAL IDENTITY is surfaced explicitly: `spiffe_id` (transport auth) + `ml_dsa_public_key_b64` (evidence signing).
A consumer verifies transport identity via the SVID (mesh mTLS) AND evidence signatures via the ML-DSA key — and
this export proves they belong to the same agent (both carried in one signed card).

Honest: this is an EXPORT/interop shaper, not a running Kagenti deployment (that needs a K8s cluster + the Kagenti
operator — pilot-scale). The shapes are spec-faithful; deploying them into a live mesh is the deployment step.
"""
from __future__ import annotations

from typing import Any, Optional

from a2a.agent_card import AgentCard


def to_a2a_spec_card(card: AgentCard, *, description: str = "") -> dict[str, Any]:
    """The LF A2A-spec AgentCard JSON shape (served at /.well-known/agent-card.json for A2A-native discovery)."""
    return {
        "protocolVersion": "0.3.0",
        "name": card.name,
        "description": description or f"{card.name} — vendor-neutral industrial agent control plane",
        "url": card.endpoints.get("a2a", ""),
        "version": card.version,
        "preferredTransport": "JSONRPC",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {"id": cap, "name": cap, "description": f"A2A capability: {cap}",
             "tags": ["industrial", "self-healing"]}
            for cap in card.capabilities
        ],
        "securitySchemes": {
            "spiffe-mtls": {"type": "mutualTLS", "description": "SPIFFE X509-SVID client certificate"},
        },
        "security": [{"spiffe-mtls": []}],
        # Our evidence spine, surfaced as signed extensions (a plain A2A consumer ignores unknown fields):
        "signatures": [{"algorithm": "ML-DSA-65", "keyId": "agent-identity",
                        "publicKey": card.public_key_b64, "value": card.signature_b64}],
    }


def to_kagenti_crd(card: AgentCard, *, spiffe_id: Optional[str] = None,
                   namespace: str = "ai-agent") -> dict[str, Any]:
    """A Kagenti-style AgentCard Custom Resource (indexable by the Kagenti operator).

    Binds the DUAL identity: `spiffeId` (SPIRE workload identity, transport auth) + the ML-DSA-65 evidence key.
    `spiffe_id` defaults to the trust-domain-scoped id for this agent's A2A server workload."""
    from security.spiffe_identity import TRUST_DOMAIN
    sid = spiffe_id or f"spiffe://{TRUST_DOMAIN}/a2a-server"
    return {
        "apiVersion": "kagenti.operator.dev/v1alpha1",
        "kind": "Agent",
        "metadata": {"name": card.name.lower().replace(" ", "-"), "namespace": namespace,
                     "labels": {"app.kubernetes.io/managed-by": "ai-embodied-agent",
                                "kagenti.dev/protocol": "a2a"}},
        "spec": {
            "description": f"{card.name} v{card.version}",
            "protocols": card.supported_protocols,
            "endpoint": card.endpoints.get("a2a", ""),
            "skills": card.capabilities,
            "identity": {
                # Dual-identity binding — transport (SPIFFE) + evidence (ML-DSA-65):
                "spiffeId": sid,
                "evidenceSignature": {"algorithm": "ML-DSA-65", "publicKey": card.public_key_b64},
            },
            "security": {"transport": "spiffe-mtls", "cardSignature": card.signature_b64},
        },
    }


__all__ = ["to_a2a_spec_card", "to_kagenti_crd"]
