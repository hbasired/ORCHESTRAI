"""Stage 8 — Learned world model (time-to-failure forecasting) training package.

Contents:
- rollouts.py : generate (telemetry-window -> true TTF) data from seeded SimWorld crack rollouts.
- train.py    : train an LSTM TTF forecaster -> models/world_model_ttf.{pt,metrics.json}.
- eval.py     : TTF MAE on held-out seeds vs a naive mean-TTF baseline.

Free-cost: torch CPU + numpy + the simulator. No external dataset, no paid services.
The TTF signal is the timing information Stage 7's RL intervention lacked (KB_25 step 1).
"""
