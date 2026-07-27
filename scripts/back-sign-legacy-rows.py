#!/usr/bin/env python3
"""Stage 19 (G-073) — re-attest audit_chain rows whose ML-DSA-65 signature does not verify under the CURRENT key.

Context: in DEV, test runs that isolated the keystore (`tmp_path`) while a shared `DATABASE_URL` was set wrote
`audit_chain` rows signed by ephemeral keys that no longer exist — so those post-cutover (key_version ≥ 1) rows can no
longer be verified (a dev test-isolation artifact; PRODUCTION retains every key version in the HSM, so this never
happens there). The **hash chain is intact** (tamper-evidence preserved) — only the signatures are unverifiable.

This tool RE-ATTESTS such rows: it re-signs each row's existing `hash` with the current `agent-identity` key and
updates ONLY the `sig_mldsa` + `key_version` columns (the hash is unchanged, so the append-only chain is preserved).
It writes a signed `chain_reattestation` marker row. Pre-Stage-13.5 placeholder rows (key_version 0) are LEFT as the
documented placeholder→ML-DSA cutover unless `--include-placeholders` is passed.

Honesty: this is a CONTROLLED, audited dev re-baseline (it briefly disables the immutability triggers as the table
owner, then re-enables them). Production never needs it. Requires `--confirm`; refuses if `ENV=prod`/`APP_ENV=prod`.

Usage: DATABASE_URL=... python scripts/back-sign-legacy-rows.py --confirm [--include-placeholders] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))


def _verifier():
    from crypto.key_manager import get_public_key_by_version
    from crypto.pqc_signing import active_key_version, sign, verify
    return sign, verify, active_key_version, get_public_key_by_version


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="required — this mutates audit_chain signatures")
    ap.add_argument("--include-placeholders", action="store_true", help="also re-attest pre-13.5 kv0 placeholder rows")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if (os.environ.get("ENV") or os.environ.get("APP_ENV") or "").lower() in ("prod", "production"):
        print("REFUSE: production environment — re-attestation is a dev-only re-baseline (prod retains all key versions).")
        return 2
    if not args.confirm and not args.dry_run:
        print("REFUSE: pass --confirm (this re-signs audit_chain rows) or --dry-run.")
        return 2

    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not url:
        print("REFUSE: no DATABASE_URL.")
        return 2
    import psycopg2
    sign, verify, active_key_version, get_pub = _verifier()
    cur_kv = active_key_version("agent-identity")
    cur_pub = get_pub("agent-identity", cur_kv)

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT seq, hash, sig_mldsa, key_version FROM audit_chain ORDER BY seq")
    rows = cur.fetchall()

    to_fix = []
    for seq, hsh, sig, kv in rows:
        is_placeholder = kv is None or int(kv) == 0 or len(bytes(sig)) < 100
        if is_placeholder and not args.include_placeholders:
            continue
        try:
            ok = verify(bytes(hsh), bytes(sig), cur_pub)
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            to_fix.append((seq, bytes(hsh)))

    print(f"rows={len(rows)} | current key=agent-identity v{cur_kv} | rows needing re-attestation: {len(to_fix)}")
    if not to_fix:
        print("nothing to re-attest — all in-scope rows already verify under the current key.")
        conn.close()
        return 0
    if args.dry_run:
        print(f"dry-run: would re-attest seqs {[s for s, _ in to_fix[:10]]}{'...' if len(to_fix) > 10 else ''}")
        conn.close()
        return 0

    try:
        cur.execute("ALTER TABLE audit_chain DISABLE TRIGGER no_update")  # owner-only, controlled maintenance
        for seq, hsh in to_fix:
            new_sig = sign(hsh)  # re-sign the (unchanged) hash with the current key
            cur.execute("UPDATE audit_chain SET sig_mldsa=%s, key_version=%s WHERE seq=%s",
                        (psycopg2.Binary(new_sig), cur_kv, seq))
        conn.commit()
    finally:
        cur.execute("ALTER TABLE audit_chain ENABLE TRIGGER no_update")
        conn.commit()

    # signed marker row (via the normal append path, real ML-DSA-65)
    try:
        from observability.evidence_sink import record
        seq = record("crypto.key_manager", "chain_reattestation",
                     {"reattested_rows": len(to_fix), "current_key_version": cur_kv,
                      "reason": "dev test-key-isolation pollution + pre-13.5 placeholders re-attested under current key",
                      "include_placeholders": args.include_placeholders})
        print(f"re-attested {len(to_fix)} rows; wrote chain_reattestation marker at seq {seq}.")
    except Exception as e:  # noqa: BLE001
        print(f"re-attested {len(to_fix)} rows; marker write skipped ({type(e).__name__}).")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
