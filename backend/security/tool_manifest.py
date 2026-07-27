"""Stage 17 — ML-DSA-65-signed MCP tool manifest (CTO #3 G-063; OWASP NHI "tool poisoning" / CSA MAESTRO).

The set of tools an agent may reach is pinned in a manifest signed with ML-DSA-65 (over JCS-canonical bytes). At call
time the live tool catalogue is diffed against the signed manifest — a **rogue/injected tool** (supply-chain or
prompt-injection planted) that is not in the signed manifest is detected + refused. Signed by the org `agent-identity`
key (the same Stage-13.5 signer that signs ADRs/audit/cards).
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any, Optional

import jcs


def build_manifest(tools: list[dict[str, Any]], *, version: str = "1") -> dict:
    """Build an unsigned manifest. Each tool: {server, name} (+ optional inputSchema hash). Order-independent."""
    entries = sorted(({"server": t.get("server", ""), "name": t["name"]} for t in tools),
                     key=lambda e: (e["server"], e["name"]))
    return {"version": version, "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "tools": entries, "signature_b64": ""}


def _payload(manifest: dict) -> bytes:
    m = {k: v for k, v in manifest.items() if k != "signature_b64"}
    return jcs.canonicalize(m)


def sign_manifest(manifest: dict, *, alias: Optional[str] = None) -> dict:
    """Sign the manifest with ML-DSA-65 (org key by default). Returns the manifest with `signature_b64` set."""
    from crypto import pqc_signing
    manifest = dict(manifest)
    manifest["signature_b64"] = base64.b64encode(pqc_signing.sign(_payload(manifest), alias=alias)).decode("ascii")
    return manifest


def verify_manifest(manifest: dict, *, public_key_b64: Optional[str] = None, alias: Optional[str] = None) -> bool:
    """Verify the manifest signature. Provide either the signer's public key or its alias (defaults to the org key)."""
    try:
        from crypto import pqc_signing
        sig = base64.b64decode(manifest.get("signature_b64", "") or "")
        if not sig:
            return False
        pub = (base64.b64decode(public_key_b64) if public_key_b64
               else pqc_signing.public_key(alias=alias))
        return pqc_signing.verify(_payload(manifest), sig, pub)
    except Exception:  # noqa: BLE001
        return False


def diff_against_live(manifest: dict, live_tools: list[dict[str, Any]]) -> dict:
    """Detect drift: tools present live but NOT in the signed manifest (rogue/injected) + manifest tools now missing."""
    pinned = {(e["server"], e["name"]) for e in manifest.get("tools", [])}
    live = {(t.get("server", ""), t["name"]) for t in live_tools}
    return {"rogue": sorted(live - pinned), "missing": sorted(pinned - live), "ok": live == pinned}


__all__ = ["build_manifest", "sign_manifest", "verify_manifest", "diff_against_live"]
