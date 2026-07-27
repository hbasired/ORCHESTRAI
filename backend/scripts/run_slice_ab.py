"""Stage 6 — seeded A/B experiment: slice loop ON vs OFF (AC4).

Runs the SimPy world twice per seed — identical seeds, identical crack
campaign — with the predict→diagnose→intervene loop enabled (ON) and disabled
(OFF), and reports MEASURED downtime/throughput for both arms. The delta is
whatever the simulation produces; this harness never asserts or massages the
direction of the result (honesty rule: the number is the artifact).

Usage (from backend/):
    python scripts/run_slice_ab.py --seed 42 --sim-hours 8 --scenario machine_crack
    python scripts/run_slice_ab.py --seeds 42,43,44 --sim-hours 8

Accounting notes (documented, not hidden):
- Broken time counts completed repairs PLUS any in-progress breakdown at the
  end of the window (env.now − failure start). Planned-maintenance time counts
  completed windows only; end-of-window truncation is ≤ one maintenance
  duration and applies to the ON arm (against us — the honest direction).
- Both arms run the same SimWorld code; the ON arm differs ONLY by the
  SliceLoop process being attached.

Output: JSON + markdown report under backend/training/evals/stage06/.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow `python scripts/run_slice_ab.py` from backend/ (mirrors pytest's rootdir).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.failure_predictor import ModelUnavailableError, get_failure_predictor  # noqa: E402
from services.slice_runner import SliceLoop  # noqa: E402
from simulation.entities import Incident, InjectRequest  # noqa: E402
from simulation.sim_world import SimWorld  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parents[1] / "training" / "evals" / "stage06"

# The crack campaign: (inject_at_minutes, stage_id). Rotating targets so the
# result is not one machine's idiosyncrasy. eta uses the calibrated default
# (12 min). Spacing > repair + cooldown so episodes don't overlap on a stage.
DEFAULT_CAMPAIGN: tuple[tuple[float, int], ...] = (
    (15.0, 3),
    (105.0, 5),
    (195.0, 2),
    (285.0, 7),
    (375.0, 1),
)


def _inject_process(world: SimWorld, at_seconds: float, req: InjectRequest):
    yield world.env.timeout(at_seconds)
    world._apply_incident(Incident.from_request(req))


def run_arm(*, seed: int, sim_hours: float, loop_on: bool,
            campaign: tuple[tuple[float, int], ...] = DEFAULT_CAMPAIGN) -> dict:
    """Run one arm (in-environment, no worker thread) and return measured metrics."""
    world = SimWorld(seed=seed)
    horizon_s = sim_hours * 3600.0
    for at_min, stage_id in campaign:
        if at_min * 60.0 >= horizon_s:
            continue
        req = InjectRequest(type="machine_crack", target_id=stage_id, details={}, severity="warning")
        world.env.process(_inject_process(world, at_min * 60.0, req))

    slice_loop = None
    if loop_on:
        slice_loop = SliceLoop(world)
        slice_loop.start()

    world.env.run(until=horizon_s)

    broken_s = 0.0
    maintenance_s = 0.0
    breakdowns = 0
    crack_breakdowns = 0
    maintenances = 0
    for stage in world.stages.values():
        broken_s += stage.time_broken_seconds
        maintenance_s += stage.time_maintenance_seconds
        breakdowns += stage.breakdown_count
        crack_breakdowns += stage.crack_breakdown_count
        maintenances += stage.maintenance_count
        # In-progress breakdown at window end: count elapsed time honestly.
        if stage.status == "broken" and stage.last_mtbf_failure_at is not None:
            broken_s += world.env.now - stage.last_mtbf_failure_at

    metrics = {
        "seed": seed,
        "arm": "on" if loop_on else "off",
        "sim_hours": sim_hours,
        "orders_complete": world.total_orders_complete,
        "throughput_units_per_hour": round(world.total_orders_complete / sim_hours, 2),
        "unplanned_downtime_min": round(broken_s / 60.0, 2),
        "planned_maintenance_min": round(maintenance_s / 60.0, 2),
        "total_downtime_min": round((broken_s + maintenance_s) / 60.0, 2),
        "breakdowns": breakdowns,
        "crack_breakdowns": crack_breakdowns,
        "planned_maintenances": maintenances,
        "cracks_injected": sum(1 for at_min, _ in campaign if at_min * 60.0 < horizon_s),
    }
    if slice_loop is not None:
        metrics["slice_trail"] = slice_loop.trail.counts()
    return metrics


def _paired_bootstrap_ci(diffs: list[float], n_boot: int = 5000, seed: int = 6) -> dict:
    """Paired bootstrap 95% CI on the mean of per-seed (CRN-paired) differences. Honest for small n: the CI
    reflects sampling uncertainty across seeds; with few seeds it is WIDE (and that is the truth)."""
    import random
    n = len(diffs)
    mean = statistics.mean(diffs) if n else 0.0
    if n < 2:
        return {"mean": round(mean, 2), "ci95": [None, None], "n": n,
                "note": "n<2 — no interval (run more seeds for a CI)"}
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        boots.append(statistics.mean(sample))
    boots.sort()
    lo = boots[int(0.025 * n_boot)]
    hi = boots[int(0.975 * n_boot)]
    return {"mean": round(mean, 2), "ci95": [round(lo, 2), round(hi, 2)], "n": n,
            "significant": bool(lo > 0 or hi < 0)}


def run_experiment(seeds: list[int], sim_hours: float) -> dict:
    pairs = []
    for seed in seeds:
        off = run_arm(seed=seed, sim_hours=sim_hours, loop_on=False)
        on = run_arm(seed=seed, sim_hours=sim_hours, loop_on=True)
        pairs.append({"seed": seed, "off": off, "on": on})

    def _mean(arm: str, key: str) -> float:
        return round(statistics.mean(p[arm][key] for p in pairs), 2)

    # Per-seed (CRN-paired) differences for the richer A/B with bootstrap 95% CIs.
    diff_unplanned = [p["off"]["unplanned_downtime_min"] - p["on"]["unplanned_downtime_min"] for p in pairs]
    diff_total = [p["off"]["total_downtime_min"] - p["on"]["total_downtime_min"] for p in pairs]
    diff_cracks = [p["off"]["crack_breakdowns"] - p["on"]["crack_breakdowns"] for p in pairs]
    diff_thr = [p["on"]["throughput_units_per_hour"] - p["off"]["throughput_units_per_hour"] for p in pairs]

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario": "machine_crack campaign (rotating stages, calibrated defaults)",
        "seeds": seeds,
        "sim_hours": sim_hours,
        "off": {
            "unplanned_downtime_min_mean": _mean("off", "unplanned_downtime_min"),
            "total_downtime_min_mean": _mean("off", "total_downtime_min"),
            "crack_breakdowns_mean": _mean("off", "crack_breakdowns"),
            "throughput_mean": _mean("off", "throughput_units_per_hour"),
        },
        "on": {
            "unplanned_downtime_min_mean": _mean("on", "unplanned_downtime_min"),
            "total_downtime_min_mean": _mean("on", "total_downtime_min"),
            "crack_breakdowns_mean": _mean("on", "crack_breakdowns"),
            "planned_maintenances_mean": _mean("on", "planned_maintenances"),
            "throughput_mean": _mean("on", "throughput_units_per_hour"),
        },
        "pairs": pairs,
    }
    summary["measured_delta"] = {
        "unplanned_downtime_min": round(
            summary["off"]["unplanned_downtime_min_mean"] - summary["on"]["unplanned_downtime_min_mean"], 2
        ),
        "total_downtime_min": round(
            summary["off"]["total_downtime_min_mean"] - summary["on"]["total_downtime_min_mean"], 2
        ),
        "throughput_units_per_hour": round(
            summary["on"]["throughput_mean"] - summary["off"]["throughput_mean"], 2
        ),
        "note": "positive = slice loop helped; reported as measured, not asserted",
    }
    # Richer A/B: paired bootstrap 95% CIs over per-seed differences (CRN-paired).
    summary["measured_delta_ci95"] = {
        "unplanned_downtime_min": _paired_bootstrap_ci(diff_unplanned),
        "total_downtime_min": _paired_bootstrap_ci(diff_total),
        "crack_breakdowns": _paired_bootstrap_ci(diff_cracks),
        "throughput_units_per_hour": _paired_bootstrap_ci(diff_thr),
        "note": ("paired bootstrap (5000 resamples) over per-seed OFF−ON differences (throughput ON−OFF). "
                 "'significant'=True iff the 95% CI excludes 0. With few seeds the CI is wide — that is honest."),
    }
    # The ON arm now runs the Stage-6 depth-hardened loop: predict → TTF forecast (Stage 8) → causal diagnose
    # (Stage 8B) → SHAP explain (Stage 10) → neuro-symbolic verify (Stage 8C) → intervene. The verifier approves
    # the single-machine maintenance, so execution (and these measured numbers) are preserved; the deepened pieces
    # add the forecast/explanation/verification provenance to each event.
    summary["loop_pipeline"] = "predict→forecast_ttf→causal_diagnose→shap_explain→neuro_symbolic_verify→intervene"
    return summary


def write_reports(summary: dict) -> tuple[Path, Path]:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    json_path = EVAL_DIR / "results.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md_path = EVAL_DIR / "results.md"
    d = summary["measured_delta"]
    md = [
        "# Stage 6 — Vertical Slice v0 A/B (measured)",
        "",
        f"Generated: {summary['generated_at']} · seeds {summary['seeds']} · {summary['sim_hours']} sim-hours/arm",
        f"Scenario: {summary['scenario']}",
        "",
        "| metric | loop OFF | loop ON | delta (OFF−ON) |",
        "|---|---|---|---|",
        f"| unplanned downtime (min, mean) | {summary['off']['unplanned_downtime_min_mean']} | {summary['on']['unplanned_downtime_min_mean']} | {d['unplanned_downtime_min']} |",
        f"| total downtime incl. planned (min, mean) | {summary['off']['total_downtime_min_mean']} | {summary['on']['total_downtime_min_mean']} | {d['total_downtime_min']} |",
        f"| crack-induced breakdowns (mean) | {summary['off']['crack_breakdowns_mean']} | {summary['on']['crack_breakdowns_mean']} | — |",
        f"| throughput (units/hr, mean) | {summary['off']['throughput_mean']} | {summary['on']['throughput_mean']} | {d['throughput_units_per_hour']} (ON−OFF) |",
        "",
        "## Paired bootstrap 95% CIs (richer A/B — CRN-paired over seeds)",
        "",
        "| metric (OFF−ON, throughput ON−OFF) | mean | 95% CI | significant? |",
        "|---|---|---|---|",
        *[f"| {k} | {v['mean']} | {v['ci95']} | {v.get('significant', '—')} |"
          for k, v in summary["measured_delta_ci95"].items() if k != "note"],
        "",
        f"Loop pipeline (ON arm): `{summary['loop_pipeline']}` — the Stage-6 depth-hardened loop wires the Stage-8 "
        "TTF forecast + learned-causal diagnosis + Stage-10 SHAP explanation + the neuro-symbolic plan verifier "
        "(which approves the single-machine maintenance, so the measured numbers are preserved).",
        "",
        "Honesty: measured output of seeded simulation runs; both arms share seeds and code, "
        "differing only by the SliceLoop process. With few seeds the CIs are wide (truthfully). "
        "Accounting caveats in the script docstring.",
    ]
    md_path.write_text("\n".join(md), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 6 slice A/B experiment")
    parser.add_argument("--seed", type=int, default=None, help="single seed")
    parser.add_argument("--seeds", type=str, default=None, help="comma-separated seeds")
    parser.add_argument("--sim-hours", type=float, default=8.0)
    parser.add_argument("--scenario", type=str, default="machine_crack",
                        choices=["machine_crack"], help="v0 supports the machine-failure scenario")
    args = parser.parse_args()

    if not get_failure_predictor().is_available():
        print("REFUSE: trained Stage-4 brain unavailable (xgboost + models/pdm_failure_predictor.*).")
        print("The A/B runs the REAL model or not at all — no fabricated arm.")
        return 2

    seeds = [args.seed] if args.seed is not None else None
    if args.seeds:
        seeds = [int(s) for s in args.seeds.split(",")]
    if not seeds:
        seeds = [42, 43, 44]

    try:
        summary = run_experiment(seeds, args.sim_hours)
    except ModelUnavailableError as e:
        print(f"REFUSE: {e}")
        return 2

    json_path, md_path = write_reports(summary)
    d = summary["measured_delta"]
    print(f"seeds={seeds} sim_hours={args.sim_hours}")
    print(f"OFF: unplanned={summary['off']['unplanned_downtime_min_mean']} min, "
          f"crack_breakdowns={summary['off']['crack_breakdowns_mean']}, thr={summary['off']['throughput_mean']} u/h")
    print(f"ON : unplanned={summary['on']['unplanned_downtime_min_mean']} min, "
          f"crack_breakdowns={summary['on']['crack_breakdowns_mean']}, "
          f"planned_maint={summary['on']['planned_maintenances_mean']}, thr={summary['on']['throughput_mean']} u/h")
    # ASCII-only console output (Windows cp1252 consoles choke on U+2212).
    print(f"MEASURED delta (OFF-ON): unplanned_downtime {d['unplanned_downtime_min']} min, "
          f"total_downtime {d['total_downtime_min']} min, throughput {d['throughput_units_per_hour']} u/h (ON-OFF)")
    print(f"reports: {json_path} · {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
