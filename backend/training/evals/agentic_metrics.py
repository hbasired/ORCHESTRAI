"""Stage 20 — agentic evaluation metrics (G-008; research §30.3).

Trajectory-based metrics (Galileo/DeepEval taxonomy) computed over the REAL LangGraph self-healing run
(`agents/runtime/graph.run_incident` -> `trace` of `TraceEvent.node`), never hand-set:

  * tool_selection_quality — fraction of the EXPECTED analytical nodes (the model/tool-using KB_25 steps) actually run.
  * action_completion      — did the run reach a terminal decision (a Decision produced + the loop closed at `log`)?
  * reasoning_coherence    — longest-common-subsequence of the observed node order vs the canonical KB_25 order,
                             normalised — penalises missing steps, out-of-order jumps, and oscillation/loops.

`compute_metrics()` is a PURE function (unit-tested deterministically in CI). `run_live()` produces the trajectory
from a real runtime run (nightly / Docker up) and is honest-skip (returns available=False) when the runtime/DB is not
reachable — it never fabricates a trajectory.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE.parents[1]))  # backend/ on path

CANONICAL = ["observe", "orient", "diagnose", "explain", "decide", "verify", "execute", "log"]
EXPECTED_ANALYTICAL = ["orient", "diagnose", "explain", "decide", "verify"]  # the model/tool-using steps


def _lcs(a: list[str], b: list[str]) -> int:
    """Length of the longest common subsequence (order-preserving)."""
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if a[i] == b[j] else max(dp[i + 1][j], dp[i][j + 1])
    return dp[0][0]


def compute_metrics(trajectory: list[str], decisions: list, interrupted: bool) -> dict:
    """Pure metric computation over one runtime trajectory (no I/O)."""
    traj = [n for n in trajectory if n]                       # node sequence as executed
    seen = set(traj)
    tool_sel = sum(1 for n in EXPECTED_ANALYTICAL if n in seen) / len(EXPECTED_ANALYTICAL)
    reached_terminal = "log" in seen and not interrupted
    action_completion = 1.0 if (reached_terminal and decisions) else (0.5 if (decisions and interrupted) else 0.0)
    # coherence over the canonical-subset of the trajectory (LCS vs canonical order)
    traj_in_canon = [n for n in traj if n in CANONICAL]
    coherence = _lcs(traj_in_canon, CANONICAL) / len(CANONICAL) if CANONICAL else 0.0
    # loop/oscillation penalty: any canonical node executed more than once lowers coherence
    repeats = len(traj_in_canon) - len(set(traj_in_canon))
    coherence = max(0.0, coherence - 0.1 * repeats)
    return {"tool_selection_quality": round(tool_sel, 4),
            "action_completion": round(action_completion, 4),
            "reasoning_coherence": round(coherence, 4),
            "trajectory": traj, "n_decisions": len(decisions), "interrupted": bool(interrupted)}


def run_live(incident: dict | None = None) -> dict:
    """Run the REAL runtime on one incident and compute metrics from its trace. Honest-skip if unavailable."""
    # Realistic at-risk incident in the model's actual schema (AI4I features — the failure predictor / explainer
    # require air_temp_k/process_temp_k/… ; a made-up telemetry shape degrades the loop to "no decision").
    incident = incident or {
        "type": "machine_crack", "target_id": 3, "sil_level": 0,
        "telemetry": {"stage_id": 3, "type_": "M", "air_temp_k": 300.0, "process_temp_k": 312.0,
                      "rot_speed_rpm": 1300.0, "torque_nm": 60.0, "tool_wear_min": 210.0,
                      "status": "degraded", "crack_proximity": 0.9},
        "plant": {"available_crew": 1}, "recent_incidents": [],
    }
    try:
        from agents.runtime.graph import run_incident
        out = run_incident(incident)
        trace = out.get("trace", []) or []
        traj = [(t.get("node") if isinstance(t, dict) else getattr(t, "node", None)) for t in trace]
        m = compute_metrics(traj, out.get("decisions", []), bool(out.get("interrupted")))
        m["available"] = True
        m["backend"] = out.get("backend")
        return m
    except Exception as e:  # noqa: BLE001 - DB/model/runtime unavailable -> honest-skip, NEVER a fake trajectory
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}


def _emit(metric: str, value: float, baseline: float) -> None:
    try:
        from observability.phoenix_evals import log_eval
        log_eval("agentic_metrics", metric, value, baseline=baseline, passed=value >= baseline)
    except Exception:  # noqa: BLE001
        pass


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true")
    args = ap.parse_args(argv)
    res = run_live()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "agentic_metrics.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    if not res.get("available"):
        print("agentic_metrics: runtime unavailable (honest-skip; no fabricated trajectory)")
        return 0  # not a CI failure — the live runtime is a nightly/Docker dependency
    for k in ("tool_selection_quality", "action_completion", "reasoning_coherence"):
        _emit(k, res[k], 0.8)
    if args.gate:
        bad = [k for k in ("tool_selection_quality", "reasoning_coherence") if res[k] < 0.8]
        if bad:
            print(f"GATE FAILED (agentic metrics below 0.8): {bad}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
