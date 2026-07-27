"""Stage 13.5 — key manager: rotation drill + provider-swap agility (KB_13). No infra."""
import pytest

from crypto import key_manager, pqc_signing
from crypto.key_provider import get_key_provider


def test_get_signing_key_descriptor():
    k = key_manager.get_signing_key("agent-identity")
    assert k["alias"] == "agent-identity" and k["version"] >= 1
    assert k["algorithm"] == "ML-DSA-65" and len(k["public_key"]) == 1952


def test_rotation_keeps_old_version_verifiable():
    """Overlap rotation (KB_13 §"Rotation drill"): a signature made under v1 still verifies after rotating to v2."""
    p = get_key_provider()
    alias = "agent-identity"
    v1 = p.active_version(alias)
    data = b"signed-under-v1"
    sig_v1 = p.sign(alias, data)
    pub_v1 = p.public_key(alias, v1)

    v2 = key_manager.rotate(alias)
    assert v2 == v1 + 1
    assert p.active_version(alias) == v2          # new signs use v2
    # historical verification: v1 sig still verifies under the retained v1 public key
    assert p.verify(pub_v1, data, sig_v1) is True
    assert key_manager.get_public_key_by_version(alias, v1) == pub_v1
    # a fresh sign now uses v2; v1 pub must NOT verify it
    sig_v2 = p.sign(alias, data)
    assert p.verify(p.public_key(alias, v2), data, sig_v2) is True
    assert p.verify(pub_v1, data, sig_v2) is False


def test_provider_swap_is_config_only_and_pkcs11_is_honest_stub(monkeypatch):
    """CRYPTO_PROVIDER selects the backend (config, no code change). pkcs11/vault are HONEST stubs (raise), not fakes."""
    from crypto.key_provider import _reset_provider_for_tests
    monkeypatch.setenv("CRYPTO_PROVIDER", "pkcs11")
    _reset_provider_for_tests()
    with pytest.raises(NotImplementedError) as ei:
        get_key_provider()
    assert "pkcs11" in str(ei.value).lower() or "softhsm" in str(ei.value).lower()
    # back to software → works again (proves the seam, not a one-way break)
    monkeypatch.setenv("CRYPTO_PROVIDER", "software")
    _reset_provider_for_tests()
    assert pqc_signing.sign(b"after-swap")  # software provider signs
