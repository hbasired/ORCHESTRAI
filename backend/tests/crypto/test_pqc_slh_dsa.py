"""Stage 18 — SLH-DSA-SHA2-128s long-trust sign/verify (FIPS 205, OpenSSL 3.5). Skips if OpenSSL < 3.5."""
import pytest

from crypto import pqc_slh_dsa

_HAS = pqc_slh_dsa.openssl_supports_slh_dsa()
skip = pytest.mark.skipif(not _HAS, reason="OpenSSL >= 3.5 with SLH-DSA not on PATH")


@skip
def test_sign_verify_roundtrip():
    data = b"firmware-image-v1: sha256=deadbeef"
    sig = pqc_slh_dsa.sign(data, "firmware-policy-test")
    assert len(sig) > 1000 and pqc_slh_dsa.algorithm() == "SLH-DSA-SHA2-128s"
    assert pqc_slh_dsa.verify(data, sig, alias="firmware-policy-test") is True


@skip
def test_tamper_rejected():
    data = b"policy-bundle-v1"
    sig = pqc_slh_dsa.sign(data, "firmware-policy-test")
    assert pqc_slh_dsa.verify(data + b"X", sig, alias="firmware-policy-test") is False
    assert pqc_slh_dsa.verify(data, sig[:-1] + bytes([sig[-1] ^ 0xFF]), alias="firmware-policy-test") is False


@skip
def test_verify_with_explicit_public_key():
    pub = pqc_slh_dsa.generate_keypair("fw-explicit")
    data = b"model-card-attestation"
    sig = pqc_slh_dsa.sign(data, "fw-explicit")
    assert pqc_slh_dsa.verify(data, sig, public_key_pem=pub) is True
    # a DIFFERENT key's public key must NOT verify
    other_pub = pqc_slh_dsa.generate_keypair("fw-other")
    assert pqc_slh_dsa.verify(data, sig, public_key_pem=other_pub) is False


def test_honest_unavailable_is_not_faked():
    """If OpenSSL 3.5 is genuinely absent, sign raises SlhDsaUnavailable (never a fake signature, Rule 1a)."""
    if _HAS:
        pytest.skip("OpenSSL 3.5 present — unavailability path not exercisable here")
    with pytest.raises(pqc_slh_dsa.SlhDsaUnavailable):
        pqc_slh_dsa.sign(b"x", "any")
