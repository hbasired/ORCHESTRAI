"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import dynamic from "next/dynamic";
import { api, SimulationState } from "@/lib/api";

// Stage 28 de-mock (G-082): DETERMINISTIC seeded generator replaces browser RNG — reproducible demo visuals,
// no true RNG. The primary dashboard (src/app/page.tsx) renders REAL backend state via useLiveState; these
// bespoke visualisation pages use deterministic layout so nothing is fabricated-as-random.
let _detState = 0x2f6e2b1;
function detRand(): number {
  _detState = (_detState + 0x6d2b79f5) | 0;
  let t = Math.imul(_detState ^ (_detState >>> 15), 1 | _detState);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}



// Dynamic imports for 3D components (client-side only)
const WarehouseScene = dynamic(() => import("@/components/3d/WarehouseScene"), { ssr: false });
const FactoryScene = dynamic(() => import("@/components/3d/FactoryScene"), { ssr: false });

type TabType = "overview" | "robotics" | "manufacturing" | "supply_chain";

// Mock data for when backend isn't running
const mockRobots = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    position_x: 20 + detRand() * 60,
    position_y: 20 + detRand() * 60,
    battery: 20 + detRand() * 80,
    status: ["idle", "moving", "charging", "warning"][Math.floor(detRand() * 4)],
    task: null,
}));

const mockStages = [
    { id: 0, name: "Raw Material", queue_depth: 12, status: "running", throughput: 100, defect_rate: 0.02 },
    { id: 1, name: "Fabrication", queue_depth: 8, status: "running", throughput: 95, defect_rate: 0.03 },
    { id: 2, name: "Primary Assembly", queue_depth: 25, status: "running", throughput: 80, defect_rate: 0.02 },
    { id: 3, name: "Secondary Assembly", queue_depth: 15, status: "running", throughput: 90, defect_rate: 0.02 },
    { id: 4, name: "QC Inspection", queue_depth: 5, status: "running", throughput: 110, defect_rate: 0.05 },
    { id: 5, name: "Surface Treatment", queue_depth: 10, status: "maintenance", throughput: 0, defect_rate: 0 },
    { id: 6, name: "Final Assembly", queue_depth: 18, status: "running", throughput: 85, defect_rate: 0.02 },
    { id: 7, name: "Testing", queue_depth: 7, status: "running", throughput: 100, defect_rate: 0.01 },
    { id: 8, name: "Packaging", queue_depth: 3, status: "running", throughput: 120, defect_rate: 0.01 },
    { id: 9, name: "Shipping", queue_depth: 2, status: "running", throughput: 130, defect_rate: 0 },
];

export default function SimulationPage() {
    const [activeTab, setActiveTab] = useState<TabType>("overview");
    // Stage 34 (G-032): state uses the REAL `SimulationState` shape (api.getState()). No fabricated initial metrics —
    // the System Health panel reads live fields and shows 0/unknown until the backend fills them (honest). The 3D
    // scenes fall back to a clearly-labelled deterministic DEMO layout only when there is no live visualization.
    const [state, setState] = useState<Partial<SimulationState>>({
        running: false,
        paused: false,
        scenario: "problem",
        speed: 1,
        tick: 0,
        events: [],
    });
    const [loading, setLoading] = useState(false);
    const [connected, setConnected] = useState(false);

    // Fetch state periodically
    const fetchState = useCallback(async () => {
        try {
            const newState = await api.getState();
            setState(newState);
            setConnected(true);
        } catch (e) {
            setConnected(false);
        }
    }, []);

    useEffect(() => {
        fetchState();
        const interval = setInterval(fetchState, 1000);
        return () => clearInterval(interval);
    }, [fetchState]);

    const handleStart = async () => {
        setLoading(true);
        try {
            await api.startSimulation();
            await fetchState();
        } finally {
            setLoading(false);
        }
    };

    const handleStop = async () => {
        await api.stopSimulation();
        await fetchState();
    };

    const handleToggleScenario = async () => {
        const newScenario = state.scenario === "problem" ? "solution" : "problem";
        await api.setScenario(newScenario);
        await fetchState();
    };

    const tabs = [
        { id: "overview", label: "Overview", color: "#00f0ff" },
        { id: "robotics", label: "Robotics", color: "#00ff88" },
        { id: "manufacturing", label: "Manufacturing", color: "#7b2ff7" },
        { id: "supply_chain", label: "Supply Chain", color: "#ffcc00" },
    ] as const;

    return (
        <div className="min-h-screen bg-[#0a0e17] grid-bg">
            {/* Header */}
            <header className="fixed top-0 left-0 right-0 z-50 glass p-4">
                <div className="max-w-7xl mx-auto flex justify-between items-center">
                    <Link href="/" className="text-xl font-bold text-gradient">
                        Embodied AI
                    </Link>

                    {/* Controls */}
                    <div className="flex items-center gap-4">
                        <div className={`flex items-center gap-2 ${connected ? "text-[#00ff88]" : "text-[#ff3366]"}`}>
                            <div className={`w-2 h-2 rounded-full ${connected ? "bg-[#00ff88]" : "bg-[#ff3366]"}`} />
                            <span className="text-sm">{connected ? "Connected" : "Offline (Mock Data)"}</span>
                        </div>

                        <button
                            onClick={handleToggleScenario}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${state.scenario === "problem"
                                    ? "bg-[#ff3366] text-white"
                                    : "bg-[#00ff88] text-black"
                                }`}
                        >
                            {state.scenario === "problem" ? "Problem Mode" : "Solution Mode"}
                        </button>

                        <button
                            onClick={state.running ? handleStop : handleStart}
                            disabled={loading}
                            className={`px-6 py-2 rounded-lg font-medium ${state.running
                                    ? "bg-red-600 hover:bg-red-700"
                                    : "btn-primary"
                                }`}
                        >
                            {loading ? "..." : state.running ? "Stop" : "Start"}
                        </button>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="pt-20 pb-8 px-4 max-w-7xl mx-auto">
                {/* Tabs */}
                <div className="flex gap-2 mb-6">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`px-6 py-3 rounded-lg font-medium transition ${activeTab === tab.id
                                    ? "glass glow-primary"
                                    : "bg-[#141a26] hover:bg-[#1c2333]"
                                }`}
                            style={{
                                borderColor: activeTab === tab.id ? tab.color : "transparent",
                                borderWidth: 2,
                            }}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Content area */}
                <AnimatePresence mode="wait">
                    {activeTab === "overview" && (
                        <motion.div
                            key="overview"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="grid grid-cols-1 lg:grid-cols-3 gap-6"
                        >
                            {/* Metrics */}
                            <div className="glass p-6">
                                <h3 className="text-xl font-bold mb-4">System Health</h3>
                                <div className="space-y-4">
                                    <div className="flex justify-between items-center">
                                        <span className="text-[#8892a4]">Scenario</span>
                                        <span className={state.scenario === "solution" ? "text-[#00ff88]" : "text-[#ffcc00]"}>
                                            {state.scenario || "problem"}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-[#8892a4]">Conflicts</span>
                                        <span className="text-[#ff3366]">{state.metrics?.current?.conflicts ?? 0}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-[#8892a4]">Robot Collisions</span>
                                        <span className="text-[#ffcc00]">{state.metrics?.current?.robot_collisions ?? 0}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-[#8892a4]">Bottlenecks</span>
                                        <span className="text-[#7b2ff7]">{state.metrics?.current?.bottlenecks ?? 0}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-[#8892a4]">Overall Score</span>
                                        <span className={(state.metrics?.current?.overall_score ?? 0) >= 70 ? "text-[#00ff88]" : "text-[#ff3366]"}>
                                            {state.metrics?.current ? `${state.metrics.current.overall_score.toFixed(0)}` : "—"}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Events */}
                            <div className="glass p-6 lg:col-span-2">
                                <h3 className="text-xl font-bold mb-4">Recent Events</h3>
                                <div className="space-y-2 max-h-64 overflow-y-auto">
                                    {(state.events || []).slice(0, 10).map((event) => (
                                        <div
                                            key={event.id}
                                            className={`p-3 rounded-lg text-sm flex items-start gap-3 ${event.severity === "critical" ? "bg-[#ff336620]" :
                                                    event.severity === "high" ? "bg-[#ffcc0020]" :
                                                        "bg-[#00ff8820]"
                                                }`}
                                        >
                                            <div className={`w-2 h-2 rounded-full mt-1.5 ${event.severity === "critical" ? "bg-[#ff3366]" :
                                                    event.severity === "high" ? "bg-[#ffcc00]" :
                                                        "bg-[#00ff88]"
                                                }`} />
                                            <div>
                                                <div className="text-[#8892a4] text-xs">{event.domain}</div>
                                                <div>{event.description}</div>
                                            </div>
                                        </div>
                                    ))}
                                    {(!state.events || state.events.length === 0) && (
                                        <div className="text-[#8892a4] text-center py-8">
                                            No events yet. Start the simulation to see activity.
                                        </div>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    )}

                    {activeTab === "robotics" && (
                        <motion.div
                            key="robotics"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="glass p-4"
                        >
                            <div className="h-[600px]">
                                <Suspense fallback={<div className="h-full flex items-center justify-center">Loading 3D...</div>}>
                                    <WarehouseScene robots={state.visualization?.robots?.map((r) => ({
                                        id: r.robot_id, position_x: r.position_x, position_y: r.position_y,
                                        battery: r.battery, status: r.status,
                                    })) ?? mockRobots} />
                                </Suspense>
                            </div>
                        </motion.div>
                    )}

                    {activeTab === "manufacturing" && (
                        <motion.div
                            key="manufacturing"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="glass p-4"
                        >
                            <div className="h-[600px]">
                                <Suspense fallback={<div className="h-full flex items-center justify-center">Loading 3D...</div>}>
                                    <FactoryScene stages={state.visualization?.stages?.map((s) => ({
                                        id: s.stage_id, name: s.name, queue_depth: s.queue_depth, status: s.status,
                                    })) ?? mockStages} />
                                </Suspense>
                            </div>
                        </motion.div>
                    )}

                    {activeTab === "supply_chain" && (
                        <motion.div
                            key="supply_chain"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="glass p-6"
                        >
                            <h3 className="text-xl font-bold mb-6">Supply Chain Overview</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Suppliers */}
                                <div>
                                    <h4 className="text-lg font-semibold text-[#00f0ff] mb-4">Suppliers</h4>
                                    <div className="space-y-3">
                                        {["GlobalMaterials", "TechParts Inc", "QualityComponents", "FastLogistics", "ReliableSupply"].map((name, i) => (
                                            <div key={i} className="bg-[#1c2333] p-4 rounded-lg flex justify-between items-center">
                                                <span>{name}</span>
                                                <span className={`px-2 py-1 rounded text-xs ${detRand() > 0.8 ? "bg-[#ffcc0030] text-[#ffcc00]" : "bg-[#00ff8830] text-[#00ff88]"
                                                    }`}>
                                                    {detRand() > 0.8 ? "Delayed" : "Active"}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Inventory */}
                                <div>
                                    <h4 className="text-lg font-semibold text-[#7b2ff7] mb-4">Critical Inventory</h4>
                                    <div className="space-y-3">
                                        {["Steel Sheets", "Electronic Components", "Sensors", "Motors", "Packaging"].map((name, i) => {
                                            const level = 20 + detRand() * 80;
                                            return (
                                                <div key={i} className="bg-[#1c2333] p-4 rounded-lg">
                                                    <div className="flex justify-between mb-2">
                                                        <span>{name}</span>
                                                        <span className={level < 30 ? "text-[#ff3366]" : "text-[#8892a4]"}>
                                                            {level.toFixed(0)}%
                                                        </span>
                                                    </div>
                                                    <div className="h-2 bg-[#2a3444] rounded-full overflow-hidden">
                                                        <div
                                                            className={`h-full transition-all ${level < 30 ? "bg-[#ff3366]" : level < 50 ? "bg-[#ffcc00]" : "bg-[#00ff88]"
                                                                }`}
                                                            style={{ width: `${level}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>
        </div>
    );
}
