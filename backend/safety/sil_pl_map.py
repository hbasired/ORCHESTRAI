"""Stage 17 — IEC 61508 SIL ↔ ISO 13849-1 Performance Level (PL) mapping (KB_17; research §27.1).

The two functional-safety regimes co-exist on a line: ISO 13849-1:2023 (PL a–e, Category B/1–4) for machinery and
IEC 61508 (SIL 1–4) for E/E/PE systems. ISO 13849-1 Annex gives the correspondence. The 2025 robot rule (ISO 10218-1):
**PL d / SIL 2** for Class II collaborative robots, **PL b / SIL 1** permitted for Class I.
"""
from __future__ import annotations

# ISO 13849-1 Table — PL -> the equivalent IEC 61508 SIL (PL a has no SIL equivalent; PL e maps to SIL 3).
PL_TO_SIL = {"a": 0, "b": 1, "c": 1, "d": 2, "e": 3}
SIL_TO_PL = {0: "a", 1: "c", 2: "d", 3: "e", 4: "e"}  # representative inverse (SIL1 spans PL b/c → 'c')

# ISO 10218-1:2025 robot-class minimums.
ROBOT_CLASS_MIN = {
    "I": {"pl": "b", "sil": 1},    # Class I (lower-risk)
    "II": {"pl": "d", "sil": 2},   # Class II (collaborative / higher-risk)
}


def sil_to_pl(sil: int) -> str:
    if sil not in SIL_TO_PL:
        raise ValueError(f"SIL must be 0..4, got {sil}")
    return SIL_TO_PL[sil]


def pl_to_sil(pl: str) -> int:
    pl = pl.lower()
    if pl not in PL_TO_SIL:
        raise ValueError(f"PL must be a..e, got {pl!r}")
    return PL_TO_SIL[pl]


def meets_robot_class(robot_class: str, sil: int) -> bool:
    """True if `sil` meets the ISO 10218-1:2025 minimum for the given robot class (I/II)."""
    rc = ROBOT_CLASS_MIN.get(robot_class.upper())
    if rc is None:
        raise ValueError(f"robot_class must be 'I' or 'II', got {robot_class!r}")
    return sil >= rc["sil"]


__all__ = ["PL_TO_SIL", "SIL_TO_PL", "ROBOT_CLASS_MIN", "sil_to_pl", "pl_to_sil", "meets_robot_class"]
