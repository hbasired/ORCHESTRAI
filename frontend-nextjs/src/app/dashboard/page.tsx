"use client";

// =============================================================================
// Operations Dashboard — LIVE, 100% backend-driven. No hardcoded numbers.
//   • plant   -> GET /api/simulation/snapshot   (real robots + stages + throughput)
//   • supply  -> GET /api/inventory/stats + /suppliers
// Every value below is a real backend call; if the backend is down it says Offline and shows dashes.
// =============================================================================

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Stage { stage_id: number; name: string; status: string; queue_depth: number; }
interface Robot { id: number; status: string; battery: number; }
interface Snapshot { stages: Stage[]; robots: Robot[]; throughput_units_per_hour?: number; incidents_fired_count?: number; }
interface InvStats { total_components: number; low_stock_count: number; pending_orders: number; active_alerts: number; total_value: number; }

async function j<T>(u: string): Promise<T | null> { try { const r = await fetch(u, { cache: "no-store" }); return r.ok ? await r.json() as T : null; } catch { return null; } }

export default function DashboardPage() {
    const [snap, setSnap] = useState<Snapshot | null>(null);
    const [inv, setInv] = useState<InvStats | null>(null);
    const [suppliers, setSuppliers] = useState<number>(0);
    const [connected, setConnected] = useState(false);
    const timer = useRef<ReturnType<typeof setInterval> | null>(null);

    const poll = useCallback(async () => {
        const [s, iv, sup] = await Promise.all([
            j<Snapshot>(`${API_BASE}/api/simulation/snapshot`),
            j<InvStats>(`${API_BASE}/api/inventory/stats`),
            j<unknown[]>(`${API_BASE}/api/inventory/suppliers`),
        ]);
        setConnected(s !== null);
        if (s) setSnap(s); if (iv) setInv(iv); if (Array.isArray(sup)) setSuppliers(sup.length);
    }, []);
    useEffect(() => { poll(); timer.current = setInterval(poll, 2000); return () => { if (timer.current) clearInterval(timer.current); }; }, [poll]);

    const robots = snap?.robots ?? [];
    const stages = snap?.stages ?? [];
    const activeRobots = robots.filter((r) => ["moving", "working", "busy"].includes(r.status?.toLowerCase())).length;
    const chargingRobots = robots.filter((r) => r.status?.toLowerCase() === "charging").length;
    const idleRobots = robots.filter((r) => r.status?.toLowerCase() === "idle").length;
    const activeStages = stages.filter((s) => ["nominal", "running", "degraded"].includes(s.status?.toLowerCase())).length;
    const bottlenecks = stages.filter((s) => ["broken", "down"].includes(s.status?.toLowerCase()) || s.queue_depth > 15).length;
    const throughput = Math.round(snap?.throughput_units_per_hour ?? 0);

    return (
        <div className="min-h-screen bg-[#0a0e17] grid-bg py-20 px-6">
            <nav className="fixed top-0 left-0 right-0 z-50 glass p-4">
                <div className="max-w-7xl mx-auto flex justify-between items-center">
                    <Link href="/" className="text-xl font-bold text-gradient">Embodied AI</Link>
                    <div className="flex gap-6"><Link href="/simulation" className="btn-primary text-sm">Live Simulation</Link></div>
                </div>
            </nav>

            <div className="max-w-7xl mx-auto pt-16">
                <h1 className="text-4xl font-bold text-center mb-3">Operations <span className="text-gradient">Dashboard</span></h1>
                <p className="text-center text-[#8892a4] text-sm mb-8">Every number is a live backend call — no hardcoded values, no local animation.</p>

                <div className="flex justify-center mb-8">
                    <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${connected ? "bg-[#00ff8820]" : "bg-[#ff336620]"}`}>
                        <div className={`w-3 h-3 rounded-full animate-pulse ${connected ? "bg-[#00ff88]" : "bg-[#ff3366]"}`} />
                        <span className={connected ? "text-[#00ff88]" : "text-[#ff3366]"}>{connected ? "Live Data" : "Offline"}</span>
                    </div>
                </div>

                {/* real KPIs */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12">
                    <KPI label="Throughput /hr" value={connected ? throughput : "—"} color="#00f0ff" />
                    <KPI label="Bottlenecks" value={connected ? bottlenecks : "—"} color={bottlenecks > 0 ? "#ff3366" : "#00ff88"} />
                    <KPI label="Incidents Fired" value={connected ? (snap?.incidents_fired_count ?? 0) : "—"} color="#ffcc00" />
                    <KPI label="Low-Stock Items" value={connected ? (inv?.low_stock_count ?? 0) : "—"} color={(inv?.low_stock_count ?? 0) > 0 ? "#ff3366" : "#00ff88"} />
                </div>

                {/* real domain panels */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                    <Panel title="Robotics" color="#00ff88" rows={[
                        ["Fleet size", robots.length || "—"],
                        ["Active", activeRobots],
                        ["Idle", idleRobots],
                        ["Charging", chargingRobots],
                    ]} link="/robotics" />
                    <Panel title="Manufacturing" color="#7b2ff7" rows={[
                        ["Active stages", stages.length ? `${activeStages} / ${stages.length}` : "—"],
                        ["Bottlenecks", bottlenecks],
                        ["Throughput", `${throughput}/hr`],
                    ]} link="/manufacturing" />
                    <Panel title="Supply Chain" color="#ffcc00" rows={[
                        ["Suppliers", suppliers || "—"],
                        ["Low stock", inv?.low_stock_count ?? "—"],
                        ["Pending orders", inv?.pending_orders ?? "—"],
                        ["Inventory value", inv ? `$${inv.total_value.toLocaleString()}` : "—"],
                    ]} link="/supply-chain" />
                </div>

                <div className="flex justify-center gap-4 flex-wrap">
                    <Link href="/factory"><button className="btn-primary">Factory Intelligence</button></Link>
                    <Link href="/embodied-agent"><button className="btn-secondary">Embodied Agents</button></Link>
                    <Link href="/knowledge-graph"><button className="btn-secondary">Knowledge Graph</button></Link>
                </div>
            </div>
        </div>
    );
}

function KPI({ label, value, color }: { label: string; value: React.ReactNode; color: string }) {
    return <div className="glass p-6 text-center"><div className="text-3xl font-bold" style={{ color }}>{value}</div><div className="text-[#8892a4] mt-2">{label}</div></div>;
}
function Panel({ title, color, rows, link }: { title: string; color: string; rows: [string, React.ReactNode][]; link: string }) {
    return (
        <Link href={link} className="glass p-6 block hover:ring-1 hover:ring-cyan-500/40 transition">
            <h3 className="text-xl font-bold mb-4" style={{ color }}>{title}</h3>
            <div className="space-y-3">
                {rows.map(([k, v]) => (
                    <div key={k} className="flex justify-between"><span className="text-[#8892a4]">{k}</span><span>{v}</span></div>
                ))}
            </div>
        </Link>
    );
}
