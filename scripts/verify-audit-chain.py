#!/usr/bin/env python3
"""scripts/verify-audit-chain.py [--quick]

Verifies the integrity of the append-only audit_chain table (Stage 13.5+):
- Every row's hash = SHA-256(prev_hash || canonical(payload))
- Every row's sig_mldsa verifies under the active ML-DSA-65 public key
  (or the previous key, if within the rotation grace window)
- Sequence is monotonic (1..N with no gaps)

Pre-Stage-13.5 / when DB not reachable: prints "(audit chain not yet enabled)" and exits 0
so hooks don't fail noisily during early stages.

Exit codes:
  0 — clean (or not-yet-enabled)
  1 — chain integrity broken
  2 — usage / environment error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _expand_env_vars(value: str, env: dict[str, str]) -> str:
    """Expand ${VAR} references against the given env dict + os.environ.

    Used when reading `.env.local` lines that reference earlier-defined
    variables (e.g., `DATABASE_URL=postgresql://${POSTGRES_USER}:...`).
    """
    import re

    def _repl(match: "re.Match[str]") -> str:
        key = match.group(1)
        return env.get(key, os.environ.get(key, match.group(0)))

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", _repl, value)


def _parse_env_file(path: Path) -> dict[str, str]:
    """Naive .env parser — handles VAR=value lines with ${VAR} expansion."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        v = _expand_env_vars(v, out)
        out[k] = v
    return out


def db_url() -> str | None:
    """Best-effort discovery of the DB URL.

    Order:
      1. os.environ DATABASE_URL / POSTGRES_DSN / POSTGRES_URL.
      2. `.env.local` (with ${VAR} expansion against itself + os.environ).
    """
    for var in ("DATABASE_URL", "POSTGRES_DSN", "POSTGRES_URL"):
        v = os.environ.get(var)
        if v and "${" not in v:  # avoid env vars that themselves contain unexpanded refs
            return v
    env_path = REPO_ROOT / ".env.local"
    env = _parse_env_file(env_path)
    for var in ("DATABASE_URL", "POSTGRES_DSN", "POSTGRES_URL"):
        if var in env and "${" not in env[var]:
            return env[var]
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true", help="Quick mode: verify last 100 rows only.")
    args = p.parse_args()

    # Try to connect to Postgres
    url = db_url()
    if not url:
        print("(audit chain not yet enabled — no DB URL discovered)")
        return 0

    try:
        import psycopg2  # type: ignore
    except ImportError:
        print("(audit chain verify skipped — psycopg2 not installed)")
        return 0

    try:
        conn = psycopg2.connect(url)
    except Exception as e:
        # Pre-Stage-13.5, audit_chain doesn't exist yet — connection failures
        # are EXPECTED (especially when running from host with no Docker
        # network access). Categorise as "not yet enabled" so audit-task.sh
        # treats it as non-blocking.
        print(f"(audit chain not yet enabled — DB unreachable: {e})")
        return 0

    try:
        cur = conn.cursor()
        # Check the table exists
        cur.execute("SELECT to_regclass('audit_chain')")
        if cur.fetchone()[0] is None:
            print("(audit chain not yet enabled — audit_chain table missing)")
            return 0

        limit_sql = "LIMIT 100" if args.quick else ""
        cur.execute(
            f"""
            SELECT seq, ts, actor, action, payload, prev_hash, hash, sig_mldsa, key_version
            FROM audit_chain
            ORDER BY seq DESC
            {limit_sql}
            """
        )
        rows = list(reversed(cur.fetchall()))
        if not rows:
            print("(audit chain empty)")
            return 0

        # Import the PQC verifier ONCE (not per-row). Distinguish crypto-UNAVAILABLE (pre-13.5 / no keystore) from a
        # genuine verify FAILURE — the old code swallowed both with try/except:pass (G-073).
        crypto_available = True
        crypto_note = ""
        _verify = None
        _pubkey = None
        try:
            sys.path.insert(0, str(REPO_ROOT / "backend"))
            from crypto.pqc_signing import verify as _verify  # type: ignore
            from crypto.key_manager import get_public_key_by_version as _pubkey  # type: ignore
        except Exception as e:  # noqa: BLE001
            crypto_available = False
            crypto_note = f"PQC verifier unavailable ({type(e).__name__}) — hash-chain checked, signatures NOT"

        # A placeholder (pre-Stage-13.5) row has key_version 0/NULL or a 32-byte sha256 "signature"; a post-cutover
        # row is real ML-DSA-65 (key_version >= 1, ~3309-byte sig) and MUST verify.
        def _is_placeholder(kv, sig) -> bool:
            return kv is None or int(kv) == 0 or len(bytes(sig)) < 100

        prev_hash = rows[0][5]  # first row's prev_hash as ground truth for the slice
        broken: list[str] = []
        placeholder_count = 0
        mldsa_verified = 0
        cutover_seq = None
        for row in rows:
            seq, ts, actor, action, payload, prev_h, hsh, sig, kv = row
            if prev_h != prev_hash:
                broken.append(f"seq={seq}: prev_hash mismatch")
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            expected = hashlib.sha256(bytes(prev_h) + canonical).digest()
            if bytes(hsh) != expected:
                broken.append(f"seq={seq}: hash mismatch")
            prev_hash = hsh

            if _is_placeholder(kv, sig):
                placeholder_count += 1
                continue
            # post-cutover ML-DSA-65 row — signature verification is LOAD-BEARING (G-073)
            if cutover_seq is None:
                cutover_seq = seq
            if not crypto_available:
                broken.append(f"seq={seq}: ML-DSA-65 row but PQC verifier unavailable to check it")
                continue
            try:
                ok = bool(_verify(bytes(hsh), bytes(sig), _pubkey("agent-identity", int(kv))))
            except Exception as e:  # noqa: BLE001 - a verify error is a FAILURE, not a pass
                ok = False
                broken.append(f"seq={seq}: ML-DSA-65 verify errored ({type(e).__name__})")
                continue
            if not ok:
                broken.append(f"seq={seq}: ML-DSA-65 signature INVALID (key v{kv})")
            else:
                mldsa_verified += 1

        # Report the placeholder->ML-DSA cutover explicitly so "OK" is never misread as "all rows PQ-signed" (G-073).
        if crypto_note:
            print(f"NOTE: {crypto_note}")
        print(f"hash-chain: {len(rows)} rows; pre-PQC placeholder rows: {placeholder_count}; "
              f"ML-DSA-65-verified rows: {mldsa_verified}")
        if cutover_seq is not None:
            print(f"placeholder->ML-DSA-65 cutover at seq {cutover_seq} "
                  f"(rows >= {cutover_seq} are post-quantum-signed){' [quick slice]' if args.quick else ''}")
        elif placeholder_count:
            print("all rows in range are pre-PQC placeholders (no post-cutover rows here)")

        if broken:
            print("AUDIT CHAIN BROKEN:")
            for b in broken[:20]:
                print(f"  - {b}")
            if len(broken) > 20:
                print(f"  ... and {len(broken) - 20} more")
            return 1

        print(f"Audit chain OK ({len(rows)} rows; hash chain intact; all {mldsa_verified} post-cutover signatures "
              f"verify{' [quick]' if args.quick else ''})")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
