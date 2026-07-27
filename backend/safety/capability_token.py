"""Stage 33 (G-075) — unforgeable actuation capability tokens (research §44.1).

A capability token is an unforgeable, action-bound, time-limited authorization that `safety.validator.validate()`
MINTS on every ALLOW and `safety.sil_bridge.execute()` REDEEMS before actuating. It closes the G-075 hole: previously
`execute()` trusted a caller-settable `Decision.allow`/`route`, so a FORGED `Decision(allow=True, route="sil_bridge")`
could actuate. Now a Decision without a valid, fresh token bound to THE SPECIFIC action is rejected.

Mechanism (stdlib only — no new deps):
  * A per-process secret key (`os.urandom(32)` at import) — never leaves the process; not persisted.
  * The token is `HMAC-SHA-256(secret, canonical{allow, route, contract, sil, action_hash, nonce, issued_at})`, where
    `action_hash = sha256(canonical(action))` BINDS the token to the exact action (a token for action A can't redeem
    action B).
  * Freshness: `issued_at` + a short window defends against TOCTOU / replay of a stale-but-genuine Decision.

This is DEFENCE-IN-DEPTH, not the sole gate: the authoritative check remains re-running `validate()` from the
contract + current world_state (which `execute` does when given them). The token makes the no-contract path
forgery/replay-resistant instead of blindly-trusting. Same-process key access is a far higher bar than forging a dict.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any

# Per-process secret. Regenerated each start; tokens do not survive a restart (fine — they're single-actuation, short-lived).
_SECRET = os.urandom(32)

DEFAULT_FRESHNESS_S = 5.0        # a genuine validate→execute round-trip is sub-second; 5s is generous, TOCTOU-tight.


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def action_hash(action: Any) -> str:
    """sha256 over the canonical action — binds a token to the exact action it authorizes."""
    payload = action.model_dump() if hasattr(action, "model_dump") else dict(action)
    return hashlib.sha256(_canon(payload)).hexdigest()


def _token_payload(*, allow: bool, route: str, contract: str, sil: int,
                   act_hash: str, nonce: str, issued_at: float) -> bytes:
    return _canon({"allow": allow, "route": route, "contract": contract, "sil": sil,
                   "action_hash": act_hash, "nonce": nonce, "issued_at": round(issued_at, 6)})


def mint(*, allow: bool, route: str, contract: str, sil: int, action: Any) -> dict[str, Any]:
    """Mint a capability token for an ALLOWED decision on `action`. Returns {token, nonce, issued_at}."""
    nonce = os.urandom(12).hex()
    issued_at = time.time()
    act_hash = action_hash(action)
    mac = hmac.new(_SECRET, _token_payload(allow=allow, route=route, contract=contract, sil=sil,
                                           act_hash=act_hash, nonce=nonce, issued_at=issued_at),
                   hashlib.sha256).hexdigest()
    return {"token": mac, "nonce": nonce, "issued_at": issued_at}


def verify(*, token: str, allow: bool, route: str, contract: str, sil: int, action: Any,
           nonce: str, issued_at: float, freshness_s: float = DEFAULT_FRESHNESS_S) -> tuple[bool, str]:
    """Verify a token authorizes THIS action, is unforged, and is fresh. Returns (ok, reason)."""
    if not token or not nonce or not issued_at:
        return False, "missing capability token (unsigned/forged decision)"
    age = time.time() - float(issued_at)
    if age < -1.0:
        return False, f"token issued in the future (clock skew {age:.2f}s)"
    if age > freshness_s:
        return False, f"stale token (age {age:.2f}s > {freshness_s}s freshness window) — possible replay/TOCTOU"
    expected = hmac.new(_SECRET, _token_payload(allow=allow, route=route, contract=contract, sil=sil,
                                                act_hash=action_hash(action), nonce=nonce, issued_at=float(issued_at)),
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, str(token)):   # constant-time; fails if any bound field (incl. action) differs
        return False, "invalid capability token (forged, tampered, or minted for a different action)"
    return True, "ok"


__all__ = ["mint", "verify", "action_hash", "DEFAULT_FRESHNESS_S"]
