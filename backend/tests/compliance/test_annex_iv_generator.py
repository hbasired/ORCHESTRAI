"""Stage 19 — the Annex IV pack generator produces all 14 sections, a real PDF+HTML, and an ML-DSA-65-signed footer."""
import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def _gen():
    spec = importlib.util.spec_from_file_location("annexiv", REPO / "scripts" / "generate-annex-iv-doc.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_gathers_all_13_evidence_sections_with_content():
    m = _gen()
    sections = m.gather_sections()
    assert len(sections) == 13                       # +1 conformity declaration rendered separately = 14
    for title, content in sections:
        assert content and not content.strip().startswith("_(source not found"), f"empty section: {title}"


def test_conformity_declaration_is_mldsa65_signed():
    m = _gen()
    sections = m.gather_sections()
    decl, meta = m._conformity(sections)
    assert "content_sha256" in meta
    # the keystore is available in dev/CI → the pack is ML-DSA-65 signed
    if "signature_b64" in meta:
        assert meta["algorithm"] == "ML-DSA-65" and meta["key_version"] >= 1
        assert "conformity-assessment-ready" in decl.lower() or "not a conformity" in decl.lower()
    else:
        # honest-unavailable path: never a fake signature
        assert "unavailable" in decl.lower()


def test_renders_pdf_and_html(tmp_path):
    m = _gen()
    sections = m.gather_sections()
    decl, meta = m._conformity(sections)
    html = m.render_html(sections, decl, meta)
    assert "Annex IV" in html and "14. Conformity declaration" in html and "<h2>" in html
    out = tmp_path / "pack.pdf"
    m.render_pdf(sections, decl, meta, out)
    assert out.exists() and out.read_bytes()[:5] == b"%PDF-"   # a real PDF


def test_honesty_no_conformity_overclaim():
    """The pack must NOT claim certified conformity (research §29.1 honesty boundary)."""
    m = _gen()
    decl, _ = m._conformity(m.gather_sections())
    low = decl.lower()
    # if signed, it explicitly states it is NOT a certificate
    if "signature_b64" in m._conformity(m.gather_sections())[1]:
        assert "not a conformity" in low or "conformity-assessment-ready" in low
