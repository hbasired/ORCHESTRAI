"""Stage 17 — a tiny declarative behaviour-tree executor (KB_17 §"Self-Healing" layer 2).

Robot self-repair routines are authored as YAML behaviour trees (`behavior_trees/<robot_class>.yaml`) — Sequence /
Selector / Condition / Action nodes — and ticked against a blackboard (+ a registry of named condition/action
callables). Deterministic, dependency-light (pyyaml only). Returns SUCCESS / FAILURE / RUNNING per BT semantics.
"""
from __future__ import annotations

import enum
from pathlib import Path
from typing import Any, Callable

_TREES_DIR = Path(__file__).resolve().parent / "behavior_trees"


class Status(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"


class BehaviorTree:
    """Executes a YAML-defined tree. `conditions`/`actions` map node `ref` names to callables `(blackboard)->bool`."""

    def __init__(self, spec: dict, conditions: dict[str, Callable[[dict], bool]],
                 actions: dict[str, Callable[[dict], bool]]) -> None:
        self.spec = spec
        self.name = spec.get("name", "behavior_tree")
        self.conditions = conditions
        self.actions = actions
        self.trace: list[tuple[str, str]] = []   # (node, status) per tick — for audit/inspection

    @classmethod
    def from_yaml(cls, path: str | Path, conditions, actions) -> "BehaviorTree":
        import yaml
        spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(spec, conditions, actions)

    @classmethod
    def for_robot_class(cls, robot_class: str, conditions, actions) -> "BehaviorTree":
        return cls.from_yaml(_TREES_DIR / f"{robot_class}.yaml", conditions, actions)

    def tick(self, blackboard: dict[str, Any]) -> Status:
        self.trace = []
        return self._tick_node(self.spec["root"], blackboard)

    def _tick_node(self, node: dict, bb: dict) -> Status:
        ntype = node["type"]
        if ntype == "sequence":
            status = Status.SUCCESS
            for child in node["children"]:
                status = self._tick_node(child, bb)
                if status != Status.SUCCESS:
                    break
            self.trace.append((node.get("name", "sequence"), status.value))
            return status
        if ntype == "selector":
            status = Status.FAILURE
            for child in node["children"]:
                status = self._tick_node(child, bb)
                if status == Status.SUCCESS:
                    break
            self.trace.append((node.get("name", "selector"), status.value))
            return status
        if ntype == "condition":
            ok = bool(self.conditions[node["ref"]](bb))
            st = Status.SUCCESS if ok else Status.FAILURE
            self.trace.append((node["ref"], st.value))
            return st
        if ntype == "action":
            ok = bool(self.actions[node["ref"]](bb))
            st = Status.SUCCESS if ok else Status.FAILURE
            self.trace.append((node["ref"], st.value))
            return st
        raise ValueError(f"unknown behaviour-tree node type: {ntype!r}")


__all__ = ["BehaviorTree", "Status"]
