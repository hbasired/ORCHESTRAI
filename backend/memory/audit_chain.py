"""Stage 12 — append-only, SHA-256 hash-chained audit log (EU AI Act Art. 12 evidence).

Each row's `hash = SHA-256(prev_hash || canonical(payload))` chains to its predecessor (research §19.4, KB_14
§"Audit chain"); altering any row breaks every subsequent hash. The DB enforces append-only via BEFORE UPDATE/DELETE
triggers (migration `0003_audit_chain`). A signature over the hash gives non-repudiation: we write a STRUCTURALLY
correct placeholder now (`algorithm='placeholder-sha256'`, `key_version=0`) and swap in real ML-DSA-65 via
`backend/crypto/pqc_signing.py` at Stage 13.5 (the signer is resolved dynamically below, so 13.5 is a drop-in).

Honest: if Postgres is unreachable, `append()` raises `AuditChainUnavailable` — it NEVER silently drops an audit
record or fabricates a seq (Rule 1a). Concurrency: appends serialize on a Postgres advisory lock so the chain links
deterministically under concurrent writers.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Optional

GENESIS_HASH = b"\x00" * 32
PLACEHOLDER_ALGO = "placeholder-sha256"
# A stable 64-bit key for pg_advisory_xact_lock so concurrent appends serialize on the chain tail.
_APPEND_LOCK_KEY = 0x4155_4449_5443_4841  # "AUDITCHA"


class AuditChainUnavailable(RuntimeError):
    """Raised when the audit chain cannot be written (no DB) — never swallowed, never faked."""


def _dsn() -> Optional[str]:
    # R1/G-1: prefer AUDIT_CHAIN_DATABASE_URL so the test suite can point the chain at an ISOLATED DB and never pollute
    # the attestable production/dev chain (the recurring ephemeral-test-key pollution the CTO #4 review flagged). Falls
    # back to the shared app DSN when unset (normal runtime).
    return (os.environ.get("AUDIT_CHAIN_DATABASE_URL")
            or os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))


def _connect():
    dsn = _dsn()
    if not dsn:
        raise AuditChainUnavailable("no DATABASE_URL/POSTGRES_URL configured")
    try:
        import psycopg
        return psycopg.connect(dsn, autocommit=False, connect_timeout=5)
    except Exception as e:  # noqa: BLE001
        raise AuditChainUnavailable(f"Postgres unreachable: {e}") from e


def canonical(payload: dict[str, Any]) -> bytes:
    """Deterministic JSON encoding (sorted keys, no whitespace) — the hashed form. `default=str` for datetimes."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def compute_hash(prev_hash: bytes, payload: dict[str, Any]) -> bytes:
    return hashlib.sha256(bytes(prev_hash) + canonical(payload)).digest()


def _sign(digest: bytes) -> tuple[bytes, int, str]:
    """Return (signature, key_version, algorithm). Real ML-DSA-65 if Stage-13.5 crypto is present, else placeholder.

    Placeholder is NOT a fake signature passed off as real — it is explicitly labelled `placeholder-sha256` with
    `key_version=0`, and `verify_range` treats placeholder rows as 'chain-valid, signature-not-yet-cryptographic'.
    """
    try:
        from crypto.pqc_signing import sign as pqc_sign, active_key_version  # Stage 13.5
        return pqc_sign(digest), int(active_key_version()), "ML-DSA-65"
    except Exception:  # noqa: BLE001 - crypto module not present until Stage 13.5
        return digest, 0, PLACEHOLDER_ALGO


def append(actor: str, action: str, payload: dict[str, Any], *, conn: Any = None) -> int:
    """Append one audit row and return its `seq`. Chains to the current tail under an advisory lock.

    `conn`: optional existing psycopg connection (so a caller can append within its own transaction). If omitted, a
    short-lived connection is opened + committed here.
    """
    if not actor or not action:
        raise ValueError("audit_chain.append requires non-empty actor + action")
    own = conn is None
    c = conn or _connect()
    try:
        with c.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (_APPEND_LOCK_KEY,))
            cur.execute("SELECT hash FROM audit_chain ORDER BY seq DESC LIMIT 1")
            row = cur.fetchone()
            prev_hash = bytes(row[0]) if row else GENESIS_HASH
            h = compute_hash(prev_hash, payload)
            sig, key_version, algo = _sign(h)
            cur.execute(
                """INSERT INTO audit_chain (actor, action, payload, prev_hash, hash, sig_mldsa, key_version, algorithm)
                   VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s) RETURNING seq""",
                (actor, action, json.dumps(payload, default=str), prev_hash, h, sig, key_version, algo),
            )
            seq = int(cur.fetchone()[0])
        if own:
            c.commit()
        return seq
    except AuditChainUnavailable:
        raise
    except Exception as e:  # noqa: BLE001
        if own:
            c.rollback()
        raise AuditChainUnavailable(f"audit append failed: {e}") from e
    finally:
        if own:
            c.close()


def read_recent(actions: Optional[list[str]] = None, *, limit: int = 20,
                target_substr: Optional[str] = None, conn: Any = None) -> list[dict[str, Any]]:
    """Stage 29 (G-022) — read the most-recent audit rows as EVIDENCE (newest first).

    This is a read-only query over the real, signed evidence store — the source of truth for "what happened / why".
    `actions` filters to specific action types (e.g. `["decision.trace", "decision"]`); `target_substr` further
    keeps only rows whose canonical payload mentions the substring (a cheap incident/stage filter). Returns a list
    of `{seq, ts, actor, action, payload}` dicts. Raises `AuditChainUnavailable` when Postgres is unreachable so the
    caller can degrade honestly (never fabricate an answer). NO writes.
    """
    own = conn is None
    c = conn or _connect()
    try:
        with c.cursor() as cur:
            if actions:
                cur.execute(
                    "SELECT seq, ts, actor, action, payload FROM audit_chain "
                    "WHERE action = ANY(%s) ORDER BY seq DESC LIMIT %s",
                    (list(actions), int(max(1, limit) * (4 if target_substr else 1))))
            else:
                cur.execute(
                    "SELECT seq, ts, actor, action, payload FROM audit_chain ORDER BY seq DESC LIMIT %s",
                    (int(max(1, limit) * (4 if target_substr else 1)),))
            rows = cur.fetchall()
        out: list[dict[str, Any]] = []
        for seq, ts, actor, action, payload in rows:
            if target_substr:
                blob = json.dumps(payload, default=str).lower()
                if target_substr.lower() not in blob:
                    continue
            out.append({"seq": seq, "ts": ts, "actor": actor, "action": action, "payload": payload})
            if len(out) >= limit:
                break
        return out
    except AuditChainUnavailable:
        raise
    except Exception as e:  # noqa: BLE001
        raise AuditChainUnavailable(f"audit read failed: {e}") from e
    finally:
        if own:
            c.close()


@dataclass
class VerifyReport:
    ok: bool
    checked: int
    first_broken_seq: Optional[int]
    placeholder_signatures: int
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "checked": self.checked, "first_broken_seq": self.first_broken_seq,
                "placeholder_signatures": self.placeholder_signatures, "detail": self.detail}


def verify_range(start_seq: int = 1, end_seq: Optional[int] = None, *, conn: Any = None) -> VerifyReport:
    """Walk the chain [start_seq, end_seq], recompute each hash from prev_hash+payload, and check linkage.

    Returns a report; the FIRST row whose recomputed hash or prev-link mismatches sets `first_broken_seq`. Rows with
    a placeholder signature are counted (not a failure pre-Stage-13.5)."""
    own = conn is None
    c = conn or _connect()
    try:
        with c.cursor() as cur:
            if end_seq is None:
                cur.execute("SELECT seq, payload, prev_hash, hash, algorithm FROM audit_chain "
                            "WHERE seq >= %s ORDER BY seq", (start_seq,))
            else:
                cur.execute("SELECT seq, payload, prev_hash, hash, algorithm FROM audit_chain "
                            "WHERE seq >= %s AND seq <= %s ORDER BY seq", (start_seq, end_seq))
            rows = cur.fetchall()
            # The expected prev_hash for the first row is the hash of seq-1 (or GENESIS if start_seq==1).
            if start_seq <= 1:
                expected_prev = GENESIS_HASH
            else:
                cur.execute("SELECT hash FROM audit_chain WHERE seq = %s", (start_seq - 1,))
                prior = cur.fetchone()
                expected_prev = bytes(prior[0]) if prior else GENESIS_HASH
        checked = 0
        placeholders = 0
        for seq, payload, prev_hash, stored_hash, algo in rows:
            prev_hash, stored_hash = bytes(prev_hash), bytes(stored_hash)
            if prev_hash != expected_prev:
                return VerifyReport(False, checked, int(seq), placeholders,
                                    f"prev_hash link broken at seq={seq}")
            recomputed = compute_hash(prev_hash, payload)
            if recomputed != stored_hash:
                return VerifyReport(False, checked, int(seq), placeholders,
                                    f"hash mismatch at seq={seq} (row altered)")
            if algo == PLACEHOLDER_ALGO:
                placeholders += 1
            expected_prev = stored_hash
            checked += 1
        return VerifyReport(True, checked, None, placeholders,
                            f"chain intact: {checked} rows verified"
                            + (f" ({placeholders} placeholder-signed, real ML-DSA-65 at Stage 13.5)" if placeholders else ""))
    finally:
        if own:
            c.close()


__all__ = ["append", "read_recent", "verify_range", "VerifyReport", "AuditChainUnavailable",
           "compute_hash", "canonical", "GENESIS_HASH", "PLACEHOLDER_ALGO"]
