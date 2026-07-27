"""Stage 18 — ML-KEM-768 KEM roundtrip (FIPS 203, kyber-py)."""
from crypto import pqc_kem


def test_kem_roundtrip_shared_secret_matches():
    ek, dk = pqc_kem.keygen()
    ct, ss = pqc_kem.encapsulate(ek)
    assert pqc_kem.decapsulate(ct, dk) == ss
    assert len(ss) == 32 and pqc_kem.ALGORITHM == "ML-KEM-768"


def test_fips203_sizes():
    ek, dk = pqc_kem.keygen()
    ct, _ = pqc_kem.encapsulate(ek)
    assert len(ek) == 1184 and len(ct) == 1088   # FIPS-203 ML-KEM-768 sizes


def test_alias_backed_decaps_from_keystore():
    pub = pqc_kem.generate_kem_keypair("agent-tls-test")
    ct, ss = pqc_kem.encapsulate(pub)
    assert pqc_kem.decapsulate(ct, "agent-tls-test") == ss          # dk loaded from the keystore
    assert pqc_kem.public_kem_key("agent-tls-test") == pub


def test_tampered_ciphertext_yields_different_secret():
    """ML-KEM implicit rejection: a tampered ciphertext decapsulates to a DIFFERENT secret (never the real one),
    and never raises — the handshake then fails downstream, not here."""
    ek, dk = pqc_kem.keygen()
    ct, ss = pqc_kem.encapsulate(ek)
    bad = bytearray(ct); bad[0] ^= 0xFF
    assert pqc_kem.decapsulate(bytes(bad), dk) != ss


def test_two_keypairs_independent():
    ek1, dk1 = pqc_kem.keygen()
    ek2, dk2 = pqc_kem.keygen()
    ct, ss = pqc_kem.encapsulate(ek1)
    assert pqc_kem.decapsulate(ct, dk2) != ss   # wrong private key → wrong secret
    assert pqc_kem.decapsulate(ct, dk1) == ss
