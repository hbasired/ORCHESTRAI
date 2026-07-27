"""Stage 13.5 — key management facade over the KeyProvider (KB_13 §"Key inventory", §"Rotation drill").

Thin role-oriented API: `get_signing_key(role)`, `rotate(key_id)`, `get_public_key_by_version(alias, version)`
(the last is what `scripts/verify-audit-chain.py` imports). All delegate to `get_key_provider()` — no concrete
backend is imported here, so the HSM swap stays a config change.
"""
from __future__ import annotations

from typing import Any, Optional


def get_signing_key(role: str = "agent-identity") -> dict[str, Any]:
    """Ensure the `role` alias has an active keypair and return a descriptor (alias, version, algorithm, public_key)."""
    from crypto.key_provider import get_key_provider
    p = get_key_provider()
    version = p.active_version(role)  # generates v1 on first use
    return {"alias": role, "version": version, "algorithm": "ML-DSA-65",
            "public_key": p.public_key(role, version)}


def rotate(key_id: str) -> int:
    """Overlap rotation: generate the next key version for `key_id` (old versions kept for verification)."""
    from crypto.key_provider import get_key_provider
    return get_key_provider().rotate(key_id)


def get_public_key_by_version(alias: str, version: int) -> bytes:
    """Public key bytes for (alias, version) — used to verify historical audit_chain rows across rotations."""
    from crypto.key_provider import get_key_provider
    return get_key_provider().public_key(alias, int(version))


# ---- Stage 18: 4-key-type rotation CLI (driven by scripts/rotate-pqc-keys.sh; KB_13 rotation drill) -------------

# key-type -> (alias, algorithm). <env> is appended by the caller's environment in deployment.
KEY_TYPES = {
    "identity": ("agent-identity", "ML-DSA-65"),       # ADRs / audit_chain / agent cards
    "tls":      ("agent-tls", "ML-KEM-768+X25519"),    # hybrid TLS (sidecar) — ML-KEM keypair
    "firmware": ("firmware-policy", "SLH-DSA-SHA2-128s"),  # long-trust bundle signing
    "hmac":     ("ot-msg-integrity", "HMAC-SHA-384"),  # OT message MAC (symmetric)
}


def rotate_key_type(key_type: str, *, mode: str = "hybrid", grace_hours: int = 24, dry_run: bool = False) -> dict:
    """Overlap-rotate a key by TYPE (KB_13 §"Rotation drill"). Generates the new key version (old kept for
    verification), writes a signed `key_rotation` audit_chain marker, and reports the overlap steps. `dry_run`
    mutates nothing. Returns a summary dict."""
    if key_type not in KEY_TYPES:
        raise ValueError(f"--key-type must be one of {sorted(KEY_TYPES)}")
    alias, algorithm = KEY_TYPES[key_type]
    steps = ["generate(new version, old active)", "mark(key_rotation audit row signed by old+new)",
             "re-sign(artefacts/cards; publish both pubkeys)", f"grace({grace_hours}h, both verify)",
             "revoke(old → revocation list, read-only for historical verify)", "verify(verify-audit-chain.py)"]
    summary = {"key_type": key_type, "alias": alias, "algorithm": algorithm, "mode": mode,
               "grace_hours": grace_hours, "dry_run": dry_run, "overlap_steps": steps}
    if dry_run:
        summary["new_version"] = "(dry-run; no key generated)"
        return summary

    # Generate the new key version per algorithm family (old version retained for historical verification).
    if key_type == "identity":
        summary["new_version"] = rotate(alias)                                   # KeyProvider ML-DSA rotate
    elif key_type == "tls":
        from crypto import pqc_kem
        pqc_kem.generate_kem_keypair(alias)                                      # new ML-KEM keypair
        summary["new_version"] = "rotated (new ML-KEM-768 encapsulation key)"
    elif key_type == "firmware":
        from crypto import pqc_slh_dsa
        pqc_slh_dsa.generate_keypair(alias)                                      # new SLH-DSA keypair
        summary["new_version"] = "rotated (new SLH-DSA-SHA2-128s key)"
    elif key_type == "hmac":
        import os as _os
        from pathlib import Path as _P
        d = _P(_os.environ.get("KEY_STORE_DIR", str(_P(__file__).resolve().parent / ".keystore"))) / "hmac"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{alias}.key").write_bytes(_os.urandom(48))                        # new 384-bit HMAC key
        summary["new_version"] = "rotated (new HMAC-SHA-384 key)"

    # Anchor the rotation in the audit chain (best-effort; the marker row links the chain across the version boundary).
    try:
        from observability.evidence_sink import record
        summary["audit_seq"] = record("crypto.key_manager", "key_rotation",
                                      {"key_type": key_type, "alias": alias, "algorithm": algorithm, "mode": mode})
    except Exception:  # noqa: BLE001
        summary["audit_seq"] = None
    return summary


def _main(argv: list[str]) -> int:
    import argparse
    import json
    p = argparse.ArgumentParser(prog="key_manager")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rotate")
    r.add_argument("--key-type", default="identity")
    r.add_argument("--mode", default="hybrid")
    r.add_argument("--grace-hours", type=int, default=24)
    r.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if args.cmd == "rotate":
        out = rotate_key_type(args.key_type, mode=args.mode, grace_hours=args.grace_hours, dry_run=args.dry_run)
        print(json.dumps(out, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    import os
    import sys
    # Make `from crypto import ...` resolve when launched as `python -m backend.crypto.key_manager` (repo-root cwd).
    _backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _backend not in sys.path:
        sys.path.insert(0, _backend)
    raise SystemExit(_main(sys.argv[1:]))


__all__ = ["get_signing_key", "rotate", "get_public_key_by_version", "rotate_key_type", "KEY_TYPES"]
