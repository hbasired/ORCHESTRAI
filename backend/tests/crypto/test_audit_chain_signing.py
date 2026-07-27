"""Stage 13.5 — the audit_chain now signs with REAL ML-DSA-65 (replacing the Stage-12 placeholder)."""
import os

import pytest


def test_audit_chain_sign_uses_real_mldsa_no_db():
    """`audit_chain._sign(digest)` returns a real ML-DSA-65 signature (not the placeholder) — no DB needed."""
    from memory.audit_chain import _sign
    from crypto import pqc_signing
    digest = b"\x11" * 32
    sig, key_version, algorithm = _sign(digest)
    assert algorithm == "ML-DSA-65"          # NOT 'placeholder-sha256'
    assert key_version >= 1                   # NOT 0 (the placeholder key_version)
    assert len(sig) == 3309                   # real ML-DSA-65 signature size
    # and the signature verifies under the agent-identity public key
    assert pqc_signing.verify(digest, sig, pqc_signing.public_key(version=key_version)) is True


_HAS_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))


@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL: audit_chain DB round-trip not exercisable")
@pytest.mark.timeout(60)
def test_audit_chain_row_is_mldsa_signed_end_to_end():
    """Append a row → it is ML-DSA-65 signed in the DB AND the signature verifies."""
    import psycopg
    from memory.audit_chain import append, _dsn
    from crypto import pqc_signing, key_manager
    seq = append("agent:test", "decision.unit", {"k": "stage13_5"})
    # Read back from the SAME DSN audit_chain writes to (AUDIT_CHAIN_DATABASE_URL when the test session isolates the
    # chain — R1/G-1 — else the shared DB). Reading raw DATABASE_URL here would hit the wrong row under isolation.
    dsn = _dsn()
    with psycopg.connect(dsn) as c, c.cursor() as cur:
        cur.execute("SELECT algorithm, key_version, hash, sig_mldsa FROM audit_chain WHERE seq=%s", (seq,))
        algorithm, kv, h, sig = cur.fetchone()
    assert algorithm == "ML-DSA-65" and kv >= 1
    pub = key_manager.get_public_key_by_version("agent-identity", kv)
    assert pqc_signing.verify(bytes(h), bytes(sig), pub) is True
