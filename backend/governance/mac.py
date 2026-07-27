"""Stage 23 (G-030) — Bell-LaPadula mandatory access control (confidentiality). Research §33.4.

Each subject/object carries a SecurityLabel = (level: int, categories: frozenset[str]). The lattice partial order is
DOMINANCE: A dominates B  iff  A.level >= B.level  AND  B.categories ⊆ A.categories.

  - no-read-up  (simple security property): a subject may READ an object iff the SUBJECT dominates the OBJECT.
  - no-write-down (the ⋆-property):          a subject may WRITE an object iff the OBJECT dominates the SUBJECT.

This protects CONFIDENTIALITY (high data can't flow to low sinks). The functional-safety wrapper (Stage 17) is the
Biba INTEGRITY dual (no-write-up: an untrusted planner can't write a high-integrity actuator). Pure, deterministic,
DB-free logic; every allow/deny is best-effort audited to `audit_chain` (Art-12) without the decision depending on the DB.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Canonical levels (higher = more sensitive). Strings map to ints for ordering.
LEVELS = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3, "safety_critical": 4}


@dataclass(frozen=True)
class SecurityLabel:
    level: int
    categories: frozenset[str] = field(default_factory=frozenset)

    @staticmethod
    def of(level, categories=()) -> "SecurityLabel":
        lvl = LEVELS[level] if isinstance(level, str) else int(level)
        return SecurityLabel(lvl, frozenset(categories))

    def __str__(self) -> str:
        name = next((k for k, v in LEVELS.items() if v == self.level), str(self.level))
        cats = ",".join(sorted(self.categories)) or "-"
        return f"{name}[{cats}]"


@dataclass(frozen=True)
class MacDecision:
    allow: bool
    rule: str            # "no-read-up" | "no-write-down"
    reason: str
    audited: bool = False

    def __bool__(self) -> bool:
        return self.allow


def dominates(a: SecurityLabel, b: SecurityLabel) -> bool:
    """A dominates B: A is at least as high AND A carries all of B's categories (level-dominance + category-containment)."""
    return a.level >= b.level and b.categories <= a.categories


def _audit(action: str, subject: SecurityLabel, obj: SecurityLabel, allow: bool, actor: str) -> bool:
    """Best-effort record to audit_chain. Returns True if recorded. Never fakes a record; never blocks the decision."""
    try:
        from memory.audit_chain import append
        append(actor or "governance:mac", f"mac.{action}",
               {"subject": str(subject), "object": str(obj), "allow": bool(allow)})
        return True
    except Exception:  # noqa: BLE001 - DB/crypto unavailable -> honest: decision stands, audited=False
        return False


def can_read(subject: SecurityLabel, obj: SecurityLabel, *, actor: str = "", audit: bool = True) -> MacDecision:
    """no-read-up: allowed iff the SUBJECT dominates the OBJECT."""
    allow = dominates(subject, obj)
    reason = (f"subject {subject} dominates object {obj}" if allow
              else f"READ-UP blocked: subject {subject} does not dominate object {obj}")
    audited = _audit("read", subject, obj, allow, actor) if audit else False
    return MacDecision(allow, "no-read-up", reason, audited)


def can_write(subject: SecurityLabel, obj: SecurityLabel, *, actor: str = "", audit: bool = True) -> MacDecision:
    """no-write-down (⋆-property): allowed iff the OBJECT dominates the SUBJECT."""
    allow = dominates(obj, subject)
    reason = (f"object {obj} dominates subject {subject}" if allow
              else f"WRITE-DOWN blocked: object {obj} does not dominate subject {subject}")
    audited = _audit("write", subject, obj, allow, actor) if audit else False
    return MacDecision(allow, "no-write-down", reason, audited)


def require_read(subject: SecurityLabel, obj: SecurityLabel, *, actor: str = "") -> None:
    d = can_read(subject, obj, actor=actor)
    if not d.allow:
        raise MacViolation(d.reason)


def require_write(subject: SecurityLabel, obj: SecurityLabel, *, actor: str = "") -> None:
    d = can_write(subject, obj, actor=actor)
    if not d.allow:
        raise MacViolation(d.reason)


class MacViolation(PermissionError):
    """Raised when a Bell-LaPadula property is violated — never swallowed, never faked."""


__all__ = ["SecurityLabel", "MacDecision", "MacViolation", "LEVELS",
           "dominates", "can_read", "can_write", "require_read", "require_write"]
