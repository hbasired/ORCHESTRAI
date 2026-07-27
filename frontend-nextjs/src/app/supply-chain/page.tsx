"use client";

// =============================================================================
// Supply Chain — LIVE, 100% backend-driven. No mock data.
//   • inventory   -> GET  /api/inventory/components
//   • suppliers   -> GET  /api/inventory/suppliers
//   • stats       -> GET  /api/inventory/stats
//   • JIT plan    -> GET  /api/inventory/jit/recommendations   (the real optimiser reasoning)
//   • solve       -> POST /api/inventory/jit/auto-order        (real action: places the recommended orders)
// =============================================================================

import { useCallback, useEffect, useRef, useState } from "react";
import Navigation from "@/components/Navigation";
import { Truck, Package, AlertTriangle, TrendingDown, CheckCircle, Boxes, DollarSign } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const INV = `${API_BASE}/api/inventory`;

interface Stats { total_components: number; low_stock_count: number; total_value: number; pending_orders: number; pending_order_value: number; active_alerts: number; }
interface Component { id: string; part_number: string; name: string; category: string; quantity: number; reorder_point: number; max_capacity: number; unit_cost: number; consumption_rate: number; lead_time_hours: number; supplier_id: string; stock_level_pct: number; is_low_stock: boolean; }
interface Supplier { id: string; name: string; reliability_score: number; avg_lead_time_hours: number; min_order_quantity: number; status: string; }
interface JITRec { component_id: string; component_name: string; current_qty: number; order_qty: number; runway_hours: number; lead_time: number; estimated_cost: number; priority: string; }
interface JIT { orders_to_place: JITRec[]; orders_to_expedite: unknown[]; components_ok: string[]; total_cost: number; }

async function getJSON<T>(url: string): Promise<T | null> {
    try { const r = await fetch(url, { cache: "no-store" }); return r.ok ? (await r.json() as T) : null; } catch { return null; }
}

export default function SupplyChainPage() {
    const [stats, setStats] = useState<Stats | null>(null);
    const [components, setComponents] = useState<Component[]>([]);
    const [suppliers, setSuppliers] = useState<Supplier[]>([]);
    const [jit, setJit] = useState<JIT | null>(null);
    const [online, setOnline] = useState<boolean | null>(null);
    const [placing, setPlacing] = useState(false);
    const [placed, setPlaced] = useState<string | null>(null);
    const timer = useRef<ReturnType<typeof setInterval> | null>(null);

    const poll = useCallback(async () => {
        const [s, c, sup, j] = await Promise.all([
            getJSON<Stats>(`${INV}/stats`), getJSON<Component[]>(`${INV}/components`),
            getJSON<Supplier[]>(`${INV}/suppliers`), getJSON<JIT>(`${INV}/jit/recommendations`),
        ]);
        setOnline(s !== null);
        if (s) setStats(s); if (c) setComponents(c); if (sup) setSuppliers(sup); if (j) setJit(j);
    }, []);

    useEffect(() => { poll(); timer.current = setInterval(poll, 3000); return () => { if (timer.current) clearInterval(timer.current); }; }, [poll]);

    const autoOrder = async () => {
        setPlacing(true); setPlaced(null);
        try {
            const r = await fetch(`${INV}/jit/auto-order`, { method: "POST" });
            const d = await r.json();
            setPlaced(`Placed ${d.orders_created?.length ?? d.orders?.length ?? "the recommended"} purchase order(s).`);
            await poll();
        } catch { setPlaced("Backend unreachable — nothing placed."); }
        finally { setPlacing(false); }
    };

    const supplierName = (id: string) => suppliers.find((s) => s.id === id)?.name ?? id;
    const recs = jit?.orders_to_place ?? [];

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white">
            <Navigation />
            <main className="p-4 max-w-[1800px] mx-auto">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2"><Truck className="w-6 h-6 text-cyan-400" />Supply Chain — Live</h1>
                        <p className="text-sm text-[#8892a4]">Real inventory, suppliers and the JIT optimiser&apos;s live recommendations. Every value is a backend call — nothing mocked.</p>
                    </div>
                    <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm ${online ? "border-green-500/40 bg-green-500/10" : online === false ? "border-red-500/40 bg-red-500/10" : "border-gray-600/40"}`}>
                        <span className={`w-2 h-2 rounded-full ${online ? "bg-green-400 animate-pulse" : online === false ? "bg-red-500" : "bg-gray-500"}`} />
                        {online ? "LIVE" : online === false ? "backend offline" : "connecting…"}
                    </span>
                </div>

                {/* real stats */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
                    <Stat icon={<Boxes className="w-4 h-4" />} label="components" value={stats?.total_components ?? "—"} />
                    <Stat icon={<TrendingDown className="w-4 h-4" />} label="low stock" value={stats?.low_stock_count ?? "—"} warn={(stats?.low_stock_count ?? 0) > 0} />
                    <Stat icon={<DollarSign className="w-4 h-4" />} label="inventory value" value={stats ? `$${stats.total_value.toLocaleString()}` : "—"} />
                    <Stat icon={<Package className="w-4 h-4" />} label="pending orders" value={stats?.pending_orders ?? "—"} />
                    <Stat icon={<AlertTriangle className="w-4 h-4" />} label="active alerts" value={stats?.active_alerts ?? "—"} warn={(stats?.active_alerts ?? 0) > 0} />
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                    {/* inventory */}
                    <section className="xl:col-span-2 glass p-4">
                        <h2 className="font-semibold flex items-center gap-2 mb-3"><Package className="w-4 h-4 text-cyan-400" />Inventory <span className="text-xs text-[#8892a4]">(GET /api/inventory/components)</span></h2>
                        <div className="space-y-2">
                            {components.length === 0 && <div className="text-sm text-[#8892a4]">Loading real inventory…</div>}
                            {components.map((c) => {
                                const pct = c.stock_level_pct;
                                const runway = c.consumption_rate > 0 ? (c.quantity / c.consumption_rate) : Infinity; // hours of stock left
                                const barColor = c.is_low_stock ? "bg-red-500" : pct < 40 ? "bg-yellow-400" : "bg-green-400";
                                return (
                                    <div key={c.id} className="bg-[#0d1220] rounded-lg p-3">
                                        <div className="flex items-center justify-between text-sm mb-1">
                                            <span className="font-medium">{c.name} <span className="text-[#6b7280] font-mono text-xs">{c.part_number}</span></span>
                                            <span className={c.is_low_stock ? "text-red-400" : "text-[#8892a4]"}>{c.quantity.toLocaleString()} / {c.max_capacity.toLocaleString()}</span>
                                        </div>
                                        <div className="h-2 bg-[#1c2333] rounded overflow-hidden mb-1"><div className={`h-full ${barColor}`} style={{ width: `${Math.min(100, pct)}%` }} /></div>
                                        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-[#6b7280]">
                                            <span>reorder @ {c.reorder_point.toLocaleString()}</span>
                                            <span>uses {c.consumption_rate}/hr → ~{Number.isFinite(runway) ? Math.round(runway) : "∞"}h runway</span>
                                            <span>lead {c.lead_time_hours}h</span>
                                            <span>{supplierName(c.supplier_id)}</span>
                                            {c.is_low_stock && <span className="text-red-400 font-semibold">LOW STOCK</span>}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </section>

                    {/* suppliers + JIT reasoning + solve */}
                    <section className="space-y-4">
                        <div className="glass p-4">
                            <h2 className="font-semibold flex items-center gap-2 mb-3"><Truck className="w-4 h-4 text-purple-400" />Suppliers</h2>
                            <div className="space-y-2">
                                {suppliers.map((s) => (
                                    <div key={s.id} className="bg-[#0d1220] rounded-lg p-2.5 flex items-center justify-between text-sm">
                                        <div>
                                            <div className="font-medium">{s.name}</div>
                                            <div className="text-[11px] text-[#6b7280]">lead {s.avg_lead_time_hours}h · MOQ {s.min_order_quantity.toLocaleString()}</div>
                                        </div>
                                        <div className="text-right">
                                            <div className={`font-bold ${s.reliability_score >= 90 ? "text-green-400" : s.reliability_score >= 70 ? "text-yellow-400" : "text-red-400"}`}>{s.reliability_score}%</div>
                                            <div className="text-[11px] text-[#6b7280] capitalize">{s.status}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* the reasoning: JIT optimiser */}
                        <div className="glass p-4 border border-cyan-500/20">
                            <h2 className="font-semibold flex items-center gap-2 mb-1"><AlertTriangle className="w-4 h-4 text-yellow-400" />JIT optimiser — what &amp; why</h2>
                            <p className="text-xs text-[#8892a4] mb-3">The backend recommends an order when a component&apos;s <b>runway</b> (stock ÷ consumption) approaches its <b>lead time</b> — order now or risk a stockout. (GET /api/inventory/jit/recommendations)</p>
                            {recs.length === 0 ? (
                                <div className="text-sm text-green-400 flex items-center gap-2"><CheckCircle className="w-4 h-4" />All components have healthy runway — no orders needed.</div>
                            ) : (
                                <div className="space-y-2">
                                    {recs.map((r) => (
                                        <div key={r.component_id} className="bg-[#0d1220] rounded-lg p-2.5 text-xs">
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="font-medium">{r.component_name}</span>
                                                <span className={`px-1.5 py-0.5 rounded capitalize ${r.priority === "urgent" || r.priority === "rush" ? "bg-red-500/15 text-red-300" : "bg-yellow-500/15 text-yellow-300"}`}>{r.priority}</span>
                                            </div>
                                            <div className="text-[#8892a4]">order <b className="text-white">{r.order_qty.toLocaleString()}</b> · runway <b className={r.runway_hours < r.lead_time ? "text-red-400" : "text-white"}>{Math.round(r.runway_hours)}h</b> vs lead {r.lead_time}h · ~${r.estimated_cost.toLocaleString()}</div>
                                        </div>
                                    ))}
                                    <div className="text-xs text-[#8892a4] pt-1">Total: <b className="text-white">${jit?.total_cost.toLocaleString()}</b> across {recs.length} order(s).</div>
                                    <button onClick={autoOrder} disabled={placing || online === false}
                                            className="w-full mt-2 bg-cyan-500/90 hover:bg-cyan-500 text-black font-semibold rounded-lg py-2 text-sm disabled:opacity-40">
                                        {placing ? "Placing orders…" : "Solve → auto-place recommended orders"}
                                    </button>
                                </div>
                            )}
                            {placed && <div className="text-xs text-green-400 mt-2 flex items-center gap-1"><CheckCircle className="w-3.5 h-3.5" />{placed}</div>}
                        </div>
                    </section>
                </div>

                {online === false && (
                    <div className="glass p-4 mt-4 border border-red-500/30 text-sm text-red-300">
                        Backend at <span className="font-mono">{API_BASE}</span> unreachable — this page shows only real data, so it stays empty rather than fake anything.
                    </div>
                )}
                <p className="text-xs text-[#6b7280] mt-4">The problem (a component draining toward a stockout) and the solution (the JIT optimiser&apos;s order plan, executed by the auto-order action) are both real backend operations — no random values, no local animation.</p>
            </main>
        </div>
    );
}

function Stat({ icon, label, value, warn }: { icon: React.ReactNode; label: string; value: React.ReactNode; warn?: boolean }) {
    return (
        <div className={`glass p-3 text-center ${warn ? "border border-red-500/30" : ""}`}>
            <div className={`flex items-center justify-center mb-1 ${warn ? "text-red-400" : "text-cyan-400"}`}>{icon}</div>
            <div className="text-xl font-bold">{value}</div>
            <div className="text-[10px] text-[#6b7280]">{label}</div>
        </div>
    );
}
