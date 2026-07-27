"use client";

// =============================================================================
// Embodied AI — LIVE, 100% backend-driven. No mock data.
//   • plant state    -> GET  /api/simulation/snapshot
//   • agent activity -> GET  /ops/cascade            (real signed audit rows = which agent did what)
//   • act            -> POST /factory/inject (run_loop) · POST /factory/diagnose · POST /facilities/optimize-energy
// Shows the head-agents, their real roles, whether each is currently active, and its last real action.
// =============================================================================

import { useCallback, useEffect, useRef, useState } from "react";
import Navigation from "@/components/Navigation";
import { Brain, AlertTriangle, Zap, Search } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ACTIVE_MS = 8000;

interface Stage { stage_id: number; name: string; status: string; }
interface Snapshot { stages: Stage[]; throughput_units_per_hour?: number; incidents_fired_count?: number; }
interface CascadeRow { seq: number; ts: string; actor: string; action: string; }

const AGENTS: { id: string; label: string; role: string; match: (a: string) => boolean }[] = [
    { id: "diagnosis",     label: "Diagnosis / Causal Agent", role: "Predicts failures (RUL/TTF) and reasons about the root cause (learned causal discovery).", match: (a) => a.includes("cdc") || a.includes("reason") || a.includes("diagnos") },
    { id: "manufacturing", label: "Manufacturing Agent",      role: "Runs the production line self-healing loop: predict → verify → intervene on stages.",         match: (a) => a.includes("slice") || a.includes("manufact") || a.includes("pdm") },
    { id: "repair",        label: "Repair / Safety Executor", role: "The SIL-gated executor — the ONLY path to an actuator; dispatches repair, enforces contracts.", match: (a) => a.includes("repair") || a.includes("dispatch") || a.includes("master") || a.includes("sil") },
    { id: "supply",        label: "Supply-Chain Agent",       role: "Multi-agent replenishment (Contract-Net) + disruption monitoring to prevent stockouts.",       match: (a) => a.includes("supply") || a.includes("inventory") || a.includes("jit") },
    { id: "facilities",    label: "Facilities / Energy Agent",role: "Peak-shaving / load-shifting via a real MILP against a time-of-use + demand-charge tariff.",     match: (a) => a.includes("facilit") || a.includes("energy") },
];

export default function EmbodiedAgentPage() {
    const [snap, setSnap] = useState<Snapshot | null>(null);
    const [online, setOnline] = useState<boolean | null>(null);
    const [rows, setRows] = useState<CascadeRow[]>([]);
    const [busy, setBusy] = useState<string | null>(null);
    const [activeAt, setActiveAt] = useState<Record<string, number>>({});
    const [lastAction, setLastAction] = useState<Record<string, string>>({});
    const [, force] = useState(0);
    const timer = useRef<ReturnType<typeof setInterval> | null>(null);
    const seenSeq = useRef(0);

    const poll = useCallback(async () => {
        try { const s = await fetch(`${API_BASE}/api/simulation/snapshot`, { cache: "no-store" }); if (s.ok) { setSnap(await s.json()); setOnline(true); } else throw new Error(); } catch { setOnline(false); }
        try {
            const c = await fetch(`${API_BASE}/ops/cascade`, { cache: "no-store" });
            if (c.ok) {
                const sys: CascadeRow[] = (await c.json()).system ?? [];
                setRows(sys.slice(-12).reverse());
                const now = Date.now(); const upd: Record<string, number> = {}; const la: Record<string, string> = {};
                for (const r of sys) {
                    const ag = AGENTS.find((x) => x.match(r.actor.toLowerCase()));
                    if (ag) { la[ag.id] = r.action; if (r.seq > seenSeq.current) upd[ag.id] = now; }
                }
                if (sys.length) seenSeq.current = Math.max(seenSeq.current, ...sys.map((r) => r.seq));
                if (Object.keys(la).length) setLastAction((p) => ({ ...p, ...la }));
                if (Object.keys(upd).length) setActiveAt((p) => ({ ...p, ...upd }));
            }
        } catch { /* best-effort */ }
    }, []);

    useEffect(() => { poll(); timer.current = setInterval(() => { poll(); force((n) => n + 1); }, 1500); return () => { if (timer.current) clearInterval(timer.current); }; }, [poll]);

    const act = async (kind: "inject" | "diagnose" | "energy") => {
        setBusy(kind);
        try {
            if (kind === "inject") await fetch(`${API_BASE}/factory/inject`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ report: "welding cell 3 is overheating and vibrating, urgent", run_loop: true }) });
            else if (kind === "diagnose") await fetch(`${API_BASE}/factory/diagnose`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
            else await fetch(`${API_BASE}/facilities/optimize-energy`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ required_slots: 6, demand_cap_kw: 100 }) });
            await poll();
        } catch { /* ignore */ } finally { setBusy(null); }
    };

    const now = Date.now();
    const activation = (id: string) => { const t = activeAt[id]; return t && now - t < ACTIVE_MS ? 1 - (now - t) / ACTIVE_MS : 0; };
    const troubled = (snap?.stages ?? []).filter((s) => !["nominal", "running"].includes(s.status?.toLowerCase()));

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white">
            <Navigation />
            <main className="p-4 max-w-[1600px] mx-auto">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2"><Brain className="w-6 h-6 text-cyan-400" />Embodied AI — agent coordination, live</h1>
                        <p className="text-sm text-[#8892a4]">The real head-agents, what each does, and which is acting now — read from the live audit chain. Trigger an action and watch the right agent light up.</p>
                    </div>
                    <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm ${online ? "border-green-500/40 bg-green-500/10" : "border-red-500/40 bg-red-500/10"}`}>
                        <span className={`w-2 h-2 rounded-full ${online ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />{online ? "LIVE" : "offline"}
                    </span>
                </div>

                {/* real context */}
                <div className="glass p-3 mb-4 text-sm text-[#8892a4] flex flex-wrap gap-4">
                    <span>line throughput <b className="text-white">{Math.round(snap?.throughput_units_per_hour ?? 0)}</b>/hr</span>
                    <span>stages not nominal <b className={troubled.length ? "text-red-400" : "text-white"}>{troubled.length}</b></span>
                    <span>incidents fired <b className="text-white">{snap?.incidents_fired_count ?? 0}</b></span>
                </div>

                {/* triggers */}
                <div className="flex flex-wrap gap-2 mb-4">
                    <button onClick={() => act("inject")} disabled={busy !== null || online === false} className="px-3 py-1.5 text-sm bg-yellow-500/90 hover:bg-yellow-500 text-black font-semibold rounded-lg disabled:opacity-40 flex items-center gap-1.5"><AlertTriangle className="w-4 h-4" />{busy === "inject" ? "…" : "Inject problem"}</button>
                    <button onClick={() => act("diagnose")} disabled={busy !== null || online === false} className="px-3 py-1.5 text-sm bg-purple-500/90 hover:bg-purple-500 rounded-lg disabled:opacity-40 flex items-center gap-1.5"><Search className="w-4 h-4" />{busy === "diagnose" ? "…" : "Active diagnosis"}</button>
                    <button onClick={() => act("energy")} disabled={busy !== null || online === false} className="px-3 py-1.5 text-sm bg-cyan-500/90 hover:bg-cyan-500 text-black font-semibold rounded-lg disabled:opacity-40 flex items-center gap-1.5"><Zap className="w-4 h-4" />{busy === "energy" ? "…" : "Optimise energy"}</button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* agent cards */}
                    <section className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-3">
                        {AGENTS.map((a) => {
                            const on = activation(a.id) > 0;
                            return (
                                <div key={a.id} className={`glass p-4 border transition-colors ${on ? "border-cyan-500/60 bg-cyan-500/5" : "border-[#2a3346]"}`}>
                                    <div className="flex items-center justify-between mb-1">
                                        <h3 className="font-semibold text-sm flex items-center gap-2">{a.label}</h3>
                                        <span className={`flex items-center gap-1 text-[11px] ${on ? "text-cyan-400" : "text-[#6b7280]"}`}>
                                            <span className={`w-2 h-2 rounded-full ${on ? "bg-cyan-400 animate-pulse" : "bg-gray-600"}`} />{on ? "ACTIVE" : "idle"}
                                        </span>
                                    </div>
                                    <p className="text-xs text-[#8892a4] mb-2">{a.role}</p>
                                    {lastAction[a.id] && <div className="text-[11px] text-[#6b7280]">last action: <span className="font-mono text-[#b9c2d0]">{lastAction[a.id]}</span></div>}
                                </div>
                            );
                        })}
                    </section>

                    {/* real activity feed */}
                    <section className="glass p-4">
                        <h2 className="font-semibold flex items-center gap-2 mb-1"><Brain className="w-4 h-4 text-cyan-400" />Live decisions <span className="text-xs text-[#8892a4]">(GET /ops/cascade)</span></h2>
                        <p className="text-xs text-[#8892a4] mb-3">Real signed <span className="font-mono">audit_chain</span> rows — the actual agent, action and sequence. This is the EU-AI-Act Art-12 evidence trail.</p>
                        <div className="space-y-1.5 max-h-[420px] overflow-y-auto">
                            {rows.length === 0 && <div className="text-sm text-[#8892a4]">No decisions yet — press a trigger above.</div>}
                            {rows.map((r) => (
                                <div key={r.seq} className="text-xs p-2 rounded bg-[#0d1220] border-l-2 border-cyan-500/40">
                                    <div className="flex items-center justify-between"><span className="font-mono text-cyan-400">{r.actor}</span><span className="text-[#6b7280]">#{r.seq}</span></div>
                                    <div className="text-[#8892a4]">{r.action}</div>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>

                {online === false && <div className="glass p-4 mt-4 border border-red-500/30 text-sm text-red-300">Backend at <span className="font-mono">{API_BASE}</span> unreachable — real data only.</div>}
                <p className="text-xs text-[#6b7280] mt-4">Which agent is &quot;active&quot; is determined by real signed audit-chain actions, and each stays lit ~8&nbsp;s so it&apos;s clearly visible. No fabricated agents, no fake activity.</p>
            </main>
        </div>
    );
}
