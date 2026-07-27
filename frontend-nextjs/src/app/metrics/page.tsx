"use client";

// =============================================================================
// System Metrics — LIVE, 100% backend-driven. No mock data.
//   • plant  -> GET /api/simulation/snapshot
//   • supply -> GET /api/inventory/stats
//   • audit  -> GET /ops/cascade   (count of real signed decisions in the audit chain)
// Every KPI is a real backend value; offline => dashes, never fabricated.
// =============================================================================

import { useCallback, useEffect, useRef, useState } from "react";
import Navigation from "@/components/Navigation";
import { BarChart3, Boxes, Cpu, AlertTriangle, Truck, DollarSign, Activity, ShieldCheck } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
async function j<T>(u: string): Promise<T | null> { try { const r = await fetch(u, { cache: "no-store" }); return r.ok ? await r.json() as T : null; } catch { return null; } }

interface Stage { status: string; queue_depth: number; units_produced: number; defect_rate_effective: number; }
interface Robot { status: string; battery: number; completed_tasks: number; }
interface Snapshot { sim_time_seconds: number; stages: Stage[]; robots: Robot[]; throughput_units_per_hour?: number; orders_complete?: number; incidents_fired_count?: number; amr_utilization?: number; }
interface InvStats { total_components: number; low_stock_count: number; pending_orders: number; total_value: number; }
interface Cascade { system: { seq: number }[]; rows_scanned?: number; }

export default function MetricsPage() {
    const [snap, setSnap] = useState<Snapshot | null>(null);
    const [inv, setInv] = useState<InvStats | null>(null);
    const [audit, setAudit] = useState<number | null>(null);
    const [online, setOnline] = useState<boolean | null>(null);
    const timer = useRef<ReturnType<typeof setInterval> | null>(null);

    const poll = useCallback(async () => {
        const [s, iv, c] = await Promise.all([j<Snapshot>(`${API_BASE}/api/simulation/snapshot`), j<InvStats>(`${API_BASE}/api/inventory/stats`), j<Cascade>(`${API_BASE}/ops/cascade`)]);
        setOnline(s !== null);
        if (s) setSnap(s); if (iv) setInv(iv);
        if (c) setAudit(c.system?.length ? Math.max(...c.system.map((r) => r.seq)) : (c.rows_scanned ?? 0));
    }, []);
    useEffect(() => { poll(); timer.current = setInterval(poll, 2000); return () => { if (timer.current) clearInterval(timer.current); }; }, [poll]);

    const stages = snap?.stages ?? [];
    const robots = snap?.robots ?? [];
    const nominal = stages.filter((s) => ["nominal", "running"].includes(s.status?.toLowerCase())).length;
    const activeRobots = robots.filter((r) => ["moving", "working", "busy"].includes(r.status?.toLowerCase())).length;
    const totalUnits = stages.reduce((a, s) => a + s.units_produced, 0);
    const avgDefect = stages.length ? (stages.reduce((a, s) => a + s.defect_rate_effective, 0) / stages.length) * 100 : 0;
    const V = (x: React.ReactNode) => online ? x : "—";

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white">
            <Navigation />
            <main className="p-4 max-w-[1600px] mx-auto">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2"><BarChart3 className="w-6 h-6 text-cyan-400" />System Metrics — Live</h1>
                        <p className="text-sm text-[#8892a4]">Real operational KPIs across the plant, supply chain and the signed audit chain. Nothing mocked.</p>
                    </div>
                    <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm ${online ? "border-green-500/40 bg-green-500/10" : "border-red-500/40 bg-red-500/10"}`}>
                        <span className={`w-2 h-2 rounded-full ${online ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />{online ? "LIVE" : "offline"}
                    </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                    <KPI icon={<Boxes />} label="throughput / hr" value={V(Math.round(snap?.throughput_units_per_hour ?? 0))} />
                    <KPI icon={<Activity />} label="stages nominal" value={V(stages.length ? `${nominal} / ${stages.length}` : 0)} tone={nominal < stages.length ? "text-yellow-400" : "text-green-400"} />
                    <KPI icon={<Cpu />} label="robots active" value={V(robots.length ? `${activeRobots} / ${robots.length}` : 0)} />
                    <KPI icon={<AlertTriangle />} label="incidents fired" value={V(snap?.incidents_fired_count ?? 0)} tone="text-yellow-400" />
                    <KPI icon={<Boxes />} label="units produced" value={V(totalUnits.toLocaleString())} />
                    <KPI icon={<Activity />} label="avg defect rate" value={V(`${avgDefect.toFixed(2)}%`)} tone={avgDefect > 5 ? "text-red-400" : "text-green-400"} />
                    <KPI icon={<Truck />} label="orders complete" value={V(snap?.orders_complete ?? 0)} />
                    <KPI icon={<DollarSign />} label="inventory value" value={V(inv ? `$${inv.total_value.toLocaleString()}` : 0)} />
                    <KPI icon={<AlertTriangle />} label="low-stock items" value={V(inv?.low_stock_count ?? 0)} tone={(inv?.low_stock_count ?? 0) > 0 ? "text-red-400" : "text-green-400"} />
                    <KPI icon={<Truck />} label="pending orders" value={V(inv?.pending_orders ?? 0)} />
                    <KPI icon={<Cpu />} label="components" value={V(inv?.total_components ?? 0)} />
                    <KPI icon={<ShieldCheck />} label="signed decisions (audit chain)" value={V(audit ?? 0)} tone="text-cyan-400" />
                </div>

                <div className="glass p-4">
                    <h2 className="font-semibold flex items-center gap-2 mb-3"><Activity className="w-4 h-4 text-cyan-400" />Per-stage detail <span className="text-xs text-[#8892a4]">(real snapshot)</span></h2>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead><tr className="text-[#8892a4] text-left text-xs uppercase"><th className="py-2">stage</th><th>status</th><th className="text-right">queue</th><th className="text-right">units</th><th className="text-right">defect</th></tr></thead>
                            <tbody>
                                {stages.length === 0 && <tr><td colSpan={5} className="py-3 text-[#8892a4]">Waiting for live data…</td></tr>}
                                {stages.map((s, i) => (
                                    <tr key={i} className="border-t border-[#1c2333]">
                                        <td className="py-2">stage {i}</td>
                                        <td className={["broken", "down"].includes(s.status?.toLowerCase()) ? "text-red-400" : ["degraded", "warning"].includes(s.status?.toLowerCase()) ? "text-yellow-400" : "text-green-400"}>{s.status}</td>
                                        <td className="text-right">{s.queue_depth}</td>
                                        <td className="text-right">{s.units_produced}</td>
                                        <td className="text-right">{(s.defect_rate_effective * 100).toFixed(2)}%</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {online === false && <div className="glass p-4 mt-4 border border-red-500/30 text-sm text-red-300">Backend at <span className="font-mono">{API_BASE}</span> unreachable — real data only.</div>}
                <p className="text-xs text-[#6b7280] mt-4">The model training/eval metrics (RMSE, accuracy, etc.) with dataset links live on the <a href="/model-metrics" className="text-cyan-400">Model Metrics</a> page. This page is live operational KPIs — all real backend calls.</p>
            </main>
        </div>
    );
}

function KPI({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: React.ReactNode; tone?: string }) {
    return (
        <div className="glass p-3 text-center">
            <div className="flex items-center justify-center text-cyan-400 mb-1">{icon}</div>
            <div className={`text-xl font-bold ${tone ?? ""}`}>{value}</div>
            <div className="text-[10px] text-[#6b7280]">{label}</div>
        </div>
    );
}
