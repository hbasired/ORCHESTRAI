"""Stage 14 — agent card sign/verify/tamper (real ML-DSA-65, no infra)."""
from datetime import datetime, timedelta, timezone

import pytest

from a2a.agent_card import AgentCard, sign_card, verify_card


def _card(**kw) -> AgentCard:
    base = dict(name="ai-embodied-agent", version="0.1.0", capabilities=["forecast_oee"],
                endpoints={"a2a": "http://localhost:8000/a2a/v1/rpc"},
                expiry=datetime.now(timezone.utc) + timedelta(days=90))
    base.update(kw)
    return AgentCard(**base)


def test_sign_then_verify():
    card = sign_card(_card())
    assert card.public_key_b64 and card.signature_b64
    assert verify_card(card) is True


def test_tampered_card_rejected():
    card = sign_card(_card())
    card.capabilities = ["forecast_oee", "predict_failure"]  # tamper after signing
    assert verify_card(card) is False


def test_expired_card_rejected():
    card = sign_card(_card(expiry=datetime.now(timezone.utc) - timedelta(days=1)))
    assert verify_card(card) is False


def test_revoked_card_rejected():
    card = sign_card(_card())
    assert verify_card(card, is_revoked=lambda pk: pk == card.public_key_b64) is False


def test_pinned_roots_enforced():
    card = sign_card(_card())
    assert verify_card(card, pinned_roots={card.public_key_b64}) is True   # pinned → OK
    assert verify_card(card, pinned_roots={"some-other-key"}) is False     # not pinned → refused
