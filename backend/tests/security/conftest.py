"""Isolated keystore for zero-trust tests (real per-agent ML-DSA-65 keys, no infra)."""
import pytest


@pytest.fixture(autouse=True)
def isolated_keystore(tmp_path, monkeypatch):
    monkeypatch.setenv("KEY_STORE_DIR", str(tmp_path / "keystore"))
    monkeypatch.setenv("CRYPTO_PROVIDER", "software")
    from crypto.key_provider import _reset_provider_for_tests
    _reset_provider_for_tests()
    yield
    _reset_provider_for_tests()
