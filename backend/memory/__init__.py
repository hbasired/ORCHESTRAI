"""Stage 12 — agent memory layer (KB_14).

Five layers: working (LangGraph checkpointer, Stage 11), **episodic/semantic** (`mem0_adapter` — pgvector,
namespace-isolated), **semantic graph** (`graph_isa95` — Neo4j ISA-95), procedural (DVC), and **audit**
(`audit_chain` — append-only, SHA-256 hash-chained, ML-DSA-65 signed at Stage 13.5). `letta_adapter` is the opt-in
long-horizon episodic backend (feature-flagged off by default).

All writes go through these adapters (never the LLM directly); the adapters namespace-check, validate, and — for
decisions — append to `audit_chain` (KB_14 §"What this design refuses to do").
"""
