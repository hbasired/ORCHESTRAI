"use client";

// =============================================================================
// Robotics — LIVE, 100% backend-driven. No mock data, no local animation.
//   • robot fleet -> GET  /api/simulation/snapshot   (real SimWorld robots: battery, status, tasks)
//   • reset       -> POST /api/simulation/reset-world
// =============================================================================

import { useCallback, useEffect, useRef, useState } from "react";
import Navigation from "@/components/Navigation";
import { Bot, BatteryCharging, Activity, Cpu } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Robot { id: number; battery: number; status: string; queue_len: number; completed_tasks: number; charge_cycles: number; }
interface Snapshot { sim_time_seconds: number; robots: Robot[]; amr_utilization?: number; }

const ROBOT_STATUS: Record<string, { dot: string; text: string }> = {
    idle:     { dot: "bg-gray-400",   text: "text-gray-300" },
    moving:   { dot: "bg-green-400",  text: "text-green-400" },
    working:  { dot: "bg-green-400",  text: "text-green-400" },
    busy:     { dot: "bg-green-400",  text: "text-green-400" },
    charging: { dot: "bg-blue-400",   text: "text-blue-400" },
    broken:   { dot: "bg-red-500",    text: "text-red-400" },
    down:     { dot: "bg-red-500",    text: "text-red-400" },
};
const rstat = (s: string) => ROBOT_STATUS[s?.toLowerCase()] ?? { dot: "bg-gray-500", text: "text-gray-400" };
const battColor = (b: number) => b < 0.2 ? "bg-red-500" : b < 0.5 ? "bg-yellow-400" : "bg-green-400";

export default function RoboticsPage() {
    const [snap, setSnap] = useState<Snapshot | null>(null);
    const [online, setOnline] = useState<boolean | null>(null);
    const [resetting, setResetting] = useState(false);
    const timer = useRef<ReturnType<typeof setInterval> | null>(null);

    const poll = useCallback(async () => {
        try { const r = await fetch(`${API_BASE}/api/simulation/snapshot`, { cache: "no-store" }); if (!r.ok) throw new Error(); setSnap(await r.json()); setOnline(true); }
        catch { setOnline(false); }
    }, []);
    useEffect(() => { poll(); timer.current = setInterval(poll, 1500); return () => { if (timer.current) clearInterval(timer.current); }; }, [poll]);
    const reset = async () => { setResetting(true); try { await fetch(`${API_BASE}/api/simulation/reset-world`, { method: "POST" }); await poll(); } catch {} finally { setResetting(false); } };

    const robots = (snap?.robots ?? []).slice().sort((a, b) => a.id - b.id);
    const active = robots.filter((r) => ["moving", "working", "busy"].includes(r.status?.toLowerCase())).length;
    const charging = robots.filter((r) => r.status?.toLowerCase() === "charging").length;
    const idle = robots.filter((r) => r.status?.toLowerCase() === "idle").length;
    const down = robots.filter((r) => ["broken", "down"].includes(r.status?.toLowerCase())).length;
    const avgBatt = robots.length ? robots.reduce((a, r) => a + r.battery, 0) / robots.length : 0;
    const totalTasks = robots.reduce((a, r) => a + r.completed_tasks, 0);

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white">
            <Navigation />
            <main className="p-4 max-w-[1800px] mx-auto">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2"><Bot className="w-6 h-6 text-cyan-400" />Robotics Fleet — Live</h1>
                        <p className="text-sm text-[#8892a4]">The real AMR fleet from the SimWorld twin — battery, status and completed tasks per robot. Nothing mocked.</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <button onClick={reset} disabled={resetting || online === false} className="px-3 py-1.5 text-sm bg-[#1c2333] hover:bg-[#252d40] border border-[#2a3346] rounded-lg disabled:opacity-40">{resetting ? "Resetting…" : "↻ Reset fleet"}</button>
                        <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm ${online ? "border-green-500/40 bg-green-500/10" : "border-red-500/40 bg-red-500/10"}`}>
                            <span className={`w-2 h-2 rounded-full ${online ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />{online ? "LIVE" : "offline"}
                        </span>
                    </div>
                </div>

                {/* fleet summary (real) */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
                    <Stat icon={<Bot className="w-4 h-4" />} label="fleet size" value={robots.length || "—"} />
                    <Stat icon={<Activity className="w-4 h-4" />} label="active" value={active} tone="text-green-400" />
                    <Stat icon={<Cpu className="w-4 h-4" />} label="idle" value={idle} />
                    <Stat icon={<BatteryCharging className="w-4 h-4" />} label="charging" value={charging} tone="text-blue-400" />
                    <Stat icon={<Bot className="w-4 h-4" />} label="avg battery" value={robots.length ? `${Math.round(avgBatt * 100)}%` : "—"} />
                </div>

                {/* reasoning */}
                <div className="glass p-3 mb-4 text-xs text-[#8892a4] flex flex-wrap items-center gap-4">
                    <span className="font-semibold text-white">How to read this:</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-green-400" />active — moving/working a task</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-gray-400" />idle — available for assignment</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-blue-400" />charging — battery low, at a dock</span>
                    {down > 0 && <span className="flex items-center gap-1.5 text-red-400"><span className="w-2.5 h-2.5 rounded-full bg-red-500" />{down} down</span>}
                    <span className="ml-auto">total completed tasks: <b className="text-white">{totalTasks.toLocaleString()}</b></span>
                </div>

                {/* the real fleet grid */}
                <section className="glass p-4">
                    <h2 className="font-semibold flex items-center gap-2 mb-3"><Bot className="w-4 h-4 text-cyan-400" />Fleet <span className="text-xs text-[#8892a4]">(GET /api/simulation/snapshot → robots)</span></h2>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                        {robots.length === 0 && <div className="text-sm text-[#8892a4]">Waiting for live fleet…</div>}
                        {robots.map((r) => {
                            const st = rstat(r.status);
                            return (
                                <div key={r.id} className="bg-[#0d1220] rounded-lg p-3">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-sm font-semibold">AMR {r.id}</span>
                                        <span className={`flex items-center gap-1 text-[11px] ${st.text}`}><span className={`w-2 h-2 rounded-full ${st.dot}`} />{r.status}</span>
                                    </div>
                                    <div className="h-2 bg-[#1c2333] rounded overflow-hidden mb-1"><div className={`h-full ${battColor(r.battery)}`} style={{ width: `${Math.round(r.battery * 100)}%` }} /></div>
                                    <div className="flex justify-between text-[10px] text-[#6b7280]">
                                        <span>{Math.round(r.battery * 100)}% batt</span>
                                        <span>{r.completed_tasks} tasks</span>
                                    </div>
                                    {r.charge_cycles > 0 && <div className="text-[10px] text-[#6b7280] mt-0.5">{r.charge_cycles} charge cycles</div>}
                                </div>
                            );
                        })}
                    </div>
                </section>

                {online === false && <div className="glass p-4 mt-4 border border-red-500/30 text-sm text-red-300">Backend at <span className="font-mono">{API_BASE}</span> unreachable — real data only, nothing faked.</div>}
                <p className="text-xs text-[#6b7280] mt-4">Every robot&apos;s battery, status and task count is live from the SimWorld twin — no random motion, no local animation. Robots charge when their battery runs low and take new tasks when idle.</p>
            </main>
        </div>
    );
}

function Stat({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: React.ReactNode; tone?: string }) {
    return <div className="glass p-3 text-center"><div className="flex items-center justify-center text-cyan-400 mb-1">{icon}</div><div className={`text-xl font-bold ${tone ?? ""}`}>{value}</div><div className="text-[10px] text-[#6b7280]">{label}</div></div>;
}
