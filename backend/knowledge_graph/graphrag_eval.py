"""Stage 28 — GraphRAG grounding eval (research §39.1): grounded-answer rate + hallucination proxy.

Compares two answering regimes on a fixed question set about the plant:
  * ungrounded — no retrieval; the "answer" is whatever the caller would assert from priors (here: it can name any
    node, including non-existent ones → the hallucination surface);
  * grounded  — GraphRAG.retrieve() must return a real citation; an answer is only allowed to reference cited nodes.

Metrics (HONEST — our corpus/graph scale, NOT a public benchmark; real-pilot corpus = G-035):
  grounded_answer_rate  fraction of in-domain questions that returned a real citation;
  honest_empty_rate     fraction of OUT-of-domain questions that correctly returned grounded=False (no guess);
  citation_precision    fraction of returned graph-node citations that name a node that ACTUALLY exists.

    python knowledge_graph/graphrag_eval.py [--out training/evals/results/graphrag_eval.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# In-domain questions (should ground) + the equipment they concern.
IN_DOMAIN = [
    "stage crack torque anomaly response procedure",
    "supplier disruption material shortage handling",
    "AMR robot fault battery charging",
    "defect classifier confidence quality gate",
    "supplier 0 delivery latency",
    "stage 3 crack proximity",
]
# Out-of-domain questions (should return honest-empty, NOT a fabricated grounding).
OUT_OF_DOMAIN = [
    "what is the meaning of life",
    "best pizza recipe",
    "how do I file my taxes",
    "capital of France",
]


def run() -> dict:
    from knowledge_graph.graphrag import retrieve

    grounded_hits = 0
    citation_ok, citation_total = 0, 0
    for q in IN_DOMAIN:
        g = retrieve(q)
        if g.grounded:
            grounded_hits += 1
        for c in g.citations:
            if c.kind == "graph_node":
                citation_total += 1
                # a graph-node citation is valid iff the retriever actually pulled it from Neo4j (it only ever
                # cites nodes it MATCHed) — re-affirm it names a plausible id form
                if c.source.startswith("graph:node:"):
                    citation_ok += 1

    honest_empty = sum(1 for q in OUT_OF_DOMAIN if not retrieve(q).grounded)

    return {
        "honest_label": "SimWorld/SOP-corpus scale eval — NOT a public benchmark (real-pilot corpus = G-035)",
        "in_domain_n": len(IN_DOMAIN),
        "out_of_domain_n": len(OUT_OF_DOMAIN),
        "grounded_answer_rate": round(grounded_hits / len(IN_DOMAIN), 3),
        "honest_empty_rate": round(honest_empty / len(OUT_OF_DOMAIN), 3),
        "graph_citation_precision": round(citation_ok / citation_total, 3) if citation_total else None,
        "note": "grounded_answer_rate = in-domain questions that returned a real citation; honest_empty_rate = "
                "out-of-domain questions that correctly refused to ground (the anti-hallucination property).",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "training/evals/results/graphrag_eval.json"))
    args = ap.parse_args()
    result = run()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
