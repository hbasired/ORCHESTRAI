"""Stage 17 — the safety-contract DSL (KB_17 §"Safety contract DSL").

A `SafetyContract` is the formal gate every actuator-bound action must reference: preconditions (checked before),
invariants (must hold at validation + during execution), postconditions (checked after), the `sil` level (IEC 61508),
the mapped `iso_clauses`, and the `fail_safe_path` (IEC 61800-5-2 safe-motion function on failure). The LLM never
defines the SIL or edits a contract at runtime (KB_17 §"What the LLM never does"); contracts are static, code-defined.
"""
from __future__ import annotations

from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

FailSafePath = Literal["STO", "SS1", "SS2", "SLS", "operator_confirm", "no_action"]


class Action(BaseModel):
    """An actuator-bound action proposed by a planner. References a named contract; carries the actuator + params."""
    contract: str                      # the SafetyContract.name this action is gated by
    actuator: str                      # e.g. "vda5050.order", "opcua.write", "sparkplug.dcmd", "amr.move", "conveyor"
    params: dict[str, Any] = Field(default_factory=dict)
    target: Optional[str] = None       # equipment / robot / zone id


class Precondition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    description: str
    check: Callable[[dict], bool]      # (world_state) -> bool ; must be True to proceed


class Invariant(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    description: str
    check: Callable[[dict], bool]      # (world_state) -> bool ; must hold continuously


class Postcondition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    description: str
    check: Callable[[dict, dict], bool]  # (world_state_before, world_state_after) -> bool


class SafetyContract(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    sil: Literal[0, 1, 2, 3, 4]
    iso_clauses: list[str] = Field(default_factory=list)
    preconditions: list[Precondition] = Field(default_factory=list)
    postconditions: list[Postcondition] = Field(default_factory=list)
    invariants: list[Invariant] = Field(default_factory=list)
    fail_safe_path: FailSafePath = "no_action"


class Decision(BaseModel):
    """The validator's verdict. `route` is where an ALLOWED action goes (KB_17 SIL routing)."""
    allow: bool
    route: Literal["sil_bridge", "operator_confirm", "direct", "blocked"]
    reason: str
    contract: str
    sil: int = 0
    fail_safe_path: Optional[FailSafePath] = None
    failed_checks: list[str] = Field(default_factory=list)
    # Stage 33 (G-075): the unforgeable, action-bound, time-limited capability token minted by validate() on ALLOW.
    # sil_bridge.execute() redeems it; a forged Decision without a valid+fresh token (and no contract) is rejected.
    token: Optional[str] = None
    nonce: Optional[str] = None
    issued_at: Optional[float] = None


__all__ = ["Action", "Precondition", "Invariant", "Postcondition", "SafetyContract", "Decision", "FailSafePath"]
