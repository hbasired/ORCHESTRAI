"""Stage 17 — per-internal-agent ML-DSA-65 non-human identity (CTO #3 G-064; NIST SP 800-207 "Identity" pillar).

NIST SP 800-207 + CSA Agentic Trust: every agent must have a **verified, auditable identity** before it accesses any
resource — including the full chain (who owns it, its purpose, the capabilities it claims). Until now only the single
`agent-identity` alias signed ADRs/audit/cards; this issues a DISTINCT ML-DSA-65 key per internal agent (alias
`agent:<id>`) via the Stage-13.5 KeyProvider, so each agent can sign statements provably as itself and be authorised
per-identity. Production swaps the software keystore for HSM/Vault by config (CRYPTO_PROVIDER) — no code change.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Optional

import jcs


def agent_alias(agent_id: str) -> str:
    """KeyProvider alias for an agent identity. `agent:<id>` namespaces it away from `agent-identity` (the org key)."""
    return agent_id if agent_id.startswith("agent:") else f"agent:{agent_id}"


@dataclass
class AgentIdentity:
    agent_id: str
    alias: str
    algorithm: str
    key_version: int
    public_key_b64: str
    owner: str
    purpose: str
    capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"agent_id": self.agent_id, "alias": self.alias, "algorithm": self.algorithm,
                "key_version": self.key_version, "public_key_b64": self.public_key_b64,
                "owner": self.owner, "purpose": self.purpose, "capabilities": sorted(self.capabilities)}


def issue_identity(agent_id: str, *, owner: str, purpose: str,
                   capabilities: Optional[list[str]] = None) -> AgentIdentity:
    """Issue (or load) a per-agent ML-DSA-65 identity. Creates the agent's key on first use (KeyProvider keystore)."""
    from crypto import key_manager
    alias = agent_alias(agent_id)
    key = key_manager.get_signing_key(role=alias)   # creates the keypair if absent
    pub = key["public_key"]                          # raw bytes from the KeyProvider
    pub_b64 = pub if isinstance(pub, str) else base64.b64encode(pub).decode("ascii")
    return AgentIdentity(agent_id=agent_id, alias=alias, algorithm=key["algorithm"],
                         key_version=key["version"], public_key_b64=pub_b64,
                         owner=owner, purpose=purpose, capabilities=sorted(capabilities or []))


def sign_statement(agent_id: str, payload: dict) -> str:
    """The agent signs `payload` AS ITSELF (ML-DSA-65 over JCS-canonical bytes). Returns base64 signature."""
    from crypto import pqc_signing
    sig = pqc_signing.sign(jcs.canonicalize(payload), alias=agent_alias(agent_id))
    return base64.b64encode(sig).decode("ascii")


def verify_statement(public_key_b64: str, payload: dict, signature_b64: str) -> bool:
    """Verify an agent statement against its public key. Any failure → False (no partial trust)."""
    try:
        from crypto import pqc_signing
        return pqc_signing.verify(jcs.canonicalize(payload), base64.b64decode(signature_b64),
                                  base64.b64decode(public_key_b64))
    except Exception:  # noqa: BLE001
        return False


__all__ = ["AgentIdentity", "agent_alias", "issue_identity", "sign_statement", "verify_statement"]
