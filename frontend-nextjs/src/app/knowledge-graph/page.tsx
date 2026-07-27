"use client";

// =============================================================================
// Knowledge Graph — LIVE, 100% backend-driven. No mock data.
//   • ISA-95 plant graph -> GET /api/simulation/snapshot   (real stages / robots / suppliers as nodes)
//   • agent activation   -> GET /ops/cascade               (real signed audit rows: which agent acted, when)
//   • trigger activity   -> POST /factory/inject · POST /facilities/optimize-energy
// An agent node lights up when it appears in the real audit chain, and stays lit for ~8s so it's clearly visible.
// =============================================================================

import { useCallback, useEffect, useRef, useState } from "react";
import Navigation from "@/components/Navigation";
import { Share2, Zap, AlertTriangle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ACTIVE_MS = 8000; // how long an agent stays visibly "active" after its last real audit row

interface Stage { stage_id: number; name: string; status: string; }
interface Snapshot { stages: Stage[]; robots: unknown[]; suppliers: unknown[]; }
interface CascadeRow { seq: number; ts: string; actor: string; action: string; }

// map a real audit-chain actor -> one of our head-agent node ids
function actorToAgent(actor: string): string | null {
    const a = actor.toLowerCase();
    if (a.includes("facilit") || a.includes("energy")) return "facilities";
    if (a.includes("supply") || a.includes("inventory") || a.includes("jit")) return "supply";
    if (a.includes("repair") || a.includes("dispatch") || a.includes("master") || a.includes("sil")) return "repair";
    if (a.includes("cdc") || a.includes("reason") || a.includes("diagnos")) return "diagnosis";
    if (a.includes("slice") || a.includes("manufact") || a.includes("pdm") || a.includes("robot")) return "manufacturing";
    return "runtime";
}

const AGENTS: { id: string; label: string; x: number; y: number }[] = [
    { id: "diagnosis",     label: "Diagnosis / Causal", x: 130, y: 70 },
    { id: "manufacturing", label: "Manufacturing",      x: 400, y: 55 },
    { id: "repair",        label: "Repair / Safety",    x: 670, y: 70 },
    { id: "supply",        label: "Supply-Chain",       x: 130, y: 330 },
    { id: "facilities",    label: "Facilities / Energy",x: 670, y: 330 },
];

const statusColor = (s: string) => {
    const x = s?.toLowerCase();
    if (x === "broken" || x === "down") return "#ef4444";
    if (x === "degraded" || x === "warning") return "#eab308";
    if (x === "maintenance") return "#3b82f6";
    return "#22c55e";
};

export default function KnowledgeGraphPage() {
    const [snap, setSnap] = useState<Snapshot | null>(null);
    const [online, setOnline] = useState<boolean | null>(null);
    const [rows, setRows] = useState<CascadeRow[]>([]);
    const [busy, setBusy] = useState<string | null>(null);
    // agentId -> last-active wall-clock ms
    const [activeAt, setActiveAt] = useState<Record<string, number>>({});
    const [, force] = useState(0); // re-render tick so fading is smooth
    const timer = useRef<ReturnType<typeof setInterval> | null>(null);
    const seenSeq = useRef<number>(0);

    const poll = useCallback(async () => {
        try {
            const s = await fetch(`${API_BASE}/api/simulation/snapshot`, { cache: "no-store" });
            if (s.ok) { setSnap(await s.json()); setOnline(true); } else throw new Error();
        } catch { setOnline(false); }
        try {
            const c = await fetch(`${API_BASE}/ops/cascade`, { cache: "no-store" });
            if (c.ok) {
                const d = await c.json();
                const sys: CascadeRow[] = d.system ?? [];
                setRows(sys.slice(-10).reverse());
                // light up agents for any NEW audit rows (seq we haven't seen)
                const now = Date.now();
                const upd: Record<string, number> = {};
                for (const r of sys) {
                    if (r.seq > seenSeq.current) {
                        const ag = actorToAgent(r.actor);
                        if (ag) upd[ag] = now;
                    }
                }
                if (sys.length) seenSeq.current = Math.max(seenSeq.current, ...sys.map((r) => r.seq));
                if (Object.keys(upd).length) setActiveAt((prev) => ({ ...prev, ...upd }));
            }
        } catch { /* best-effort */ }
    }, []);

    useEffect(() => {
        poll();
        timer.current = setInterval(() => { poll(); force((n) => n + 1); }, 1500);
        return () => { if (timer.current) clearInterval(timer.current); };
    }, [poll]);

    const trigger = async (kind: "inject" | "energy") => {
        setBusy(kind);
        try {
            if (kind === "inject") await fetch(`${API_BASE}/factory/inject`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ report: "welding cell 3 is overheating and vibrating, urgent", run_loop: true }) });
            else await fetch(`${API_BASE}/facilities/optimize-energy`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ required_slots: 6, demand_cap_kw: 100 }) });
            await poll();
        } catch { /* ignore */ } finally { setBusy(null); }
    };

    const now = Date.now();
    const activation = (id: string) => { const t = activeAt[id]; if (!t) return 0; const age = now - t; return age < ACTIVE_MS ? 1 - age / ACTIVE_MS : 0; };
    const stages = (snap?.stages ?? []).slice().sort((a, b) => a.stage_id - b.stage_id);

    // layout: production line stages across the middle band
    const lineY = 200, x0 = 120, x1 = 680;
    const stageX = (i: number) => stages.length <= 1 ? (x0 + x1) / 2 : x0 + (i * (x1 - x0)) / (stages.length - 1);

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white">
            <Navigation />
            <main className="p-4 max-w-[1600px] mx-auto">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2"><Share2 className="w-6 h-6 text-cyan-400" />Knowledge Graph — agents &amp; plant, live</h1>
                        <p className="text-sm text-[#8892a4]">The real ISA-95 plant (from the SimWorld snapshot) with head-agents that light up when they act in the real audit chain. Trigger an action and watch an agent activate.</p>
                    </div>
                    <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm ${online ? "border-green-500/40 bg-green-500/10" : "border-red-500/40 bg-red-500/10"}`}>
                        <span className={`w-2 h-2 rounded-full ${online ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />{online ? "LIVE" : "offline"}
                    </span>
                </div>

                <div className="flex flex-wrap gap-2 mb-4">
                    <button onClick={() => trigger("inject")} disabled={busy !== null || online === false} className="px-3 py-1.5 text-sm bg-yellow-500/90 hover:bg-yellow-500 text-black font-semibold rounded-lg disabled:opacity-40 flex items-center gap-1.5"><AlertTriangle className="w-4 h-4" />{busy === "inject" ? "injecting…" : "Trigger problem → diagnosis + repair"}</button>
                    <button onClick={() => trigger("energy")} disabled={busy !== null || online === false} className="px-3 py-1.5 text-sm bg-cyan-500/90 hover:bg-cyan-500 text-black font-semibold rounded-lg disabled:opacity-40 flex items-center gap-1.5"><Zap className="w-4 h-4" />{busy === "energy" ? "optimising…" : "Trigger energy optimise → facilities agent"}</button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* the graph */}
                    <section className="lg:col-span-2 glass p-2">
                        <svg viewBox="0 0 800 400" className="w-full">
                            {/* edges: line -> stages */}
                            {stages.map((s, i) => <line key={`e${s.stage_id}`} x1={400} y1={140} x2={stageX(i)} y2={lineY} stroke="#2a3346" strokeWidth={1} />)}
                            {/* edges: agents -> what they act on */}
                            {AGENTS.map((a) => <line key={`ea${a.id}`} x1={a.x} y1={a.y} x2={400} y2={a.id === "supply" || a.id === "facilities" ? 200 : 140} stroke={activation(a.id) > 0 ? "#22d3ee" : "#232b3d"} strokeWidth={activation(a.id) > 0 ? 2 : 1} />)}

                            {/* central: production line hub */}
                            <g>
                                <rect x={345} y={118} width={110} height={44} rx={9} fill="#131a2b" stroke="#3a4358" />
                                <text x={400} y={138} textAnchor="middle" fontSize={12} fill="#dbe2ea" fontWeight="700">Production Line</text>
                                <text x={400} y={153} textAnchor="middle" fontSize={10} fill="#8892a4">ISA-95</text>
                            </g>

                            {/* stage nodes (real, coloured by status) */}
                            {stages.map((s, i) => (
                                <g key={s.stage_id}>
                                    <circle cx={stageX(i)} cy={lineY} r={11} fill={statusColor(s.status)} opacity={0.9} />
                                    <text x={stageX(i)} y={lineY + 26} textAnchor="middle" fontSize={9} fill="#8892a4">{s.name}</text>
                                </g>
                            ))}

                            {/* agent nodes (light up on real activity, linger ~8s) */}
                            {AGENTS.map((a) => {
                                const act = activation(a.id);
                                return (
                                    <g key={a.id}>
                                        {act > 0 && <circle cx={a.x} cy={a.y} r={26 + act * 8} fill="#22d3ee" opacity={0.12 * act} />}
                                        <circle cx={a.x} cy={a.y} r={20} fill={act > 0 ? "#0e7490" : "#161d2e"} stroke={act > 0 ? "#22d3ee" : "#3a4358"} strokeWidth={act > 0 ? 2.5 : 1.5} />
                                        <text x={a.x} y={a.y + 4} textAnchor="middle" fontSize={13}>{"🤖"}</text>
                                        <text x={a.x} y={a.y + (a.y < 200 ? -28 : 36)} textAnchor="middle" fontSize={10.5} fill={act > 0 ? "#67e8f9" : "#8892a4"} fontWeight={act > 0 ? "700" : "400"}>{a.label}</text>
                                    </g>
                                );
                            })}
                        </svg>
                        <div className="flex flex-wrap gap-3 text-xs text-[#8892a4] px-3 pb-2">
                            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full" style={{ background: "#22c55e" }} />running</span>
                            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full" style={{ background: "#eab308" }} />degraded</span>
                            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full" style={{ background: "#ef4444" }} />broken</span>
                            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full" style={{ background: "#3b82f6" }} />maintenance</span>
                            <span className="flex items-center gap-1.5 ml-auto"><span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />agent active (from the audit chain)</span>
                        </div>
                    </section>

                    {/* real activity log */}
                    <section className="glass p-4">
                        <h2 className="font-semibold flex items-center gap-2 mb-1"><Share2 className="w-4 h-4 text-cyan-400" />Agent activity <span className="text-xs text-[#8892a4]">(GET /ops/cascade)</span></h2>
                        <p className="text-xs text-[#8892a4] mb-3">Every row is a real, signed <span className="font-mono">audit_chain</span> action — the actual agent that acted, its action, and its sequence number.</p>
                        <div className="space-y-1.5 max-h-[380px] overflow-y-auto">
                            {rows.length === 0 && <div className="text-sm text-[#8892a4]">No agent actions yet — press a trigger above.</div>}
                            {rows.map((r) => {
                                const ag = actorToAgent(r.actor);
                                const fresh = ag ? activation(ag) > 0 : false;
                                return (
                                    <div key={r.seq} className={`text-xs p-2 rounded border-l-2 ${fresh ? "bg-cyan-500/10 border-cyan-500" : "bg-[#0d1220] border-[#2a3346]"}`}>
                                        <div className="flex items-center justify-between">
                                            <span className="font-mono text-cyan-400">{r.actor}</span>
                                            <span className="text-[#6b7280]">#{r.seq}</span>
                                        </div>
                                        <div className="text-[#8892a4]">{r.action}</div>
                                    </div>
                                );
                            })}
                        </div>
                    </section>
                </div>

                {online === false && <div className="glass p-4 mt-4 border border-red-500/30 text-sm text-red-300">Backend at <span className="font-mono">{API_BASE}</span> unreachable — real data only.</div>}
                <p className="text-xs text-[#6b7280] mt-4">The graph nodes are the real plant entities from the SimWorld snapshot; agent activation is read from the real signed audit chain. An agent stays highlighted for ~8&nbsp;s after it acts so you can clearly see who did what — no fabricated motion.</p>
            </main>
        </div>
    );
}
