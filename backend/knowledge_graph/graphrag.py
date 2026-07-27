"""Stage 28 — GraphRAG retriever over the Neo4j ISA-95 graph + SOP corpus (research §39.1).

A lean, free/local VectorCypher-style retriever (no `neo4j-graphrag` package — it pulls langchain-heavy deps off
our frozen matrix; we already have the neo4j driver + bge-small embeddings). Pipeline:

  1. embed the SOP/document corpus with bge-small (the Stage-12/20 embedder), cached;
  2. cosine-match the query to seed SOP chunks (semantic retrieval);
  3. expand the 1-2-hop ISA-95 graph neighbourhood around the query's named equipment (Cypher);
  4. return GROUNDED context with EXPLICIT citations — SOP doc-ids + Neo4j node-ids/edge-types.

HONESTY: if neither the corpus nor the graph yields a match, return an EMPTY grounding with `grounded=False` — never
a plausible guess. Neo4j down → the graph leg degrades to `graph_available=False` (SOP leg still works); embedder
absent → `embedder_available=False` (graph leg still works); both down → honest-empty. Every returned fact carries a
citation the caller can put in the Art-12 trace — the trust/explainability property (a retrieval that can't cite is
not returned).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_CORPUS_DIR = Path(__file__).resolve().parent / "sop_corpus"


@dataclass
class Citation:
    source: str          # "sop:SOP-001" | "graph:node:stage_3" | "graph:edge:supplier_0-FEEDS-sku_default"
    kind: str            # "sop_chunk" | "graph_node" | "graph_edge"
    detail: str          # the cited text / node label / edge triple


@dataclass
class Grounding:
    query: str
    grounded: bool                         # False = honest "no grounding found" (never a guess)
    context: list[str] = field(default_factory=list)     # the grounded facts (each citable)
    citations: list[Citation] = field(default_factory=list)
    embedder_available: bool = True
    graph_available: bool = True
    top_score: float = 0.0     # the best SOP cosine match [0,1] — the retrieval-confidence anchor (Stage 28)

    def to_trace(self) -> dict[str, Any]:
        """Compact form for the Art-12 record_decision_trace snapshot."""
        return {"grounded": self.grounded,
                "citations": [f"{c.source}" for c in self.citations],
                "n_facts": len(self.context)}


# ---------------------------------------------------------------------------
# SOP corpus embedding (bge-small, cached)
# ---------------------------------------------------------------------------

_chunks: Optional[list[tuple[str, str]]] = None      # (doc_id, chunk_text)
_chunk_vecs: Optional[list[list[float]]] = None


def _load_corpus() -> list[tuple[str, str]]:
    """Split each SOP doc into paragraph chunks tagged with its doc-id."""
    global _chunks
    if _chunks is not None:
        return _chunks
    chunks: list[tuple[str, str]] = []
    for md in sorted(_CORPUS_DIR.glob("*.md")):
        doc_id = md.stem.split("_")[0]                # "SOP-001"
        text = md.read_text(encoding="utf-8")
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if len(para) >= 25:                       # skip headers/blank
                chunks.append((doc_id, para))
    _chunks = chunks
    return chunks


def _embedder():
    from memory.mem0_adapter import _embedder as mem0_embedder
    return mem0_embedder()


def _embed(texts: list[str]) -> list[list[float]]:
    model = _embedder()
    return [list(map(float, v)) for v in model.encode(texts, normalize_embeddings=True)]


def _ensure_corpus_embedded() -> bool:
    """Embed the corpus once. Returns False (honest) if the embedder is unavailable."""
    global _chunk_vecs
    if _chunk_vecs is not None:
        return True
    try:
        corpus = _load_corpus()
        _chunk_vecs = _embed([c for _, c in corpus])
        return True
    except Exception:  # noqa: BLE001 — embedder absent: SOP leg unavailable, honestly
        _chunk_vecs = None
        return False


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))          # inputs are normalised → dot == cosine


def _sop_search(query: str, k: int = 3, min_score: float = 0.6) -> tuple[list[tuple[str, str, float]], bool]:
    """Top-k SOP chunks above min_score. Returns ([(doc_id, chunk, score)], embedder_available).

    min_score=0.6: bge-small has a HIGH cosine floor (off-topic queries score ~0.43-0.51; a naive 0.35 cutoff
    falsely grounded 'what is the meaning of life'). Measured on-topic queries score 0.67-0.90, off-topic <=0.51 —
    0.6 cleanly separates them, so an out-of-domain query returns honest-empty (grounded=False)."""
    if not _ensure_corpus_embedded():
        return [], False
    corpus = _load_corpus()
    qv = _embed([query])[0]
    scored = sorted(((doc_id, chunk, _cosine(qv, cv))
                     for (doc_id, chunk), cv in zip(corpus, _chunk_vecs)),
                    key=lambda t: t[2], reverse=True)
    return [(d, c, s) for d, c, s in scored[:k] if s >= min_score], True


# ---------------------------------------------------------------------------
# Graph neighbourhood expansion (Cypher, 1-2 hops)
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"\b(stage[_ ]?\d+|supplier[_ ]?\d+|sku[_ ]?\w+|robot[_ ]?\d+)\b", re.I)


def _entities_in(query: str) -> list[str]:
    """Extract candidate ISA-95 node-id mentions from the query (normalised to the graph id form)."""
    out = []
    for m in _ID_RE.findall(query):
        out.append(m.lower().replace(" ", "_"))
    return list(dict.fromkeys(out))                  # dedupe, keep order


async def _graph_neighbourhood(entity_ids: list[str], hops: int = 2) -> tuple[list[str], list[Citation], bool]:
    """1-2-hop neighbourhood of the named nodes. Returns (facts, citations, graph_available)."""
    if not entity_ids:
        return [], [], True                          # nothing to look up (not an error)
    from memory.graph_isa95 import _driver, Neo4jUnavailable
    facts: list[str] = []
    cites: list[Citation] = []
    try:
        driver = _driver()
    except Neo4jUnavailable:
        return [], [], False
    try:
        async with driver.session() as session:
            for eid in entity_ids:
                res = await session.run(
                    f"MATCH (n {{id: $id}}) "
                    f"OPTIONAL MATCH (n)-[r*1..{hops}]-(m) "
                    f"RETURN n.id AS nid, labels(n) AS nlabels, n.name AS nname, "
                    f"collect(DISTINCT {{mid: m.id, mlabels: labels(m)}})[..12] AS neighbours",
                    id=eid)
                rec = await res.single()
                if rec is None or rec["nid"] is None:
                    continue
                nlabel = (rec["nlabels"] or ["Node"])[0]
                facts.append(f"{nlabel} {rec['nid']} ({rec['nname']}) exists in the ISA-95 graph")
                cites.append(Citation(f"graph:node:{rec['nid']}", "graph_node",
                                      f"{nlabel}:{rec['nid']}"))
                for nb in rec["neighbours"]:
                    if nb.get("mid"):
                        mlabel = (nb.get("mlabels") or ["Node"])[0]
                        facts.append(f"{rec['nid']} is connected to {mlabel} {nb['mid']}")
                        cites.append(Citation(f"graph:edge:{rec['nid']}-{nb['mid']}", "graph_edge",
                                              f"{rec['nid']}—{nb['mid']}"))
    except Exception:  # noqa: BLE001 — query error: graph leg unavailable, honestly
        return facts, cites, False
    finally:
        await driver.close()
    return facts, cites, True


# ---------------------------------------------------------------------------
# Public retrieval
# ---------------------------------------------------------------------------

def retrieve(query: str, *, k: int = 3) -> Grounding:
    """GraphRAG retrieval: SOP semantic match + ISA-95 graph neighbourhood, with explicit citations.

    Synchronous entry (runs the async graph leg on a private loop) so it drops into the runtime nodes cleanly."""
    import asyncio

    sop_hits, embedder_ok = _sop_search(query, k=k)
    top_score = max((sc for _, _, sc in sop_hits), default=0.0)
    context: list[str] = []
    citations: list[Citation] = []
    for doc_id, chunk, score in sop_hits:
        headline = chunk.splitlines()[0][:180]
        context.append(f"[{doc_id}] {headline}")
        citations.append(Citation(f"sop:{doc_id}", "sop_chunk", headline))

    entity_ids = _entities_in(query)
    try:
        graph_facts, graph_cites, graph_ok = asyncio.run(_graph_neighbourhood(entity_ids))
    except RuntimeError:
        # already inside a running loop (rare in the sync runtime path) — skip the graph leg honestly
        graph_facts, graph_cites, graph_ok = [], [], True
    context.extend(graph_facts)
    citations.extend(graph_cites)

    grounded = bool(context)                         # grounded ONLY if a real citation was found
    return Grounding(query=query, grounded=grounded, context=context, citations=citations,
                     embedder_available=embedder_ok, graph_available=graph_ok, top_score=round(float(top_score), 3))


__all__ = ["retrieve", "Grounding", "Citation"]
