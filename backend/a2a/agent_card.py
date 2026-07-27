"""Stage 14 — the A2A agent card: Pydantic model + ML-DSA-65 sign/verify (KB_16 §"Agent card shape").

The card is the discovery + trust artefact: it declares the capabilities we expose over A2A (a deliberate subset,
NOT the MCP tool surface), our ML-DSA-65 public key, supported algorithms, and an expiry — all covered by an
ML-DSA-65 `signature_b64` over the **JCS-canonicalised** (RFC 8785) card minus the signature field. Signed by the
Stage-13.5 KeyProvider (`agent-identity` key). `verify_card()` checks the revocation list THEN the signature against
the card's public key (and, when given, that the key is a pinned root).
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import jcs
from pydantic import BaseModel, Field


class AgentCard(BaseModel):
    """KB_16 agent-card schema. `signature_b64` covers JCS(card minus signature_b64)."""
    name: str
    version: str
    capabilities: list[str]                                   # A2A-exposed skills (subset; NOT MCP tools)
    endpoints: dict[str, str]                                 # protocol -> URL
    public_key_b64: str = ""                                  # ML-DSA-65 public key (base64); set by sign_card
    supported_kems: list[str] = Field(default_factory=lambda: ["ML-KEM-768+X25519", "X25519"])
    supported_signatures: list[str] = Field(default_factory=lambda: ["ML-DSA-65"])
    supported_protocols: list[str] = Field(default_factory=lambda: ["a2a/1.0"])
    provenance: dict[str, str] = Field(default_factory=dict)  # build info, git SHA, model refs
    expiry: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revocation_list_url: Optional[str] = None
    signature_b64: str = ""                                   # ML-DSA-65 signature (base64)

    def signing_payload(self) -> bytes:
        """JCS-canonicalised JSON of the card MINUS the signature field — the exact bytes that get signed/verified."""
        data = self.model_dump(mode="json")
        data.pop("signature_b64", None)
        return jcs.canonicalize(data)


def sign_card(card: AgentCard) -> AgentCard:
    """Set the card's public key (the agent-identity ML-DSA-65 key) + sign the canonical payload. Returns the card."""
    from crypto import pqc_signing
    card.public_key_b64 = base64.b64encode(pqc_signing.public_key()).decode("ascii")
    card.signature_b64 = base64.b64encode(pqc_signing.sign(card.signing_payload())).decode("ascii")
    return card


def verify_card(card: AgentCard, *, pinned_roots: Optional[set[str]] = None,
                is_revoked: Optional[Callable[[str], bool]] = None,
                now: Optional[datetime] = None) -> bool:
    """Verify a peer's card: (1) not revoked, (2) not expired, (3) ML-DSA-65 signature valid under its public key,
    (4) — when `pinned_roots` is given — the public key is pinned. Honest: any failure returns False (no exceptions
    leak a partial trust decision)."""
    try:
        if not card.public_key_b64 or not card.signature_b64:
            return False
        if is_revoked is not None and is_revoked(card.public_key_b64):
            return False
        if pinned_roots is not None and card.public_key_b64 not in pinned_roots:
            return False
        ref = now or datetime.now(timezone.utc)
        expiry = card.expiry if card.expiry.tzinfo else card.expiry.replace(tzinfo=timezone.utc)
        if expiry < ref:
            return False
        from crypto import pqc_signing
        pub = base64.b64decode(card.public_key_b64)
        sig = base64.b64decode(card.signature_b64)
        return pqc_signing.verify(card.signing_payload(), sig, pub)
    except Exception:  # noqa: BLE001 - a malformed card is an untrusted card, not a crash
        return False


__all__ = ["AgentCard", "sign_card", "verify_card"]
