"use client";

// =============================================================================
// Solution Mode — LIVE, 100% backend-driven. Run the REAL self-healing + optimisers
// and read the grounded "how it was solved".
//   • plant        -> GET  /api/simulation/snapshot
//   • self-heal    -> POST /factory/inject (run_loop=true)     (validator-gated self-healing loop)
//   • energy MILP  -> POST /facilities/optimize-energy
//   • supply solve -> POST /api/inventory/jit/auto-order
//   • grounded how -> POST /factory/ask
//   • reset        -> POST /api/simulation/reset-world
// =============================================================================

import { useCallback, useEffect, useRef, useState } from "react";
import Navigation from "@/components/Navigation";
import Link from "next/link";
import { CheckCircle, Zap, Wrench, Truck, Brain, ArrowRight } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Stage { stage_id: number; name: string; status: string; queue_depth: number; }
interface Snapshot { stages: Stage[]; throughput_units_per_hour?: number; }
interface Energy { method: string; baseline_peak_kw: number; optimized_peak_kw: number; peak_reduction_pct: number; cost_reduction_pct: number; diagnosed: string | null; committed: boolean; audit_seq?: number; }

const sc = (s: string) => { const x = s?.toLowerCase(); return x === "broken" || x === "down" ? "text-red-400 border-red-500/50" : x === "degraded" || x === "warning" ? "text-yellow-400 border-yellow-500/50" : x === "maintenance" ? "text-blue-400 border-blue-500/50" : "text-green-400 border-green-500/40"; };

export default function SolutionPage() {
    const [snap, setSnap] = useState<Snapshot | null>(null);
    const [online, setOnline] = useState<boolean | null>(null);
    const [busy, setBusy] = useState<string | null>(null);
    const [log, setLog] = useState<string[]>([]);
    const [energy, setEnergy] = useState<Energy | null>(null);
    const [how, setHow] = useState<string | null>(null);
    const timer = useRef<ReturnType<typeof setInterval> | null>(null);

    const poll = useCallback(async () => { try { const r = await fetch(`${API_BASE}/api/simulation/snapshot`, { cache: "no-store" }); if (r.ok) { setSnap(await r.json()); setOnline(true); } else throw new Error(); } catch { setOnline(false); } }, []);
    useEffect(() => { poll(); timer.current = setInterval(poll, 1500); return () => { if (timer.current) clearInterval(timer.current); }; }, [poll]);

    const addLog = (s: string) => setLog((l) => [s, ...l].slice(0, 8));

    const selfHeal = async () => {
        setBusy("heal");
        try {
            const r = await fetch(`${API_BASE}/factory/inject`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ report: "welding cell 3 is overheating and vibrating, urgent", run_loop: true }) });
            const d = await r.json();
            addLog(`Self-healing loop ran on ${d.loop?.backend ?? "runtime"} — diagnosed ${d.incident?.type ?? "?"} on stage ${d.incident?.target_id ?? "?"} (validator-gated).`);
            const a = await fetch(`${API_BASE}/factory/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: "what was detected and how is it being resolved?" }) });
            if (a.ok) setHow((await a.json()).answer);
            await poll();
        } catch { addLog("backend unreachable"); } finally { setBusy(null); }
    };
    const optimize = async () => {
        setBusy("energy");
        try { const r = await fetch(`${API_BASE}/facilities/optimize-energy`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ required_slots: 6, demand_cap_kw: 100 }) }); const d: Energy = await r.json(); setEnergy(d); addLog(`Energy MILP: peak ${d.baseline_peak_kw}→${d.optimized_peak_kw} kW (−${d.peak_reduction_pct}%), signed audit #${d.audit_seq ?? "—"}.`); } catch { addLog("backend unreachable"); } finally { setBusy(null); }
    };
    const autoOrder = async () => {
        setBusy("supply");
        try { const r = await fetch(`${API_BASE}/api/inventory/jit/auto-order`, { method: "POST" }); const d = await r.json(); addLog(`Supply-chain: placed ${d.orders_created?.length ?? d.orders?.length ?? "the recommended"} JIT order(s) to prevent stockouts.`); } catch { addLog("backend unreachable"); } finally { setBusy(null); }
    };
    const reset = async () => { setBusy("reset"); try { await fetch(`${API_BASE}/api/simulation/reset-world`, { method: "POST" }); setEnergy(null); setHow(null); addLog("Plant reset to nominal."); await poll(); } catch {} finally { setBusy(null); } };

    const stages = (snap?.stages ?? []).slice().sort((a, b) => a.stage_id - b.stage_id);
    const nominal = stages.filter((s) => ["nominal", "running"].includes(s.status?.toLowerCase())).length;

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white">
            <Navigation />
            <main className="p-4 max-w-[1600px] mx-auto">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2"><CheckCircle className="w-6 h-6 text-green-400" />Solution Mode — the system fixes it</h1>
                        <p className="text-sm text-[#8892a4]">Run the real self-healing loop and optimisers, and read the grounded explanation of how it&apos;s solved. Coming from <Link href="/problem" className="text-cyan-400">Problem Mode</Link>?</p>
                    </div>
                    <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm ${online ? "border-green-500/40 bg-green-500/10" : "border-red-500/40 bg-red-500/10"}`}>
                        <span className={`w-2 h-2 rounded-full ${online ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />{online ? "LIVE" : "offline"}
                    </span>
                </div>

                {/* solution actions (all real) */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                    <ActBtn onClick={selfHeal} busy={busy === "heal"} disabled={busy !== null || online === false} icon={<Wrench className="w-4 h-4" />} label="Self-heal (loop)" sub="predict→verify→intervene" color="bg-green-500/90 hover:bg-green-500 text-black" />
                    <ActBtn onClick={optimize} busy={busy === "energy"} disabled={busy !== null || online === false} icon={<Zap className="w-4 h-4" />} label="Optimise energy" sub="real MILP peak-shave" color="bg-yellow-500/90 hover:bg-yellow-500 text-black" />
                    <ActBtn onClick={autoOrder} busy={busy === "supply"} disabled={busy !== null || online === false} icon={<Truck className="w-4 h-4" />} label="Solve supply" sub="auto-place JIT orders" color="bg-cyan-500/90 hover:bg-cyan-500 text-black" />
                    <ActBtn onClick={reset} busy={busy === "reset"} disabled={busy !== null || online === false} icon={<CheckCircle className="w-4 h-4" />} label="Reset plant" sub="fresh nominal state" color="bg-[#1c2333] hover:bg-[#252d40] border border-[#2a3346]" />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <section className="lg:col-span-2 glass p-4">
                        <h2 className="font-semibold flex items-center gap-2 mb-3">Live line <span className={`text-xs px-2 py-0.5 rounded ${nominal === stages.length && stages.length ? "bg-green-500/15 text-green-300" : "bg-yellow-500/15 text-yellow-300"}`}>{stages.length ? `${nominal}/${stages.length} nominal` : "…"}</span></h2>
                        <div className="flex items-center gap-1 overflow-x-auto pb-2">
                            {stages.map((s, i) => (
                                <div key={s.stage_id} className="flex items-center">
                                    <div className={`min-w-[110px] bg-[#0d1220] rounded-lg p-2.5 border ${sc(s.status)}`}>
                                        <div className="text-xs font-semibold capitalize">{s.name}</div>
                                        <div className={`text-[10px] capitalize ${sc(s.status).split(" ")[0]}`}>{s.status}</div>
                                    </div>
                                    {i < stages.length - 1 && <ArrowRight className="w-3.5 h-3.5 text-[#3a4358] shrink-0" />}
                                </div>
                            ))}
                        </div>
                        {energy && (
                            <div className="mt-3 bg-[#0d1220] rounded-lg p-3 text-sm">
                                <div className="text-xs text-[#8892a4] mb-1">Energy MILP result (real):</div>
                                peak <b className="text-white">{energy.baseline_peak_kw}</b> → <b className="text-green-400">{energy.optimized_peak_kw} kW</b> (−{energy.peak_reduction_pct}%), cost −{energy.cost_reduction_pct}%{energy.audit_seq != null && <span className="text-[#6b7280]"> · signed #{energy.audit_seq}</span>}
                            </div>
                        )}
                        {how && (
                            <div className="mt-3 bg-[#0d1220] rounded-lg p-3">
                                <div className="text-xs text-purple-400 flex items-center gap-1 mb-1"><Brain className="w-3.5 h-3.5" />grounded explanation</div>
                                <p className="text-sm text-[#dbe2ea]">{how}</p>
                            </div>
                        )}
                    </section>
                    <section className="glass p-4">
                        <h2 className="font-semibold mb-2">Action log (real)</h2>
                        <div className="space-y-1.5">
                            {log.length === 0 && <div className="text-sm text-[#8892a4]">Run a solution action above.</div>}
                            {log.map((l, i) => <div key={i} className="text-xs p-2 rounded bg-[#0d1220] border-l-2 border-green-500/40 text-[#b9c2d0]">{l}</div>)}
                        </div>
                    </section>
                </div>

                {online === false && <div className="glass p-4 mt-4 border border-red-500/30 text-sm text-red-300">Backend at <span className="font-mono">{API_BASE}</span> unreachable — real data only.</div>}
                <p className="text-xs text-[#6b7280] mt-4">Every action is a real backend operation — the safety-gated self-healing loop, the scipy/HiGHS energy MILP, and the JIT supply optimiser — with grounded reasoning. No fabricated resolution.</p>
            </main>
        </div>
    );
}

function ActBtn({ onClick, busy, disabled, icon, label, sub, color }: { onClick: () => void; busy: boolean; disabled: boolean; icon: React.ReactNode; label: string; sub: string; color: string }) {
    return (
        <button onClick={onClick} disabled={disabled} className={`rounded-lg p-3 text-left disabled:opacity-40 ${color}`}>
            <div className="flex items-center gap-1.5 font-semibold text-sm">{icon}{busy ? "…" : label}</div>
            <div className="text-[10px] opacity-80 mt-0.5">{sub}</div>
        </button>
    );
}
