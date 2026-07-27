"""Isolated keystore + provider/singleton reset for the A2A tests (real ML-DSA-65, no infra)."""
import pytest


@pytest.fixture(autouse=True)
def isolated_crypto(tmp_path, monkeypatch):
    monkeypatch.setenv("KEY_STORE_DIR", str(tmp_path / "keystore"))
    monkeypatch.setenv("CRYPTO_PROVIDER", "software")
    monkeypatch.delenv("AGENT_IDENTITY_ALIAS", raising=False)
    from crypto.key_provider import _reset_provider_for_tests
    _reset_provider_for_tests()
    # reset A2A singletons too
    import a2a.peer_state as ps
    import a2a.revocation as rev
    ps._registry = None
    rev._revocation = None
    yield
    _reset_provider_for_tests()
