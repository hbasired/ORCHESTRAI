#!/usr/bin/env python3
"""Stage 18 — SLH-DSA-SHA2-128s sign a long-trust bundle (firmware image / policy bundle / model-card attestation).

FIPS 205 (hash-based, 10-year trust horizon) via OpenSSL 3.5 (`backend/crypto/pqc_slh_dsa.py`). Two modes:
  - default (detached): writes `<file>.slhdsa.sig` + `<file>.attestation.json` (sha256 + sig + signer public key); the
    bundle is unchanged. For firmware images / policy bundles.
  - `--model-card`: appends a signed `<!-- SLH-DSA attestation -->` footer to a model card (signs the body above the
    footer marker — like the ADR signer), so the card carries its own long-trust attestation.

Usage:
  python scripts/sign-firmware-bundle.py <file> [--alias firmware-policy]
  python scripts/sign-firmware-bundle.py --model-card compliance/model-cards/<model>.md
  python scripts/sign-firmware-bundle.py --verify <file>          # verify a detached signature/attestation
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

_FOOTER = "<!-- SLH-DSA-SHA2-128s ATTESTATION (managed by scripts/sign-firmware-bundle.py) -->"


def _slh():
    from crypto import pqc_slh_dsa
    return pqc_slh_dsa


def sign_detached(path: str, alias: str = "firmware-policy") -> dict:
    slh = _slh()
    data = Path(path).read_bytes()
    sig = slh.sign(data, alias)
    pub = slh.public_key(alias)
    att = {"file": os.path.basename(path), "sha256": hashlib.sha256(data).hexdigest(),
           "algorithm": slh.ALGORITHM, "alias": alias,
           "signature_b64": base64.b64encode(sig).decode("ascii"),
           "public_key_pem_b64": base64.b64encode(pub).decode("ascii")}
    Path(path + ".slhdsa.sig").write_bytes(sig)
    Path(path + ".attestation.json").write_text(json.dumps(att, indent=2), encoding="utf-8")
    if not slh.verify(data, sig, public_key_pem=pub):
        raise SystemExit("self-verify FAILED after signing")
    return att


def sign_model_card(path: str, alias: str = "firmware-policy") -> dict:
    slh = _slh()
    text = Path(path).read_text(encoding="utf-8")
    body = text.split("\n" + _FOOTER)[0].rstrip() + "\n"     # content above any existing footer
    sig = slh.sign(body.encode("utf-8"), alias)
    pub = slh.public_key(alias)
    footer = (f"\n{_FOOTER}\n"
              f"<!-- algorithm: {slh.ALGORITHM} -->\n"
              f"<!-- sha256:    {hashlib.sha256(body.encode()).hexdigest()} -->\n"
              f"<!-- signature_b64: {base64.b64encode(sig).decode('ascii')} -->\n"
              f"<!-- public_key_pem_b64: {base64.b64encode(pub).decode('ascii')} -->\n")
    Path(path).write_text(body + footer, encoding="utf-8")
    return {"file": os.path.basename(path), "algorithm": slh.ALGORITHM, "signed": True}


def verify_detached(path: str) -> bool:
    slh = _slh()
    att = json.loads(Path(path + ".attestation.json").read_text(encoding="utf-8"))
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != att["sha256"]:
        return False
    return slh.verify(data, base64.b64decode(att["signature_b64"]),
                      public_key_pem=base64.b64decode(att["public_key_pem_b64"]))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--alias", default="firmware-policy")
    ap.add_argument("--model-card", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args(argv)
    try:
        from crypto import pqc_slh_dsa
        if not pqc_slh_dsa.openssl_supports_slh_dsa():
            print("REFUSE: OpenSSL >= 3.5 with SLH-DSA not available (FIPS 205).")
            return 2
        if args.verify:
            ok = verify_detached(args.path)
            print(f"{'OK' if ok else 'FAIL'}: SLH-DSA attestation for {args.path}")
            return 0 if ok else 1
        out = sign_model_card(args.path, args.alias) if args.model_card else sign_detached(args.path, args.alias)
        print(f"Signed ({out['algorithm']}): {args.path}")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
