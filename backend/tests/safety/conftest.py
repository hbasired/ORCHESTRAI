"""Isolated keystore for safety tests that sign audit_chain rows (real ML-DSA-65, no infra needed for signing)."""
import pytest


@pytest.fixture(autouse=True)
def isolated_keystore(tmp_path, monkeypatch):
    monkeypatch.setenv("KEY_STORE_DIR", str(tmp_path / "keystore"))
    monkeypatch.setenv("CRYPTO_PROVIDER", "software")
    try:
        from crypto.key_provider import _reset_provider_for_tests
        _reset_provider_for_tests()
    except Exception:
        pass
    yield
    try:
        from crypto.key_provider import _reset_provider_for_tests
        _reset_provider_for_tests()
    except Exception:
        pass
