"use client";

// =============================================================================
// Factory Intelligence — LIVE, 100% backend-driven. No mock data, no local
// animation. Every value here comes from a real backend operation:
//   • live plant state  -> GET  /api/simulation/snapshot   (the real SimWorld digital twin)
//   • inject a problem  -> POST /factory/inject            (real Groq-LLM parse -> validated incident)
//   • reasoning "why?"  -> POST /factory/ask               (grounded evidence + citations, honest-empty)
//   • live event feed   -> GET  /api/simulation/events
// If the backend is unreachable the page says so — it never fabricates.
// =============================================================================

import { useCallback, useEffect, useRef, useState } from "react";
import Navigation from "@/components/Navigation";
import { Activity, Brain, Zap, AlertTriangle, Send, Cpu, Boxes, Truck } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---- real backend shapes ----------------------------------------------------
interface Stage {
    stage_id: number; name: string; status: string; queue_depth: number;
    defect_rate_effective: number; breakdown_count: number; units_produced: number;
    time_broken_seconds: number;
}
interface Robot { robot_id?: number; id?: number; status?: string; battery?: number; }
interface Snapshot {
    sim_time_seconds: number; stages: Stage[]; robots: Robot[];
    throughput_units_per_hour?: number; amr_utilization?: number;
    orders_complete?: number; incidents_fired_count?: number;
    recent_incidents?: { type: string; target_id: number | null; severity: string }[];
}
interface Incident { type: string; target_id: number | null; severity: string; confidence: number; raw_text?: string; }
interface InjectResult { accepted: boolean; method?: string; incident?: Incident; note?: string; reason?: string;
    loop?: { backend?: string; decisions?: unknown[]; audit_seqs?: number[] }; }
interface AskResult { grounded: boolean; answer: string; citations: string[]; }

// ---- realistic problems (natural language — the backend LLM parses each) -----
const SCENARIOS: { label: string; report: string; hint: string }[] = [
    { label: "Welding cell overheating", report: "welding cell 3 is overheating and vibrating badly, urgent", hint: "→ machine_crack on a stage" },
    { label: "Defect surge (quality)", report: "there is a sudden defect surge on the machining stage, quality is dropping fast", hint: "→ defect_surge" },
    { label: "Robot down", report: "robot 2 has stopped moving and is unresponsive on the line", hint: "→ robot_down" },
    { label: "Supplier delivery delayed", report: "the steel-sheet supplier delivery is delayed by two days, we are running low", hint: "→ late_delivery" },
    { label: "Power spike on the press", report: "the press stage is drawing abnormally high power, energy is spiking", hint: "→ power_dip / energy" },
];

const STATUS_STYLE: Record<string, { dot: string; ring: string; label: string }> = {
    nominal:     { dot: "bg-green-400",  ring: "border-green-500/40",  label: "running" },
    running:     { dot: "bg-green-400",  ring: "border-green-500/40",  label: "running" },
    degraded:    { dot: "bg-yellow-400", ring: "border-yellow-500/50", label: "degraded" },
    warning:     { dot: "bg-yellow-400", ring: "border-yellow-500/50", label: "warning" },
    broken:      { dot: "bg-red-500",    ring: "border-red-500/60",    label: "broken" },
    down:        { dot: "bg-red-500",    ring: "border-red-500/60",    label: "down" },
    maintenance: { dot: "bg-blue-400",   ring: "border-blue-500/50",   label: "maintenance" },
};
const styleFor = (s: string) => STATUS_STYLE[s?.toLowerCase()] ?? { dot: "bg-gray-500", ring: "border-gray-600/40", label: s || "—" };

export default function FactoryPage() {
    const [snap, setSnap] = useState<Snapshot | null>(null);
    const [online, setOnline] = useState<boolean | null>(null); // null=connecting
    const [scenario, setScenario] = useState(SCENARIOS[0].report);
    const [injecting, setInjecting] = useState(false);
    const [injectRes, setInjectRes] = useState<InjectResult | null>(null);
    const [question, setQuestion] = useState("what is happening on the line right now and why?");
    const [asking, setAsking] = useState(false);
    const [ask, setAsk] = useState<AskResult | null>(null);
    const [resetting, setResetting] = useState(false);
    const timer = useRef<ReturnType<typeof setInterval> | null>(null);

    // ---- live polling of the REAL SimWorld snapshot + event feed ----
    const poll = useCallback(async () => {
        try {
            const r = await fetch(`${API_BASE}/api/simulation/snapshot`, { cache: "no-store" });
            if (!r.ok) throw new Error(String(r.status));
            setSnap(await r.json()); setOnline(true);
        } catch { setOnline(false); }
    }, []);

    useEffect(() => {
        poll();
        timer.current = setInterval(poll, 1500);
        return () => { if (timer.current) clearInterval(timer.current); };
    }, [poll]);

    const inject = async () => {
        setInjecting(true); setInjectRes(null);
        try {
            const r = await fetch(`${API_BASE}/factory/inject`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ report: scenario, run_loop: true }),
            });
            setInjectRes(await r.json());
            poll(); // refresh the plant immediately so the injected problem is visible
        } catch { setInjectRes({ accepted: false, reason: "backend unreachable" }); }
        finally { setInjecting(false); }
    };

    const resetPlant = async () => {
        setResetting(true); setInjectRes(null);
        try {
            await fetch(`${API_BASE}/api/simulation/reset-world`, { method: "POST" });
            await poll();
        } catch { /* stays on real state */ }
        finally { setResetting(false); }
    };

    const doAsk = async () => {
        setAsking(true); setAsk(null);
        try {
            const r = await fetch(`${API_BASE}/factory/ask`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question }),
            });
            setAsk(await r.json());
        } catch { setAsk({ grounded: false, answer: "Backend unreachable — no fabricated answer.", citations: [] }); }
        finally { setAsking(false); }
    };

    const stages = snap?.stages ?? [];
    const troubled = stages.filter((s) => !["nominal", "running"].includes(s.status?.toLowerCase()));

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white">
            <Navigation />
            <main className="p-4 max-w-[1800px] mx-auto">
                {/* header */}
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2"><Cpu className="w-6 h-6 text-cyan-400" />Factory Intelligence — Live</h1>
                        <p className="text-sm text-[#8892a4]">Real plant state from the SimWorld digital twin · inject a real problem · ask the factory why. Nothing here is mocked.</p>
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                        <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border ${online ? "border-green-500/40 bg-green-500/10" : online === false ? "border-red-500/40 bg-red-500/10" : "border-gray-600/40 bg-gray-500/10"}`}>
                            <span className={`w-2 h-2 rounded-full ${online ? "bg-green-400 animate-pulse" : online === false ? "bg-red-500" : "bg-gray-500"}`} />
                            {online ? "LIVE — backend connected" : online === false ? "backend offline" : "connecting…"}
                        </span>
                        {snap && <span className="text-[#8892a4]">sim&nbsp;t = {Math.round(snap.sim_time_seconds).toLocaleString()}s</span>}
                    </div>
                </div>

                {online === false && (
                    <div className="glass p-4 mb-4 border border-red-500/30 text-sm text-red-300">
                        The backend at <span className="font-mono">{API_BASE}</span> is unreachable. Start it
                        (<span className="font-mono">uvicorn main:app --port 8000</span>) — this page shows only real data, so it stays empty rather than fake anything.
                    </div>
                )}

                <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                    {/* ---- LIVE PLANT (real snapshot) ---- */}
                    <section className="xl:col-span-2 glass p-4">
                        <div className="flex items-center justify-between mb-2">
                            <h2 className="font-semibold flex items-center gap-2"><Activity className="w-4 h-4 text-cyan-400" />Live production line <span className="text-xs text-[#8892a4]">(GET /api/simulation/snapshot)</span></h2>
                            {troubled.length > 0 && <span className="text-xs px-2 py-1 rounded bg-red-500/15 text-red-300 border border-red-500/30">{troubled.length} stage(s) not nominal</span>}
                        </div>
                        {/* legend — what the colours mean */}
                        <div className="flex flex-wrap gap-3 text-xs text-[#8892a4] mb-3">
                            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-green-400" />running</span>
                            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-yellow-400" />degraded / warning</span>
                            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-red-500" />broken / down</span>
                            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-blue-400" />under maintenance</span>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            {stages.length === 0 && <div className="text-sm text-[#8892a4] col-span-3">Waiting for live plant state…</div>}
                            {stages.map((s) => {
                                const st = styleFor(s.status);
                                return (
                                    <div key={s.stage_id} className={`bg-[#0d1220] rounded-lg p-3 border ${st.ring}`}>
                                        <div className="flex items-center justify-between">
                                            <span className="font-semibold capitalize text-sm">{s.name}</span>
                                            <span className={`w-2.5 h-2.5 rounded-full ${st.dot}`} />
                                        </div>
                                        <div className="text-[11px] text-[#8892a4] capitalize mb-2">{st.label}</div>
                                        <div className="grid grid-cols-3 gap-1 text-center">
                                            <div><div className="text-sm font-bold">{s.queue_depth}</div><div className="text-[9px] text-[#6b7280]">queue</div></div>
                                            <div><div className="text-sm font-bold">{(s.defect_rate_effective * 100).toFixed(1)}%</div><div className="text-[9px] text-[#6b7280]">defect</div></div>
                                            <div><div className="text-sm font-bold">{s.breakdown_count}</div><div className="text-[9px] text-[#6b7280]">breakdowns</div></div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                        {/* real plant metrics */}
                        <div className="grid grid-cols-4 gap-3 mt-4">
                            <Metric icon={<Boxes className="w-4 h-4" />} label="throughput/hr" value={snap?.throughput_units_per_hour != null ? Math.round(snap.throughput_units_per_hour) : "—"} />
                            <Metric icon={<Cpu className="w-4 h-4" />} label="AMR utilisation" value={snap?.amr_utilization != null ? `${Math.round((snap.amr_utilization) * (snap.amr_utilization <= 1 ? 100 : 1))}%` : "—"} />
                            <Metric icon={<Truck className="w-4 h-4" />} label="orders complete" value={snap?.orders_complete ?? "—"} />
                            <Metric icon={<AlertTriangle className="w-4 h-4" />} label="incidents fired" value={snap?.incidents_fired_count ?? "—"} />
                        </div>
                    </section>

                    {/* ---- INJECT + REASONING (real ops) ---- */}
                    <section className="space-y-4">
                        {/* inject a real problem */}
                        <div className="glass p-4">
                            <h2 className="font-semibold flex items-center gap-2 mb-1"><Zap className="w-4 h-4 text-yellow-400" />Inject a real problem</h2>
                            <p className="text-xs text-[#8892a4] mb-3">A plain-English report is parsed by the backend LLM into a validated incident and driven through the self-healing loop (POST /factory/inject). Watch the line react on the left.</p>
                            <select value={scenario} onChange={(e) => setScenario(e.target.value)}
                                    className="w-full bg-[#0d1220] border border-[#2a3346] rounded-lg px-3 py-2 text-sm mb-1">
                                {SCENARIOS.map((s) => <option key={s.label} value={s.report}>{s.label}</option>)}
                            </select>
                            <div className="text-[11px] text-[#6b7280] mb-3 italic">“{scenario}”</div>
                            <div className="flex gap-2">
                                <button onClick={inject} disabled={injecting || resetting || online === false}
                                        className="flex-1 bg-yellow-500/90 hover:bg-yellow-500 text-black font-semibold rounded-lg py-2 text-sm disabled:opacity-40">
                                    {injecting ? "Injecting + running loop…" : "Inject → run self-healing"}
                                </button>
                                <button onClick={resetPlant} disabled={resetting || injecting || online === false}
                                        title="Re-initialise the SimWorld to a fresh nominal state"
                                        className="px-3 bg-[#1c2333] hover:bg-[#252d40] border border-[#2a3346] rounded-lg py-2 text-sm disabled:opacity-40">
                                    {resetting ? "Resetting…" : "↻ Reset plant"}
                                </button>
                            </div>
                            {injectRes && (
                                <div className="mt-3 text-sm">
                                    {injectRes.accepted && injectRes.incident ? (
                                        <div className="bg-[#0d1220] rounded-lg p-3 border border-cyan-500/30">
                                            <div className="text-xs text-[#8892a4] mb-1">Diagnosed by the backend ({injectRes.method}):</div>
                                            <div className="flex flex-wrap gap-2 text-xs">
                                                <span className="px-2 py-1 rounded bg-red-500/15 text-red-300 border border-red-500/30">{injectRes.incident.type}</span>
                                                <span className="px-2 py-1 rounded bg-[#1c2333]">target: stage {injectRes.incident.target_id ?? "—"}</span>
                                                <span className="px-2 py-1 rounded bg-[#1c2333] capitalize">{injectRes.incident.severity}</span>
                                                <span className="px-2 py-1 rounded bg-[#1c2333]">conf {(injectRes.incident.confidence * 100).toFixed(0)}%</span>
                                            </div>
                                            {injectRes.loop && <div className="text-[11px] text-[#6b7280] mt-2">self-healing loop ran on <span className="font-mono">{injectRes.loop.backend}</span> · {(injectRes.loop.decisions?.length ?? 0)} decision(s){injectRes.loop.audit_seqs?.length ? ` · audit rows ${injectRes.loop.audit_seqs.join(", ")}` : ""}</div>}
                                        </div>
                                    ) : (
                                        <div className="bg-[#0d1220] rounded-lg p-3 border border-gray-600/40 text-[#8892a4] text-xs">Not accepted / abstained: {injectRes.reason ?? "the parser found no actionable incident (honest abstain)."}</div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* ask the factory (real grounded reasoning) */}
                        <div className="glass p-4">
                            <h2 className="font-semibold flex items-center gap-2 mb-1"><Brain className="w-4 h-4 text-purple-400" />Ask the factory — why?</h2>
                            <p className="text-xs text-[#8892a4] mb-3">Grounded in real evidence only (POST /factory/ask). If nothing grounds the question it says so honestly — it never invents.</p>
                            <div className="flex gap-2">
                                <input value={question} onChange={(e) => setQuestion(e.target.value)}
                                       onKeyDown={(e) => e.key === "Enter" && doAsk()}
                                       className="flex-1 bg-[#0d1220] border border-[#2a3346] rounded-lg px-3 py-2 text-sm" />
                                <button onClick={doAsk} disabled={asking || online === false}
                                        className="px-3 bg-purple-500/90 hover:bg-purple-500 rounded-lg disabled:opacity-40" aria-label="ask"><Send className="w-4 h-4" /></button>
                            </div>
                            {asking && <div className="text-xs text-[#8892a4] mt-3">Gathering evidence…</div>}
                            {ask && (
                                <div className="mt-3 bg-[#0d1220] rounded-lg p-3 border border-purple-500/20">
                                    <div className={`text-xs mb-1 ${ask.grounded ? "text-green-400" : "text-yellow-400"}`}>{ask.grounded ? "● grounded in evidence" : "○ no evidence (honest-empty)"}</div>
                                    <p className="text-sm text-[#dbe2ea]">{ask.answer}</p>
                                    {ask.citations?.length > 0 && (
                                        <div className="flex flex-wrap gap-1 mt-2">
                                            {ask.citations.map((c, i) => <span key={i} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1c2333] text-cyan-400">{c}</span>)}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </section>
                </div>

                {/* real incident feed — the actual incidents fired inside the SimWorld twin */}
                <section className="glass p-4 mt-4">
                    <h2 className="font-semibold flex items-center gap-2 mb-3"><AlertTriangle className="w-4 h-4 text-yellow-400" />Recent incidents <span className="text-xs text-[#8892a4]">(real SimWorld incidents, from /api/simulation/snapshot)</span></h2>
                    <div className="space-y-2">
                        {(snap?.recent_incidents?.length ?? 0) === 0 && <div className="text-sm text-[#8892a4]">No incidents fired yet — inject one above.</div>}
                        {snap?.recent_incidents?.slice().reverse().map((e, i) => (
                            <div key={i} className={`text-xs p-2 rounded border-l-2 ${e.severity === "critical" ? "bg-red-500/10 border-red-500" : e.severity === "warning" ? "bg-yellow-500/10 border-yellow-500" : "bg-green-500/10 border-green-500"}`}>
                                <span className="capitalize font-medium">{e.type?.replace(/_/g, " ")}</span>
                                {e.target_id != null && <span className="text-[#8892a4]"> · stage {e.target_id}</span>}
                                <span className="text-[#8892a4] capitalize"> · {e.severity}</span>
                            </div>
                        ))}
                    </div>
                </section>

                <p className="text-xs text-[#6b7280] mt-4">
                    Every panel is a real backend call — SimWorld snapshot, LLM-parsed injection through the safety-gated
                    self-healing loop, and grounded reasoning. No page-side animation, no random numbers, no mock state.
                </p>
            </main>
        </div>
    );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
    return (
        <div className="bg-[#0d1220] rounded-lg p-3 text-center">
            <div className="flex items-center justify-center text-cyan-400 mb-1">{icon}</div>
            <div className="text-lg font-bold">{value}</div>
            <div className="text-[10px] text-[#6b7280]">{label}</div>
        </div>
    );
}
