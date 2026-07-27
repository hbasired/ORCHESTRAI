#!/usr/bin/env python3
"""Stage 19 — EU AI Act Annex IV technical-documentation pack generator (KB_18 §"Annex IV ... generator").

Assembles the 14 KB_18 sections from LIVE repo evidence into an HTML bundle + a PDF, stamped with an ML-DSA-65-signed
conformity-declaration footer (over the pack content hash + the audit_chain head). HONESTY (research §29.1): this is a
**conformity-assessment-READY technical-documentation bundle** (EU AI Act Art-11 / Annex IV evidence assembly), NOT a
claim of certified conformity — ISO/IEC 42001 is operational governance (not harmonised), and no harmonised AI-Act
standard is published yet, so there is no presumption of conformity. Actual conformity = Stage 23 dry-run + notified body.

Usage: python scripts/generate-annex-iv-doc.py [--out compliance/annex-iv-packs]
Outputs: <out>/<YYYY-MM-DD>_annex_iv.{html,pdf} + <out>/latest.{html,pdf}
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))


# ---- evidence gatherers ------------------------------------------------------

def _read(path: Path, limit: int = 0) -> str:
    if not path.exists():
        return f"_(source not found: {path.relative_to(REPO)})_"
    txt = path.read_text(encoding="utf-8", errors="replace")
    return txt if not limit or len(txt) <= limit else txt[:limit] + "\n…(truncated; full source in repo)…"


def _first_para(path: Path, n: int = 1200) -> str:
    return _read(path, n)


def _audit_summary() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not url:
        return "audit_chain: DB not reachable at generation time — run `scripts/verify-audit-chain.py` against the live DB."
    try:
        import psycopg2
        c = psycopg2.connect(url); cur = c.cursor()
        cur.execute("SELECT count(*), min(ts), max(ts), max(seq) FROM audit_chain")
        n, tmin, tmax, head_seq = cur.fetchone()
        cur.execute("SELECT key_version, count(*) FROM audit_chain GROUP BY key_version ORDER BY key_version")
        kv = cur.fetchall()
        cur.execute("SELECT encode(hash,'hex') FROM audit_chain WHERE seq=%s", (head_seq,))
        head = cur.fetchone()[0]
        c.close()
        return (f"- Rows: **{n}** (seq 1..{head_seq})\n- Time range: {tmin} → {tmax}\n"
                f"- Key versions: {', '.join(f'v{k}×{cnt}' for k, cnt in kv)} (v0 = pre-Stage-13.5 placeholder; v≥1 = ML-DSA-65)\n"
                f"- Head hash: `{head}`\n- Integrity: verify with `scripts/verify-audit-chain.py` (load-bearing — fails on any non-verifying post-cutover row).")
    except Exception as e:  # noqa: BLE001
        return f"audit_chain summary unavailable: {type(e).__name__}"


def _index(glob_dir: Path, pattern: str) -> str:
    items = sorted(glob_dir.glob(pattern))
    if not items:
        return "_(none)_"
    return "\n".join(f"- `{p.name}`" for p in items)


def _evals() -> str:
    import json
    rows = []
    base = REPO / "backend" / "training" / "evals"
    for rj in sorted(base.glob("*/results.json")):                       # model eval results
        try:
            d = json.loads(rj.read_text(encoding="utf-8"))
            keys = {k: d[k] for k in list(d)[:6]}
            rows.append(f"- **{rj.parent.name}**: {keys}")
        except Exception:  # noqa: BLE001
            rows.append(f"- {rj.parent.name}: (unreadable)")
    for rj in sorted((base / "results").glob("*.json")):                 # Stage-20 red-team / agentic results
        if rj.stem == "summary":                                         # summary is a nested roll-up of the per-suite files
            continue
        try:
            d = json.loads(rj.read_text(encoding="utf-8"))
            keys = {k: d[k] for k in list(d) if k in (
                "suite", "detection_rate", "false_positive_rate", "block_rate", "input_tier_rate",
                "tool_selection_quality", "action_completion", "reasoning_coherence", "available")}
            rows.append(f"- **redteam/{rj.stem}**: {keys}")
        except Exception:  # noqa: BLE001
            rows.append(f"- redteam/{rj.stem}: (unreadable)")
    return "\n".join(rows) if rows else "_(no eval results found)_"


def gather_sections() -> list[tuple[str, str]]:
    C = REPO / "compliance"
    K = REPO / "knowledge-base"
    return [
        ("1. System description", _first_para(REPO / "PRD-ai-embodied-agent-v3.md", 2000)),
        ("2. Intended purpose", _first_para(K / "KB_26_Product_Market_Strategy.md", 1500)),
        ("3. System architecture", _first_para(K / "KB_01_System_Architecture.md", 1800) + "\n\n### Coordination\n"
         + _first_para(K / "KB_06_Agent_Coordination_Protocol.md", 1200)),
        ("4. Risk management (Art. 9)", _read(C / "risk-register.md", 6000)),
        ("5. Data governance (Art. 10)", _index(REPO / "data" / "datasets", "*/CARD.md")
         + "\n\n" + _first_para(K / "KB_03_Datasets_Catalog.md", 1500)),
        ("6. Model documentation", "Model cards (full text in `compliance/model-cards/`):\n"
         + _index(C / "model-cards", "*.md")),
        ("7. Performance / evals", _evals()),
        ("8. Record-keeping (Art. 12)", _audit_summary()),
        ("9. Decision logs (ADRs)", "Append-only architectural decision records (`compliance/decision-logs/`):\n"
         + _index(C / "decision-logs", "*.md")),
        ("10. Human oversight (Art. 14)", _read(C / "human-oversight.md", 4000)),
        ("11. Human-in-use & post-market monitoring (Art. 26/72)",
         _read(C / "incident-playbook.md", 3000)
         + "\n\n### Post-market monitoring plan (Art. 72 — part of Annex IV)\n"
         + _read(C / "post-market-monitoring-plan.md", 4500)),
        ("12. Standards compliance", _first_para(K / "KB_12_Standards_Map.md", 2500) + "\n\n### Functional safety\n"
         + _first_para(K / "KB_17_Functional_Safety_Wrapper.md", 1500)),
        ("13. Cybersecurity (Art. 15)", _first_para(K / "KB_13_PQC_Crypto_Strategy.md", 2500)),
    ]


# ---- conformity declaration (ML-DSA-65 signed) -------------------------------

def _conformity(sections: list[tuple[str, str]]) -> tuple[str, dict]:
    import base64
    body = "\n\n".join(f"## {t}\n{c}" for t, c in sections)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    meta = {"generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(), "content_sha256": digest}
    try:
        from crypto import pqc_signing
        sig = pqc_signing.sign(bytes.fromhex(digest))
        meta.update({"algorithm": pqc_signing.algorithm(), "key_version": pqc_signing.active_key_version(),
                     "signature_b64": base64.b64encode(sig).decode("ascii"),
                     "public_key_b64": base64.b64encode(pqc_signing.public_key()).decode("ascii")})
        signed = (f"This technical-documentation pack is sealed with a **{meta['algorithm']}** signature "
                  f"(key v{meta['key_version']}) over its SHA-256 content hash `{digest}`.\n\n"
                  f"`signature_b64`: {meta['signature_b64'][:80]}…\n\n"
                  f"**Honesty:** this bundle is *conformity-assessment-ready* Annex IV / Art-11 technical documentation "
                  f"— NOT a conformity certificate. ISO/IEC 42001 is an operational governance framework (not harmonised "
                  f"under the Act); no harmonised AI-Act standard is yet published. Actual conformity = Stage 23 "
                  f"dry-run + a notified body.")
    except Exception as e:  # noqa: BLE001
        meta["signature_error"] = type(e).__name__
        signed = f"_(conformity signature unavailable: {type(e).__name__}; content_sha256={digest})_"
    return signed, meta


# ---- renderers ---------------------------------------------------------------

def _ascii(s: str) -> str:
    """Latin-1-safe text for fpdf2 core fonts (replace common unicode)."""
    for a, b in [("—", "-"), ("–", "-"), ("→", "->"), ("←", "<-"), ("≤", "<="), ("≥", ">="), ("’", "'"),
                 ("“", '"'), ("”", '"'), ("•", "*"), ("×", "x"), ("…", "..."), ("∈", "in"), ("⟂", "perp")]:
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def render_html(sections, conformity, meta) -> str:
    import html as _h
    parts = ["<!DOCTYPE html><html><head><meta charset='utf-8'><title>Annex IV Technical Documentation</title>",
             "<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;line-height:1.5;padding:0 1rem}"
             "h1{border-bottom:2px solid #333}h2{margin-top:2rem;color:#0b5}pre{white-space:pre-wrap;background:#f6f8fa;"
             "padding:.6rem;border-radius:6px;font-size:.85em}.meta{color:#666;font-size:.9em}</style></head><body>",
             "<h1>EU AI Act Annex IV — Technical Documentation Pack</h1>",
             f"<p class='meta'>Generated {meta['generated_at']} · content sha256 {meta['content_sha256'][:16]}… · "
             f"vendor-neutral EU-AI-Act-grade agent control plane</p>"]
    for t, c in sections:
        parts.append(f"<h2>{_h.escape(t)}</h2><pre>{_h.escape(c)}</pre>")
    parts.append(f"<h2>14. Conformity declaration</h2><pre>{_h.escape(conformity)}</pre>")
    parts.append("</body></html>")
    return "".join(parts)


def _wrap_tokens(s: str, maxlen: int = 90) -> str:
    """Break whitespace-free runs longer than maxlen (base64 sigs / URLs / hex hashes) so fpdf2 can line-wrap them."""
    out = []
    for tok in s.split(" "):
        while len(tok) > maxlen:
            out.append(tok[:maxlen])
            tok = tok[maxlen:]
        out.append(tok)
    return " ".join(out)


def _pdf_safe(s: str) -> str:
    return _wrap_tokens(_ascii(s))


def render_pdf(sections, conformity, meta, out_pdf: Path) -> None:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def cell(text: str, size: int, style: str = "") -> None:
        pdf.set_x(pdf.l_margin)                       # reset cursor to left margin (avoid width-drift)
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(0, 5 + size // 4, _pdf_safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    cell("EU AI Act Annex IV - Technical Documentation Pack", 16, "B")
    cell(f"Generated {meta['generated_at']} | content sha256 {meta['content_sha256']}", 9)
    for t, c in list(sections) + [("14. Conformity declaration", conformity)]:
        pdf.ln(2)
        cell(t, 12, "B")
        cell(c[:9000], 9)                            # cap each section's rendered text
    pdf.output(str(out_pdf))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="compliance/annex-iv-packs")
    args = ap.parse_args(argv)
    out_dir = REPO / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    sections = gather_sections()
    conformity, meta = _conformity(sections)
    # completeness gate: all 13 evidence sections must have non-trivial content (+ section 14 declaration)
    missing = [t for t, c in sections if not c or c.strip().startswith("_(source not found")]
    if missing:
        print(f"INCOMPLETE: missing evidence for sections: {missing}")
        return 1

    date = _dt.date.today().isoformat()
    html = render_html(sections, conformity, meta)
    for name in (f"{date}_annex_iv.html", "latest.html"):
        (out_dir / name).write_text(html, encoding="utf-8")
    try:
        for name in (f"{date}_annex_iv.pdf", "latest.pdf"):
            render_pdf(sections, conformity, meta, out_dir / name)
        pdf_note = f"{date}_annex_iv.pdf + latest.pdf"
    except Exception as e:  # noqa: BLE001
        pdf_note = f"PDF skipped ({type(e).__name__})"
        print(f"::warning::PDF render failed: {e}")

    print(f"Annex IV pack generated: 14 sections, {len(sections)+1} incl. conformity declaration")
    print(f"  HTML: {date}_annex_iv.html + latest.html")
    print(f"  PDF:  {pdf_note}")
    print(f"  Signed: {meta.get('algorithm', 'UNSIGNED')} key v{meta.get('key_version', '?')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
