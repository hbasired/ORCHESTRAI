"use client";

// =============================================================================
// Problem Mode — LIVE, 100% backend-driven. Inject a REAL problem and watch the
// plant react + read the real diagnosis and grounded "why".
//   • plant   -> GET  /api/simulation/snapshot
//   • inject  -> POST /factory/inject   (real LLM parse -> validated incident)
//   • why     -> POST /factory/ask      (grounded, honest-empty)
//   • reset   -> POST /api/simulation/reset-world
// =============================================================================

import { useCallback, useEffect, useRef, useState } from "react";
import Navigation from "@/components/Navigation";
import Link from "next/link";
import { AlertTriangle, Brain, ArrowRight } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Stage { stage_id: number; name: string; status: string; queue_depth: number; defect_rate_effective: number; }
interface Snapshot { stages: Stage[]; throughput_units_per_hour?: number; incidents_fired_count?: number; recent_incidents?: { type: string; target_id: number | null; severity: string }[]; }
interface Incident { type: string; target_id: number | null; severity: string; confidence: number; }
interface InjectResult { accepted: boolean; method?: string; incident?: Incident; reason?: string; }

const SCENARIOS = [
    { label: "Welding cell overheating", report: "welding cell 3 is overheating and vibrating badly, urgent" },
    { label: "Defect surge on machining", report: "there is a sudden defect surge on the machining stage, quality is dropping fast" },
    { label: "Robot 2 down", report: "robot 2 has stopped moving and is unresponsive on the line" },
    { label: "Power spike on the press", report: "the press stage is drawing abnormally high power, energy is spiking" },
];
const sc = (s: string) => { const x = s?.toLowerCase(); return x === "broken" || x === "down" ? "text-red-400 border-red-500/50" : x === "degraded" || x === "warning" ? "text-yellow-400 border-yellow-500/50" : x === "maintenance" ? "text-blue-400 border-blue-500/50" : "text-green-400 border-green-500/40"; };

export default function ProblemPage() {
    const [snap, setSnap] = useState<Snapshot | null>(null);
    const [online, setOnline] = useState<boolean | null>(null);
    const [scenario, setScenario] = useState(SCENARIOS[0].report);
    const [busy, setBusy] = useState(false);
    const [res, setRes] = useState<InjectResult | null>(null);
    const [why, setWhy] = useState<string | null>(null);
    const timer = useRef<ReturnType<typeof setInterval> | null>(null);

    const poll = useCallback(async () => { try { const r = await fetch(`${API_BASE}/api/simulation/snapshot`, { cache: "no-store" }); if (r.ok) { setSnap(await r.json()); setOnline(true); } else throw new Error(); } catch { setOnline(false); } }, []);
    useEffect(() => { poll(); timer.current = setInterval(poll, 1500); return () => { if (timer.current) clearInterval(timer.current); }; }, [poll]);

    const inject = async () => {
        setBusy(true); setRes(null); setWhy(null);
        try {
            const r = await fetch(`${API_BASE}/factory/inject`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ report: scenario, run_loop: false }) });
            const d: InjectResult = await r.json(); setRes(d); await poll();
            // grounded "why is this happening" from real evidence
            const a = await fetch(`${API_BASE}/factory/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: "what is currently wrong on the line and why?" }) });
            if (a.ok) setWhy((await a.json()).answer);
        } catch { setRes({ accepted: false, reason: "backend unreachable" }); } finally { setBusy(false); }
    };
    const reset = async () => { setBusy(true); try { await fetch(`${API_BASE}/api/simulation/reset-world`, { method: "POST" }); setRes(null); setWhy(null); await poll(); } catch {} finally { setBusy(false); } };

    const stages = (snap?.stages ?? []).slice().sort((a, b) => a.stage_id - b.stage_id);
    const troubled = stages.filter((s) => !["nominal", "running"].includes(s.status?.toLowerCase()));

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white">
            <Navigation />
            <main className="p-4 max-w-[1600px] mx-auto">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2"><AlertTriangle className="w-6 h-6 text-red-400" />Problem Mode — see what goes wrong</h1>
                        <p className="text-sm text-[#8892a4]">Inject a real problem, watch the live plant react, and read the real diagnosis + grounded reasoning. Then flip to <Link href="/solution" className="text-cyan-400">Solution Mode</Link> to fix it.</p>
                    </div>
                    <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm ${online ? "border-green-500/40 bg-green-500/10" : "border-red-500/40 bg-red-500/10"}`}>
                        <span className={`w-2 h-2 rounded-full ${online ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />{online ? "LIVE" : "offline"}
                    </span>
                </div>

                <div className="glass p-4 mb-4">
                    <div className="flex flex-wrap items-end gap-2">
                        <div className="flex-1 min-w-[220px]">
                            <label className="text-xs text-[#8892a4]">Choose a problem to inject</label>
                            <select value={scenario} onChange={(e) => setScenario(e.target.value)} className="w-full mt-1 bg-[#0d1220] border border-[#2a3346] rounded-lg px-3 py-2 text-sm">
                                {SCENARIOS.map((s) => <option key={s.label} value={s.report}>{s.label}</option>)}
                            </select>
                        </div>
                        <button onClick={inject} disabled={busy || online === false} className="bg-red-500/90 hover:bg-red-500 text-white font-semibold rounded-lg px-4 py-2 text-sm disabled:opacity-40">{busy ? "injecting…" : "Inject problem"}</button>
                        <button onClick={reset} disabled={busy || online === false} className="bg-[#1c2333] hover:bg-[#252d40] border border-[#2a3346] rounded-lg px-3 py-2 text-sm disabled:opacity-40">↻ Reset</button>
                    </div>
                    <div className="text-[11px] text-[#6b7280] mt-1 italic">“{scenario}”</div>
                    {res && (res.accepted && res.incident ? (
                        <div className="mt-3 bg-[#0d1220] rounded-lg p-3 border border-red-500/30 text-sm">
                            <span className="text-xs text-[#8892a4]">Diagnosed ({res.method}): </span>
                            <span className="px-2 py-0.5 rounded bg-red-500/15 text-red-300 text-xs">{res.incident.type}</span>
                            <span className="text-xs text-[#8892a4]"> · stage {res.incident.target_id ?? "—"} · {res.incident.severity} · conf {(res.incident.confidence * 100).toFixed(0)}%</span>
                        </div>
                    ) : <div className="mt-3 text-xs text-[#8892a4]">Not accepted: {res.reason ?? "no actionable incident (honest abstain)."}</div>)}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <section className="lg:col-span-2 glass p-4">
                        <h2 className="font-semibold flex items-center gap-2 mb-3">Live line {troubled.length > 0 && <span className="text-xs px-2 py-0.5 rounded bg-red-500/15 text-red-300">{troubled.length} problem stage(s)</span>}</h2>
                        <div className="flex items-center gap-1 overflow-x-auto pb-2">
                            {stages.map((s, i) => (
                                <div key={s.stage_id} className="flex items-center">
                                    <div className={`min-w-[110px] bg-[#0d1220] rounded-lg p-2.5 border ${sc(s.status)}`}>
                                        <div className="text-xs font-semibold capitalize">{s.name}</div>
                                        <div className={`text-[10px] capitalize ${sc(s.status).split(" ")[0]}`}>{s.status}</div>
                                        <div className="text-[10px] text-[#6b7280] mt-1">queue {s.queue_depth} · defect {(s.defect_rate_effective * 100).toFixed(1)}%</div>
                                    </div>
                                    {i < stages.length - 1 && <ArrowRight className="w-3.5 h-3.5 text-[#3a4358] shrink-0" />}
                                </div>
                            ))}
                        </div>
                    </section>
                    <section className="glass p-4">
                        <h2 className="font-semibold flex items-center gap-2 mb-1"><Brain className="w-4 h-4 text-purple-400" />Why? (grounded)</h2>
                        <p className="text-xs text-[#8892a4] mb-2">From real evidence via /factory/ask — honest-empty if nothing grounds it.</p>
                        {why ? <p className="text-sm text-[#dbe2ea] bg-[#0d1220] rounded-lg p-3">{why}</p> : <div className="text-sm text-[#8892a4]">Inject a problem to see the grounded explanation.</div>}
                        {(snap?.recent_incidents?.length ?? 0) > 0 && (
                            <div className="mt-3">
                                <div className="text-xs text-[#8892a4] mb-1">recent incidents (real):</div>
                                {snap?.recent_incidents?.slice().reverse().map((e, i) => <div key={i} className="text-xs text-[#b9c2d0]">• <span className="capitalize">{e.type.replace(/_/g, " ")}</span> · stage {e.target_id ?? "—"} · {e.severity}</div>)}
                            </div>
                        )}
                    </section>
                </div>

                {online === false && <div className="glass p-4 mt-4 border border-red-500/30 text-sm text-red-300">Backend at <span className="font-mono">{API_BASE}</span> unreachable — real data only.</div>}
                <p className="text-xs text-[#6b7280] mt-4">Everything here is a real backend operation. Ready to fix it? → <Link href="/solution" className="text-cyan-400">Solution Mode</Link>.</p>
            </main>
        </div>
    );
}
