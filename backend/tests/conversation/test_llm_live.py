"""Stage 29 — LIVE free-LLM path (Groq->Ollama, Rule 9). Gated on a configured key + the embedder so CI without
them skips cleanly; when enabled it proves the LLM genuinely synthesizes grounded, cited answers and parses NL into
the validated schema — not just the deterministic fallback."""
from __future__ import annotations

import asyncio
import os

import pytest

def _have_llm() -> bool:
    if os.environ.get("GROQ_API_KEY") or os.environ.get("OLLAMA_BASE_URL"):
        return True
    try:  # the key is normally loaded from backend/.env via settings, not the OS env
        from config import settings
        return bool(getattr(settings, "groq_api_key", None))
    except Exception:  # noqa: BLE001
        return False


_HAVE_LLM = _have_llm()
_HAVE_EMBED = os.environ.get("MEM0_EMBED_MODEL") is not None

live = pytest.mark.skipif(not (_HAVE_LLM and _HAVE_EMBED),
                          reason="needs a live free LLM (GROQ_API_KEY/Ollama) + the embedder (MEM0_EMBED_MODEL)")


@live
def test_live_ask_is_grounded_and_cites_real_handles():
    from conversation.ask import ask_factory
    r = asyncio.run(ask_factory("what is the procedure for a stage torque anomaly / crack risk?", use_llm=True))
    assert r["grounded"] is True
    assert r["llm"] in ("groq", "gemini", "ollama")
    # the LLM answer must cite at least one real evidence handle (SOP id or audit seq).
    assert any(h.startswith(("sop:", "audit:", "node:", "edge:", "graph:")) for h in r["citations"])


@live
def test_live_nl_parse_into_validated_schema():
    from conversation.nl_inject import parse_incident, INCIDENT_TYPES
    inc, method = asyncio.run(parse_incident(
        "the number 3 welding cell is vibrating and overheating, urgent", use_llm=True))
    assert method == "llm"
    assert inc is not None and inc.type in INCIDENT_TYPES
    assert inc.target_id == 3
