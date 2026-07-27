#!/usr/bin/env python3
"""scripts/sign-decision-log.py <adr-file>

Appends an ML-DSA-65 signature footer to a decision-log ADR file. Stage 13.5+
wires the real signing path via backend/crypto/pqc_signing.py. Before then,
this script no-ops gracefully (prints a placeholder footer) so the closure
ritual doesn't fail during early stages.
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def canonical_body(text: str) -> str:
    """Body = text up to the signature footer (if any), normalized line endings."""
    marker = "\n<!-- ML-DSA-65 SIGNATURE FOOTER"
    if marker in text:
        text = text.split(marker, 1)[0]
    return text.rstrip() + "\n"


def try_real_sign(payload: bytes) -> tuple[str, str, str] | None:
    """Try the real signer at backend.crypto.pqc_signing. Returns (alg, key_id, sig_b64) or None."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "backend"))
        from crypto.pqc_signing import sign as _sign  # type: ignore
        from crypto.key_manager import get_signing_key  # type: ignore

        key = get_signing_key("agent-identity")          # ensures the alias has an active keypair
        sig_bytes = _sign(payload)                        # ML-DSA-65 over the canonical body; alias = agent-identity
        import base64

        key_id = f"{key['alias']}:v{key['version']}"
        return ("ML-DSA-65", key_id, base64.b64encode(sig_bytes).decode("ascii"))
    except Exception:
        return None


def placeholder_sign(payload: bytes) -> tuple[str, str, str]:
    """Pre-Stage-13.5 placeholder. Records the SHA-256 over canonical body."""
    h = hashlib.sha256(payload).hexdigest()
    return ("placeholder-SHA256", "no-key", h)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/sign-decision-log.py <adr-file>")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"ERROR: {p} not found")
        return 2
    text = p.read_text(encoding="utf-8")
    body = canonical_body(text)
    payload = body.encode("utf-8")

    out = try_real_sign(payload) or placeholder_sign(payload)
    alg, key_id, sig = out
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    footer = (
        "\n\n<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->\n"
        f"<!-- algorithm: {alg} -->\n"
        f"<!-- key_id:    {key_id} -->\n"
        f"<!-- signed_at: {ts} -->\n"
        f"<!-- signature: {sig} -->\n"
    )
    p.write_text(body + footer, encoding="utf-8")
    print(f"Signed: {p}  ({alg})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
