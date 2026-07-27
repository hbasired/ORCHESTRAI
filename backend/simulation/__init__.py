"""Simulation module for the manufacturing ecosystem.

The canonical simulator is `SimWorld` (a SimPy discrete-event twin — see `simulation/sim_world.py`), exposed to the
API via `backend/api/simulation_routes.py`. The old `SimulationEngine` (and its `_generate_mock_state` fabrication) was
DELETED in 2026-07 once every frontend surface was wired to the real SimWorld; nothing imports it anymore.
"""
