"use client";

// =============================================================================
// Manufacturing — LIVE, 100% backend-driven. No mock data, no local animation.
//   • production line -> GET  /api/simulation/snapshot        (real SimWorld stages, in flow order)
//   • energy solution -> POST /facilities/optimize-energy     (real MILP peak-shaving / load-shifting)
//   • reset line      -> POST /api/simulation/reset-world
// The line shows the real product flow; the energy optimiser is the real "how it's solved".
// =============================================================================

import { useCallback, useEffect, useRef, useState } from "react";
import Navigation from "@/components/Navigation";
import { Factory, Zap, ArrowRight, Activity, AlertTriangle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Stage { stage_id: number; name: string; status: string; queue_depth: number; defect_rate_effective: number; breakdown_count: number; units_produced: number; }
interface Snapshot { sim_time_seconds: number; stages: Stage[]; throughput_units_per_hour?: number; }
interface Energy {
    method: string; baseline_peak_kw: number; optimized_peak_kw: number; baseline_cost: number; optimized_cost: number;
    peak_reduction_pct: number; cost_reduction_pct: number; diagnosed: string | null; allowed: boolean; committed: boolean; audit_seq?: number;
}

const STATUS: Record<string, { dot: string; ring: string; text: string; label: string }> = {
    nominal:     { dot: "bg-green-400",  ring: "border-green-500/40",  text: "text-green-400",  label: "running" },
    running:     { dot: "bg-green-400",  ring: "border-green-500/40",  text: "text-green-400",  label: "running" },
    degraded:    { dot: "bg-yellow-400", ring: "border-yellow-500/50", text: "text-yellow-400", label: "degrading" },
    warning:     { dot: "bg-yellow-400", ring: "border-yellow-500/50", text: "text-yellow-400", label: "warning" },
    broken:      { dot: "bg-red-500",    ring: "border-red-500/60",    text: "text-red-400",    label: "broken (bottleneck)" },
    down:        { dot: "bg-red-500",    ring: "border-red-500/60",    text: "text-red-400",    label: "down" },
    maintenance: { dot: "bg-blue-400",   ring: "border-blue-500/50",   text: "text-blue-400",   label: "maintenance" },
};
const sfor = (s: string) => STATUS[s?.toLowerCase()] ?? { dot: "bg-gray-500", ring: "border-gray-600/40", text: "text-gray-400", label: s || "—" };

export default function ManufacturingPage() {
    const [snap, setSnap] = useState<Snapshot | null>(null);
    const [online, setOnline] = useState<boolean | null>(null);
    const [energy, setEnergy] = useState<Energy | null>(null);
    const [optimizing, setOptimizing] = useState(false);
    const [resetting, setResetting] = useState(false);
    const timer = useRef<ReturnType<typeof setInterval> | null>(null);

    const poll = useCallback(async () => {
        try {
            const r = await fetch(`${API_BASE}/api/simulation/snapshot`, { cache: "no-store" });
            if (!r.ok) throw new Error();
            setSnap(await r.json()); setOnline(true);
        } catch { setOnline(false); }
    }, []);
    useEffect(() => { poll(); timer.current = setInterval(poll, 1500); return () => { if (timer.current) clearInterval(timer.current); }; }, [poll]);

    const optimize = async () => {
        setOptimizing(true); setEnergy(null);
        try {
            const r = await fetch(`${API_BASE}/facilities/optimize-energy`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ required_slots: 6, demand_cap_kw: 100 }),
            });
            setEnergy(await r.json());
        } catch { /* leave null */ }
        finally { setOptimizing(false); }
    };
    const reset = async () => { setResetting(true); try { await fetch(`${API_BASE}/api/simulation/reset-world`, { method: "POST" }); await poll(); } catch {} finally { setResetting(false); } };

    const stages = (snap?.stages ?? []).slice().sort((a, b) => a.stage_id - b.stage_id);
    const troubled = stages.filter((s) => !["nominal", "running"].includes(s.status?.toLowerCase()));

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white">
            <Navigation />
            <main className="p-4 max-w-[1800px] mx-auto">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2"><Factory className="w-6 h-6 text-cyan-400" />Manufacturing — Live production flow</h1>
                        <p className="text-sm text-[#8892a4]">The real product flow through the line (SimWorld), and the real MILP energy optimiser as the solution. Nothing mocked.</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <button onClick={reset} disabled={resetting || online === false} className="px-3 py-1.5 text-sm bg-[#1c2333] hover:bg-[#252d40] border border-[#2a3346] rounded-lg disabled:opacity-40">{resetting ? "Resetting…" : "↻ Reset line"}</button>
                        <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm ${online ? "border-green-500/40 bg-green-500/10" : "border-red-500/40 bg-red-500/10"}`}>
                            <span className={`w-2 h-2 rounded-full ${online ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />{online ? "LIVE" : "offline"}
                        </span>
                    </div>
                </div>

                {/* legend — what the colours mean (you asked) */}
                <div className="glass p-3 mb-4 flex flex-wrap items-center gap-4 text-xs text-[#8892a4]">
                    <span className="font-semibold text-white">Legend:</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-green-400" />running — flowing normally</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-yellow-400" />degrading — quality/throughput slipping</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-red-500" />broken — a bottleneck, its queue backs up</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-blue-400" />maintenance — being repaired</span>
                </div>

                {/* the real production flow, left -> right */}
                <section className="glass p-4 mb-4">
                    <div className="flex items-center justify-between mb-3">
                        <h2 className="font-semibold flex items-center gap-2"><Activity className="w-4 h-4 text-cyan-400" />Production line — product flows left → right</h2>
                        <div className="text-xs text-[#8892a4]">{snap ? <>throughput <b className="text-white">{Math.round(snap.throughput_units_per_hour ?? 0)}</b> units/hr {troubled.length > 0 && <span className="text-red-400 ml-2">· {troubled.length} stage(s) not nominal</span>}</> : "…"}</div>
                    </div>
                    <div className="flex items-stretch gap-1 overflow-x-auto pb-2">
                        {stages.length === 0 && <div className="text-sm text-[#8892a4]">Waiting for live line state…</div>}
                        {stages.map((s, i) => {
                            const st = sfor(s.status);
                            return (
                                <div key={s.stage_id} className="flex items-center">
                                    <div className={`min-w-[120px] bg-[#0d1220] rounded-lg p-3 border ${st.ring}`}>
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="text-xs font-semibold capitalize">{s.name}</span>
                                            <span className={`w-2.5 h-2.5 rounded-full ${st.dot}`} />
                                        </div>
                                        <div className={`text-[10px] mb-2 ${st.text}`}>{st.label}</div>
                                        <div className="text-[11px] text-[#8892a4] space-y-0.5">
                                            <div>queue <b className={`text-white ${s.queue_depth > 15 ? "text-red-400" : ""}`}>{s.queue_depth}</b></div>
                                            <div>defect {(s.defect_rate_effective * 100).toFixed(1)}%</div>
                                            <div>made {s.units_produced}</div>
                                        </div>
                                    </div>
                                    {i < stages.length - 1 && <ArrowRight className="w-4 h-4 text-[#3a4358] shrink-0" />}
                                </div>
                            );
                        })}
                    </div>
                    <p className="text-xs text-[#6b7280] mt-2">Each unit enters at the first stage and flows down the line; a stage&apos;s <b>queue</b> is work waiting on it — a growing queue on a red stage is a bottleneck starving everything downstream.</p>
                </section>

                {/* the solution: real MILP energy optimisation */}
                <section className="glass p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                        <h2 className="font-semibold flex items-center gap-2"><Zap className="w-4 h-4 text-yellow-400" />Energy optimisation — the real solution</h2>
                        <button onClick={optimize} disabled={optimizing || online === false} className="px-3 py-1.5 text-sm bg-yellow-500/90 hover:bg-yellow-500 text-black font-semibold rounded-lg disabled:opacity-40">{optimizing ? "Solving MILP…" : "Optimise energy (peak-shaving)"}</button>
                    </div>
                    <p className="text-xs text-[#8892a4] mb-3">A real mixed-integer program (scipy/HiGHS) shifts schedulable stage load off peak windows to cut the demand-charge peak, subject to the production floor. POST /facilities/optimize-energy.</p>
                    {!energy ? (
                        <div className="text-sm text-[#8892a4]">Press <b>Optimise energy</b> to run the real MILP and see the before/after.</div>
                    ) : (
                        <div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                                <KV label="baseline peak" value={`${energy.baseline_peak_kw} kW`} />
                                <KV label="optimised peak" value={`${energy.optimized_peak_kw} kW`} good />
                                <KV label="peak cut" value={`−${energy.peak_reduction_pct}%`} good />
                                <KV label="cost cut" value={`−${energy.cost_reduction_pct}%`} good />
                            </div>
                            {/* before/after peak bars */}
                            <div className="space-y-2 mb-3">
                                <Bar label="baseline peak" kw={energy.baseline_peak_kw} max={Math.max(energy.baseline_peak_kw, energy.optimized_peak_kw)} color="bg-red-500/70" />
                                <Bar label="optimised peak" kw={energy.optimized_peak_kw} max={Math.max(energy.baseline_peak_kw, energy.optimized_peak_kw)} color="bg-green-500/70" />
                            </div>
                            <div className="text-xs text-[#8892a4]">
                                {energy.diagnosed && <>Diagnosed <b className="text-yellow-400">{energy.diagnosed}</b> → </>}
                                the MILP {energy.committed ? <span className="text-green-400">committed a plan</span> : "produced a plan"} that shaves the peak from <b className="text-white">{energy.baseline_peak_kw} kW</b> to <b className="text-white">{energy.optimized_peak_kw} kW</b> while holding every stage&apos;s required production. Safety-gate: <b className={energy.allowed ? "text-green-400" : "text-red-400"}>{energy.allowed ? "allowed" : "rejected"}</b>{energy.audit_seq != null && <> · signed audit row #{energy.audit_seq}</>}.
                            </div>
                        </div>
                    )}
                </section>

                {online === false && <div className="glass p-4 mt-4 border border-red-500/30 text-sm text-red-300">Backend at <span className="font-mono">{API_BASE}</span> unreachable — real data only, nothing faked.</div>}
                <p className="text-xs text-[#6b7280] mt-4">Every number here is a live backend call — the line state from the SimWorld twin and the energy result from the scipy/HiGHS MILP. No random values, no local animation.</p>
            </main>
        </div>
    );
}

function KV({ label, value, good }: { label: string; value: string; good?: boolean }) {
    return <div className="bg-[#0d1220] rounded-lg p-3 text-center"><div className={`text-lg font-bold ${good ? "text-green-400" : "text-white"}`}>{value}</div><div className="text-[10px] text-[#6b7280]">{label}</div></div>;
}
function Bar({ label, kw, max, color }: { label: string; kw: number; max: number; color: string }) {
    return (
        <div className="flex items-center gap-2 text-xs">
            <span className="w-28 text-[#8892a4] shrink-0">{label}</span>
            <div className="flex-1 h-5 bg-[#1c2333] rounded overflow-hidden"><div className={`h-full ${color} flex items-center justify-end pr-2 text-white font-semibold`} style={{ width: `${max > 0 ? (kw / max) * 100 : 0}%` }}>{kw} kW</div></div>
        </div>
    );
}
