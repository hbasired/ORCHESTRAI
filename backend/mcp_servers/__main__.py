"""Stage 11.5 — MCP server supervisor (multiprocess + watchdog).

Runs the five MCP servers as long-lived **streamable-HTTP** services (one subprocess each, on its registry port)
and restarts any that die (watchdog). This is the production-style run; CI tests + the LangGraph mount use stdio
(the client spawns a server per session — see `backend/agents/runtime/mcp_mount.py`).

    python -m mcp_servers                 # supervise all five (HTTP on 9101-9105)
    python -m mcp_servers --only kpi_query_server,sim_world_server
    python -m mcp_servers --once          # start each once, report liveness, exit (CI smoke)

Honest: a subprocess that exits is reported + (unless --once) restarted with backoff; nothing is faked.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from typing import Optional

from mcp_servers import SERVER_REGISTRY


def _spawn(name: str, module: str, port: int) -> subprocess.Popen:
    env = dict(os.environ, MCP_TRANSPORT="http", MCP_PORT=str(port))
    # -m <module> from the backend dir; inherit stdio so logs surface.
    return subprocess.Popen([sys.executable, "-m", module], env=env)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="mcp_servers", description="MCP server supervisor")
    ap.add_argument("--only", help="comma-separated subset of server names")
    ap.add_argument("--once", action="store_true",
                    help="start each once, check liveness after a grace period, then exit (CI smoke)")
    ap.add_argument("--grace", type=float, default=3.0, help="liveness grace period for --once")
    ap.add_argument("--max-restarts", type=int, default=50, help="restart budget per server (watchdog)")
    args = ap.parse_args(argv)

    selected = list(SERVER_REGISTRY.items())
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        selected = [(n, v) for n, v in SERVER_REGISTRY.items() if n in wanted]
        if not selected:
            print(f"no servers matched --only {args.only!r}", file=sys.stderr)
            return 2

    procs: dict[str, subprocess.Popen] = {}
    restarts: dict[str, int] = {n: 0 for n, _ in selected}
    for name, (module, port) in selected:
        procs[name] = _spawn(name, module, port)
        print(f"[supervisor] started {name} (pid={procs[name].pid}) http://127.0.0.1:{port}/mcp", flush=True)

    if args.once:
        time.sleep(args.grace)
        alive = {n: (p.poll() is None) for n, p in procs.items()}
        for n, ok in alive.items():
            print(f"[supervisor] {n}: {'ALIVE' if ok else 'DEAD (exit %s)' % procs[n].returncode}", flush=True)
        for p in procs.values():
            if p.poll() is None:
                p.terminate()
        for p in procs.values():
            try:
                p.wait(timeout=5)
            except Exception:  # noqa: BLE001
                p.kill()
        return 0 if all(alive.values()) else 1

    stop = {"flag": False}

    def _handle(signum, _frame):
        stop["flag"] = True
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle)
        except Exception:  # noqa: BLE001 - not all platforms/threads allow this
            pass

    port_of = {n: v[1] for n, v in selected}
    mod_of = {n: v[0] for n, v in selected}
    try:
        while not stop["flag"]:
            for name, p in list(procs.items()):
                if p.poll() is not None:  # died
                    if restarts[name] >= args.max_restarts:
                        print(f"[supervisor] {name} exceeded restart budget; leaving down", flush=True)
                        continue
                    restarts[name] += 1
                    backoff = min(2.0 * restarts[name], 30.0)
                    print(f"[supervisor] {name} died (exit {p.returncode}); restart "
                          f"#{restarts[name]} in {backoff:.0f}s", flush=True)
                    time.sleep(backoff)
                    procs[name] = _spawn(name, mod_of[name], port_of[name])
            time.sleep(1.0)
    finally:
        print("[supervisor] shutting down children...", flush=True)
        for p in procs.values():
            if p.poll() is None:
                p.terminate()
        for p in procs.values():
            try:
                p.wait(timeout=5)
            except Exception:  # noqa: BLE001
                p.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
