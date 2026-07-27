"""Stage 26 — supply-chain disruption monitoring (research §37.4).

Watches the OBSERVED signals for four disruption classes and reacts honestly:
  D1 supplier failure-rate spike   -> quarantine the supplier (CNP stops awarding to it) + incident
  D2 delivery-latency spike        -> incident (robust-Z on observed lead times vs their own history)
  D3 stage-buffer starvation       -> incident (persistent queue_depth == 0 -> stockout)
  D4 demand spike                  -> incident (robust-Z on the observed throughput series)

Incidents are raised into the SELF-HEALING RUNTIME through the Stage-25 exactly-once router
(`run_incident_guarded`) so a disruption gets the full predict→diagnose→verify→log treatment and a signed
audit trail; the orchestrator additionally triggers a CNP replan. Detection thresholds are the same sourced
robust-Z (|z|>=3.5, Iglewicz–Hoaglin) used by the Art-72 sweep — no invented magic numbers. Below MIN_OBS
observations no detector fires (honest-unknown, never a guess).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from agents.supply_chain.signals import SignalObserver, _median

ROBUST_Z = 3.5          # Iglewicz–Hoaglin cutoff (research §36.2 / §37.4)
MIN_OBS = 6             # below this, detectors abstain
MIN_LEAD_OBS = 12       # minimum lead observations before any latency verdict (small samples are unsound)
LEAD_RECENT_K = 5       # shift test: median of the last K leads (a 5-median is immune to isolated tail draws)
LEAD_BASELINE_OBS = 12  # ...vs the median of the B leads before them (the frozen local baseline)
LEAD_SHIFT_FACTOR = 2.0 # structural shift = recent median >= 2x baseline median (P[5-median >=2x | lognormal
                        # sigma_log~0.4] requires >=3 of 5 independent >=2x draws ~ 1e-4 — sound at our scale)
OVERDUE_MIN_COUNT = 3   # overdue detector: >=3 SIMULTANEOUSLY overdue orders (independent lognormal draws make 3
                        # concurrent 3.5-sigma-age pendings vanishingly rare; a frozen supplier accumulates them
                        # immediately — the operational expediting rule)
FAILURE_RATE_LIMIT = 0.5   # observed failure rate that quarantines a supplier (>= half of observed orders failed)
STARVATION_TICKS = 3    # consecutive zero-buffer observations that constitute a stockout
EPISODE_QUIET_CHECKS = 12  # G-083: an episode closes after this many consecutive quiet checks (~1h at
                           # 300s ticks) — the (kind,subject) channel can then raise a NEW incident


def _robust_z(history: list[float], last: float) -> Optional[float]:
    if len(history) < MIN_OBS:
        return None
    med = _median(history)
    mad = _median([abs(x - med) for x in history])
    if mad == 0.0:
        return None if last == med else float("inf")
    return 0.6745 * (last - med) / mad


def _lead_outlier_threshold(history: list[float]) -> Optional[float]:
    """Log-space 3.5-sigma outlier threshold for LEAD TIMES: median * exp(ROBUST_Z * sigma_log_hat).

    Lead times are lognormal-like; a FIXED multiple of the median (the first implementation used 2x) fires on
    natural tail draws (independent review, 2026-07-03: with sigma_log 0.4, P(lead >= 2x median) ~ 4% per order —
    a no-injection control reproduced the 'detection'). Scaling the threshold to the OBSERVED log-space spread
    (sigma_log_hat = 1.4826 * MAD(ln lead)) puts the false-fire rate at the same 3.5-sigma standard as every other
    detector (~0.02%/order) while a structural 6x-median delay (ln6/0.4 ~ 4.5 sigma) still fires."""
    import math
    xs = [math.log(x) for x in history if x > 0]
    if len(xs) < MIN_LEAD_OBS:
        return None
    med_log = _median(xs)
    mad_log = _median([abs(x - med_log) for x in xs])
    sigma_log = 1.4826 * mad_log
    if sigma_log == 0.0:
        return math.exp(med_log) * 2.0  # flat history: any 2x jump is structural
    return math.exp(med_log + ROBUST_Z * sigma_log)


@dataclass
class Disruption:
    kind: str            # "supplier_failure" | "latency_spike" | "stockout" | "demand_spike"
    subject: str         # "supplier:2" | "stage:3" | "plant"
    detail: dict[str, Any]


class DisruptionMonitor:
    """Stateful detector over a SignalObserver; `check()` once per tick returns new disruptions."""

    def __init__(self, observer: SignalObserver,
                 raise_incident: Optional[Callable[[dict], Any]] = None):
        self.observer = observer
        self.quarantined: set[int] = set()
        self._starvation_run: dict[int, int] = {}
        # Episode registry (G-083 fix): a (kind,subject) episode CLOSES after EPISODE_QUIET_CHECKS consecutive
        # checks in which that channel stayed silent — the channel can then re-raise for a genuinely new episode.
        # (The Stage-26 review found `_raised` never reset: one incident per channel per monitor LIFETIME, so the
        # first episode permanently deafened the channel.) Value = consecutive quiet checks since last seen.
        self._raised: dict[tuple[str, str], int] = {}
        self._lead_seen: dict[int, int] = {}         # supplier -> count of lead observations already checked
        # Default incident sink = the Stage-25 exactly-once router into the real runtime.
        self._raise = raise_incident if raise_incident is not None else self._default_raise

    @staticmethod
    def _default_raise(incident: dict) -> Any:
        from agents.runtime.shard_router import run_incident_guarded
        return run_incident_guarded(incident, sil_level=0)

    def check(self) -> list[Disruption]:
        found: list[Disruption] = []
        # D1 supplier failure-rate + D2 latency spike
        for sid, s in sorted(self.observer.suppliers.items()):
            if s.observations >= MIN_OBS and s.reliability is not None:
                fail_rate = 1.0 - s.reliability
                if fail_rate >= FAILURE_RATE_LIMIT and sid not in self.quarantined:
                    self.quarantined.add(sid)
                    found.append(Disruption("supplier_failure", f"supplier:{sid}",
                                            {"observed_failure_rate": round(fail_rate, 3),
                                             "observations": s.observations, "action": "quarantined"}))
            # D2 — TWO-WINDOW MEDIAN-SHIFT detector (3rd design; each predecessor refuted by a drill):
            #   v1 last-element robust-Z missed mid-batch spikes; v2 per-lead log-space outlier testing was refuted
            #   by the independent review's no-injection control (natural lognormal tails fire ~per-mille x hundreds
            #   of draws = multiple-testing false positives) AND by the ramp drill (the sim's decaying-extra delay
            #   arrives GRADUALLY, contaminating the history before any single point can outlie it).
            # The shift test is robust to both: median(last K) can't be moved by an isolated tail draw, and a ramp
            # or step RAISES it against the FROZEN prior baseline. Fires when recent >= LEAD_SHIFT_FACTOR x baseline.
            # D2a — OVERDUE-PENDING detector (4th design iteration; the operational one). The sim's freeze-type
            # delay (`delay_next_delivery`) releases ALL delayed fulfilments at the freeze end, so post-hoc lead
            # statistics only see the shift AFTER it is over (drill finding #3: the shift test was structurally
            # LATE). Real expediting watches the other side: orders PLACED but not arrived past a quantile age.
            # Threshold = observed median x exp(ROBUST_Z x sigma_log_hat) — same 3.5-sigma standard, log space.
            now = self.observer.last_time_s
            outstanding = self.observer.outstanding.get(sid, [])
            leads_hist = [l_ for l_ in s.lead_times_s]
            basis = "own_history"
            if len(leads_hist) < MIN_LEAD_OBS:
                # The freeze STARVES its own detector: a recently-promoted supplier has few observed leads and a
                # frozen supplier produces none (drill finding #5, seed 42 — 3 leads at detection time). Fall back
                # to the FLEET-pooled lead distribution (standard expediting practice for thin per-supplier
                # history), labelled as such in the detection detail.
                leads_hist = [l_ for st_ in self.observer.suppliers.values() for l_ in st_.lead_times_s]
                basis = "fleet_pooled"
            if len(leads_hist) >= MIN_LEAD_OBS and outstanding:
                import math
                logs = [math.log(x) for x in leads_hist if x > 0]
                med_log = _median(logs)
                sigma_log = 1.4826 * _median([abs(x - med_log) for x in logs])
                age_threshold = math.exp(med_log + ROBUST_Z * max(sigma_log, 0.1))
                overdue = [p_ for p_ in outstanding if (now - p_) > age_threshold]
                if len(overdue) >= OVERDUE_MIN_COUNT:
                    found.append(Disruption("latency_spike", f"supplier:{sid}",
                                            {"detector": "overdue_pending", "threshold_basis": basis,
                                             "overdue_count": len(overdue),
                                             "age_threshold_s": round(age_threshold, 1),
                                             "oldest_overdue_age_s": round(now - min(overdue), 1)}))
            # D2b — placement-windowed median-shift test (complementary: catches sustained lead degradation that
            # still fulfils; windowed by placement batch to kill the fulfilment-order ramp artifact).
            pairs = [(p_, l_) for p_, l_ in zip(s.lead_placed_at_s, s.lead_times_s) if p_ is not None]
            if len(pairs) >= LEAD_BASELINE_OBS + LEAD_RECENT_K:
                # Window by PLACEMENT time, not observation order: a same-placement batch fulfils
                # shortest-lead-first, so observation order fabricates an upward 'ramp' (drill finding).
                # Windows are drawn at BATCH (placement-time) boundaries — orders placed together stay together
                # (a K-pair cut can split a batch, and then no strictly-later split point exists).
                pairs.sort(key=lambda t: t[0])
                batches: dict[float, list[float]] = {}
                for p_, l_ in pairs:
                    batches.setdefault(p_, []).append(l_)
                times = sorted(batches)
                recent: list[float] = []
                split = len(times)
                while split > 0 and len(recent) < LEAD_RECENT_K:
                    split -= 1
                    recent = [l_ for t_ in times[split:] for l_ in batches[t_]]
                baseline = [l_ for t_ in times[:split] for l_ in batches[t_]]
                if len(recent) >= LEAD_RECENT_K and len(baseline) >= LEAD_BASELINE_OBS:
                    med_recent, med_base = _median(recent), _median(baseline[-LEAD_BASELINE_OBS * 3:])
                    if med_base > 0 and med_recent >= LEAD_SHIFT_FACTOR * med_base:
                        found.append(Disruption("latency_spike", f"supplier:{sid}",
                                                {"median_recent_s": round(med_recent, 1),
                                                 "median_baseline_s": round(med_base, 1),
                                                 "shift": round(med_recent / med_base, 2)}))
            self._lead_seen[sid] = s.lead_total
        # D3 stage starvation
        for stage_id, hist in sorted(self.observer.queue_history.items()):
            run = self._starvation_run.get(stage_id, 0)
            run = run + 1 if (len(hist) and hist[-1] == 0) else 0
            self._starvation_run[stage_id] = run
            if run == STARVATION_TICKS:  # fire once when the threshold is first crossed
                found.append(Disruption("stockout", f"stage:{stage_id}",
                                        {"consecutive_zero_buffer_ticks": run}))
        # D4 demand spike
        th = list(self.observer.throughput_history)
        if len(th) > MIN_OBS:
            z = _robust_z(th[:-1], th[-1])
            if z is not None and z != float("inf") and abs(z) >= ROBUST_Z:
                found.append(Disruption("demand_spike", "plant",
                                        {"z": round(z, 2), "last_throughput": round(th[-1], 2)}))
        # Raise each NEW disruption episode into the runtime (exactly-once per OPEN episode; episodes expire
        # after EPISODE_QUIET_CHECKS consecutive quiet checks — G-083).
        active_keys = {(d.kind, d.subject) for d in found}
        for key in list(self._raised):
            if key in active_keys:
                self._raised[key] = 0                      # still active: reset its quiet counter
            else:
                self._raised[key] += 1
                if self._raised[key] >= EPISODE_QUIET_CHECKS:
                    del self._raised[key]                  # episode closed: channel may re-raise
        for d in found:
            key = (d.kind, d.subject)
            if key in self._raised:
                continue
            self._raised[key] = 0
            incident = {"id": f"supply-{d.kind}-{d.subject.replace(':', '-')}",
                        "type": f"supply_chain_{d.kind}", "target_id": d.subject,
                        "severity": "high" if d.kind in ("supplier_failure", "stockout") else "medium",
                        "description": f"supply-chain disruption {d.kind} at {d.subject}: {d.detail}",
                        "telemetry": {}, "detail": d.detail}
            try:
                self._raise(incident)
            except Exception:  # noqa: BLE001 — runtime unavailable: detection still returned; surfaced by caller
                pass
        return found


__all__ = ["DisruptionMonitor", "Disruption", "ROBUST_Z", "MIN_OBS", "FAILURE_RATE_LIMIT", "STARVATION_TICKS"]
