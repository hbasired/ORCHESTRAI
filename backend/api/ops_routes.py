"""Stage 25 (G-021) — live ops: decision-cascade / latency view + post-market dashboard data.

Reads ONLY the real, signed `audit_chain` (never the legacy fabricated state path — G-082): the cascade view
reconstructs each incident's decision sequence from its audit rows (`decision.trace`, `rbac.check`, `mac.read`,
`safety.*`, `a2a.rpc.*`, `key_rotation`, `post_market.sweep`) with real inter-row latencies. Honest-unavailable:
with no DB the endpoints return 503, never a fabricated cascade. The HTML page is a thin self-contained render of
these endpoints (no external assets).

Endpoints:
  GET /ops/cascade?limit=200      recent audit rows grouped by incident, with per-step latency deltas
  GET /ops/post-market            latest Art-72 sweep verdicts + chain/rotation posture
  GET /ops/                       self-contained HTML view of both
"""
from __future__ import annotations

import datetime as dt
import json
import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/ops", tags=["Live Ops (Art-72 / G-021)"])


def _dsn() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


def _connect():
    dsn = _dsn()
    if not dsn:
        raise HTTPException(status_code=503, detail="ops view unavailable: no DATABASE_URL configured (honest-unavailable)")
    try:
        import psycopg
        return psycopg.connect(dsn, connect_timeout=5)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"ops view unavailable: Postgres unreachable ({e})")


@router.get("/cascade")
def cascade(limit: int = Query(default=200, le=1000)) -> dict[str, Any]:
    """Recent audit rows grouped into per-incident cascades with real latency deltas (ms) between steps."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT seq, ts, actor, action,
                   COALESCE(payload->>'incident_id', payload->'payload'->>'incident_id') AS incident_id
            FROM audit_chain ORDER BY seq DESC LIMIT %s
            """,
            (limit,),
        )
        rows = list(reversed(cur.fetchall()))
    cascades: dict[str, list[dict[str, Any]]] = {}
    system_rows: list[dict[str, Any]] = []
    for seq, ts, actor, action, incident_id in rows:
        entry = {"seq": seq, "ts": ts.isoformat(), "actor": actor, "action": action}
        if incident_id:
            cascades.setdefault(incident_id, []).append(entry)
        else:
            system_rows.append(entry)
    # Real per-step latency inside each incident cascade.
    for steps in cascades.values():
        prev = None
        for step in steps:
            t = dt.datetime.fromisoformat(step["ts"])
            step["delta_ms"] = round((t - prev).total_seconds() * 1000, 1) if prev else 0.0
            prev = t
    return {"incidents": cascades, "system": system_rows[-50:], "rows_scanned": len(rows)}


@router.get("/post-market")
def post_market() -> dict[str, Any]:
    """Art-72 posture: latest sweep verdicts, chain head, rotation cadence — all from the live chain."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT max(seq), count(*) FROM audit_chain")
        head, total = cur.fetchone()
        cur.execute(
            """
            SELECT ts, payload FROM audit_chain WHERE action = 'post_market.sweep'
            ORDER BY seq DESC LIMIT 10
            """
        )
        sweeps = [{"ts": ts.isoformat(), **(p if isinstance(p, dict) else json.loads(p))} for ts, p in cur.fetchall()]
        cur.execute(
            """
            SELECT ts, payload->>'key_type' FROM audit_chain WHERE action = 'key_rotation'
            ORDER BY seq DESC LIMIT 5
            """
        )
        rotations = [{"ts": ts.isoformat(), "key_type": kt} for ts, kt in cur.fetchall()]
    return {"chain_head_seq": head, "chain_rows": total, "recent_sweeps": sweeps, "recent_rotations": rotations}


_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Live Ops — Cascade &amp; Art-72</title>
<style>body{font-family:system-ui;background:#0d1117;color:#e6edf3;margin:0;padding:24px}
h1{font-size:1.2rem}h2{font-size:1rem;color:#58a6ff;margin-top:24px}
table{border-collapse:collapse;width:100%;font-size:.8rem}td,th{border:1px solid #30363d;padding:4px 8px;text-align:left}
th{background:#1c2330;color:#58a6ff}.muted{color:#9da7b3}.err{color:#f85149}</style></head><body>
<h1>Live Ops — decision cascade &amp; Art-72 posture (real audit_chain; honest-503 when DB down)</h1>
<div id="pm" class="muted">loading…</div><h2>Incident cascades (latency = real inter-row ms)</h2>
<div id="cascade" class="muted">loading…</div>
<script>
async function load(){
 try{
  const pm=await (await fetch('/ops/post-market')).json();
  document.getElementById('pm').innerHTML='<b>chain head</b> seq '+pm.chain_head_seq+' ('+pm.chain_rows+' rows) · '+
   '<b>sweeps</b> '+pm.recent_sweeps.map(s=>s.ts.slice(0,10)+':'+s.status).join(' · ')+
   ' · <b>rotations</b> '+pm.recent_rotations.map(r=>r.key_type+'@'+r.ts.slice(0,10)).join(', ');
  const c=await (await fetch('/ops/cascade')).json();
  let html='';
  for(const [inc,steps] of Object.entries(c.incidents)){
   html+='<h3>'+inc+'</h3><table><tr><th>seq</th><th>action</th><th>actor</th><th>Δms</th></tr>'+
    steps.map(s=>'<tr><td>'+s.seq+'</td><td>'+s.action+'</td><td>'+s.actor+'</td><td>'+s.delta_ms+'</td></tr>').join('')+'</table>';
  }
  document.getElementById('cascade').innerHTML=html||'<i>no incident-tagged rows in window</i>';
 }catch(e){document.getElementById('pm').innerHTML='<span class="err">unavailable: '+e+'</span>';}
}
load();setInterval(load,10000);
</script></body></html>"""


@router.get("/", response_class=HTMLResponse)
def ops_page() -> str:
    return _PAGE
