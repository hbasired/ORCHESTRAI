"""Isolated keystore + provider reset for the crypto tests (no shared state, no infra)."""
import pytest


@pytest.fixture(autouse=True)
def isolated_keystore(tmp_path, monkeypatch):
    """Point the software keystore at a fresh tmp dir + force the software provider, re-selected per test."""
    monkeypatch.setenv("KEY_STORE_DIR", str(tmp_path / "keystore"))
    monkeypatch.setenv("CRYPTO_PROVIDER", "software")
    monkeypatch.delenv("AGENT_IDENTITY_ALIAS", raising=False)
    from crypto.key_provider import _reset_provider_for_tests
    _reset_provider_for_tests()
    yield
    _reset_provider_for_tests()
