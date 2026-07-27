"""Stage 35 (C6-R3 tail) — multi-turn dialogue memory: durable sliding-window session store + the grounding
invariant (history never substitutes for evidence; honest-empty still fires). DB-gated; honest no-op without a DB."""
from __future__ import annotations

import asyncio
import os
import uuid

import pytest

from conversation.session_store import append_turn, recent_turns, format_history

_HAVE_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))
requires_db = pytest.mark.skipif(not _HAVE_DB, reason="session store needs Postgres (DATABASE_URL)")


def _sid() -> str:
    return "t-" + uuid.uuid4().hex[:12]


@requires_db
def test_append_and_read_round_trip():
    sid = _sid()
    assert append_turn(sid, "user", "why did stage 3 go down?") is True
    assert append_turn(sid, "assistant", "Stage 3 torque anomaly [audit:seq=424].") is True
    turns = recent_turns(sid, window=6)
    assert [t["role"] for t in turns] == ["user", "assistant"]        # chronological
    assert turns[0]["content"].startswith("why did stage 3")


@requires_db
def test_sliding_window_keeps_only_last_n():
    sid = _sid()
    for i in range(5):
        append_turn(sid, "user", f"q{i}")
    turns = recent_turns(sid, window=2)
    assert len(turns) == 2
    assert [t["content"] for t in turns] == ["q3", "q4"]              # the two most recent, chronological


@requires_db
def test_empty_session_is_empty_not_fabricated():
    assert recent_turns(_sid(), window=6) == []                       # a fresh session has no turns (honest)


def test_append_and_read_are_honest_noops_without_db(monkeypatch):
    # Point the store at an unreachable DSN -> append returns False, recent_turns returns [] (never fabricates history).
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:nobody@127.0.0.1:59999/nope")
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    assert append_turn(_sid(), "user", "hi") is False
    assert recent_turns(_sid()) == []


def test_format_history_is_labelled_not_evidence():
    block = format_history([{"role": "user", "content": "why did stage 3 go down?"},
                            {"role": "assistant", "content": "torque anomaly"}])
    assert "NOT evidence" in block                                    # the block explicitly disclaims being a source
    assert "USER:" in block and "ASSISTANT:" in block
    assert format_history([]) == ""                                   # no history -> empty (no fabricated context)


@requires_db
def test_ask_honest_empty_still_fires_with_a_session_and_records_the_turn():
    """The grounding invariant: even inside a multi-turn session, an ungrounded question returns honest-empty, and the
    turn is still recorded (history is NOT a substitute for evidence)."""
    from conversation.ask import ask_factory
    sid = _sid()
    r = asyncio.run(ask_factory("what is the airspeed of a swallow", world=None, use_llm=False, session_id=sid))
    assert r["grounded"] is False
    assert r["answer"] == "I have no evidence for that."
    assert r["session_id"] == sid
    # the user Q + the honest-empty answer are both persisted (multi-turn works even for abstentions)
    turns = recent_turns(sid, window=6)
    assert [t["role"] for t in turns] == ["user", "assistant"]
    assert turns[1]["content"] == "I have no evidence for that."
