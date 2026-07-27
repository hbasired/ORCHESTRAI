"""Test-only ASGI app exposing ONLY the A2A router — used by the two-instance HTTP federation check (G-071).
Launched as two separate uvicorn processes with distinct KEY_STORE_DIRs so each gets its own ML-DSA-65 identity.
Not imported by the app; lives under tests/."""
from fastapi import FastAPI

from a2a.server import router

app = FastAPI(title="a2a-peer")
app.include_router(router)
