---
status: done
stage: 05
slug: demand_forecasting
created: 2026-06-01
---

# Stage 05 — Demand Forecasting (supply-chain head predictor; LSTM)

> The supply-chain head agent needs to forecast near-term demand so the coordinator can pre-position inventory
> and absorb spikes without interruption (feeds the self-healing loop's intervene step). This stage ships a real
> **LSTM** time-series forecaster (the algorithm asked about), trained free-cost on Colab, replacing the
> `random.*` demand stub in `backend/ml/neural_networks.py`. First-cut on a reliable open proxy dataset; re-fit
> on real order data before pilot.

## Cross-cutting requirements (MANDATORY — CLAUDE.md §4 rules 9–10)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` + `KB_25_Causal_SelfHealing_Engine.md` (demand feeds intervene/optimization).
- [ ] Pull in `audits/OPEN_GAPS_LEDGER.md` rows ≤ Stage 5 — none new-blocking; note G-006 (PdM dashboard can show demand too).
- [ ] **Free-cost only:** Colab-free / local; reliable license-clean dataset; Groq/Ollama for any LLM. No paid SaaS, no committed keys.

## Pre-requisites

- Stage(s) closed: Stage 4 (predictive maintenance; baseline 404). Stage 2 (SimPy world).
- Decision logs honoured: `2026-05-31_causal_self_healing_engine.md`.
- KB at min version: KB_02 (model inventory), KB_03 (datasets), KB_23 (evals), KB_25.
- Gaps ledger rows pulled in: (none blocking).

## Acceptance criteria

- [ ] `backend/ml/demand_forecaster.py` exists — an **LSTM** that, given a window of recent demand + covariates,
      forecasts demand for the next H steps. Honest: raises `ModelUnavailableError` if torch/brain absent — no fabrication.
- [ ] Trained on a **reliable, license-clean** open dataset (default: **UCI Bike Sharing #275** — hourly demand
      + weather/time covariates; same UCI direct-download proven in Stage 4). License recorded in KB_03.
- [ ] `models/demand_forecaster.*` ships with `models/demand_forecaster.metrics.json` +
      `compliance/model-cards/demand_forecaster.md` (CI gate).
- [ ] Eval vs stated baselines (naive "tomorrow=today" persistence + seasonal-naive). Report **MAE / RMSE / MAPE**
      and the % improvement over persistence in `results.json` (KB_23). No metric without a baseline.
- [ ] `forecast(window) -> {horizon, point, lower, upper}` inference seam (sync, CPU, < 50 ms).
- [ ] **Audit count strictly decreases (< 404)** by replacing the `random.*` demand stub in `backend/ml/neural_networks.py` with the real forecaster (or an honest model-unavailable path).

## Files to CREATE / MODIFY

| Path | Purpose |
|---|---|
| `notebooks/stage05_demand_forecasting_colab.ipynb` | training (I generate it; you run on Colab → `demand_brain.zip`) |
| `backend/ml/demand_forecaster.py` | inference: `forecast(window)` |
| `models/demand_forecaster.*` + `.metrics.json` | weights + metrics |
| `compliance/model-cards/demand_forecaster.md` | model card |
| `backend/ml/neural_networks.py` (MODIFY) | remove the `random.*` demand stub → real model / honest fallback (drops audit) |

## KB files this stage updates (ALL must be touched before close — the Stage-4 lesson)

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_02_Models_Inventory.md` (demand_forecaster row)
- `knowledge-base/KB_03_Datasets_Catalog.md` (Bike Sharing dataset + license)
- `knowledge-base/KB_23_Evals_and_Benchmarks.md` (demand eval + baselines)
- `knowledge-base/KB_25_Causal_SelfHealing_Engine.md` (demand feeds intervene/optimization)

## Verification commands

```bash
bash scripts/audit.sh                       # TOTAL must be < 404
cd backend && venv/Scripts/python -m pytest tests/test_demand_forecaster.py -q
# train (free, Colab): notebooks/stage05_demand_forecasting_colab.ipynb -> demand_brain.zip
```

## Audit target

- Pre-stage baseline: **404**. Target: **< 404** — replace the demand `random.*` stub in `backend/ml/neural_networks.py`.

## Role

- Primary: `ml-engineer`. Secondary: `backend-engineer` (inference wiring), `system-designer` (the demand→optimization seam).

## Risks / unknowns

- Proxy dataset (Bike Sharing) ≠ real warehouse orders → re-fit on real demand before pilot (ledger at close).
- Forecast uncertainty: ship a simple interval (e.g., residual quantiles), not a fake confidence.
- Free compute: small LSTM, fits Colab-free.

## Hand-off (read by scripts/seed-next-task.sh / next-task.sh)

- What is now true: a real LSTM demand forecaster with `forecast(...)`; baseline < 404.
- What the next stage starts with: predict (Stage 4) + demand (Stage 5) feeding the world/optimization → toward diagnose (Stage 8/11).
- Open items deferred: re-fit on real order data; probabilistic forecasting; energy forecaster (Stage 6.5).

---

*Authored 2026-06-01 (agentic-governance-engineer, for ml-engineer). Replaces the start-task.sh TBD seed.*
