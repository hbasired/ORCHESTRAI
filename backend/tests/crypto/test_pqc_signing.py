"""Stage 13.5 — ML-DSA-65 sign/verify (real FIPS-204 via the software KeyProvider). No infra."""
import pytest

from crypto import pqc_signing


def test_sign_verify_roundtrip():
    data = b"audit_chain row hash"
    sig = pqc_signing.sign(data)
    pub = pqc_signing.public_key()
    assert pqc_signing.verify(data, sig, pub) is True


def test_tamper_is_rejected():
    data = b"original"
    sig = pqc_signing.sign(data)
    pub = pqc_signing.public_key()
    assert pqc_signing.verify(b"tampered", sig, pub) is False
    bad = bytearray(sig); bad[0] ^= 0xFF
    assert pqc_signing.verify(data, bytes(bad), pub) is False


def test_signature_is_real_ml_dsa_65():
    """FIPS-204 ML-DSA-65 sizes — proves a REAL algorithm, not a placeholder/stub."""
    sig = pqc_signing.sign(b"x")
    pub = pqc_signing.public_key()
    assert pqc_signing.algorithm() == "ML-DSA-65"
    assert len(sig) == 3309   # ML-DSA-65 signature size
    assert len(pub) == 1952   # ML-DSA-65 public key size


def test_software_provider_capabilities_are_honest():
    from crypto.key_provider import get_key_provider
    caps = get_key_provider().capabilities()
    assert "ML-DSA-65" in caps["supported_algorithms"]
    assert caps["backend"].startswith("software")
    assert caps["attestation"] is False  # honest: software tier has no hardware attestation
