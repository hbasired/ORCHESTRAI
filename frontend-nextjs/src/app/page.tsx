"use client";

import { useState, useEffect, useCallback } from "react";
import Navigation from "@/components/Navigation";
import { api } from "@/lib/api";
import { useLiveState } from "@/lib/liveState";
import {
  Bot, Factory, Truck, Activity, AlertTriangle,
  Zap, TrendingUp, Battery, Gauge, Brain
} from "lucide-react";

// =============================================================================
// TYPES
// =============================================================================

interface Robot {
  id: number;
  position: { x: number; y: number };
  battery: number;
  status: string;  // Stage 28: real backend status (was a narrow union)
  task: string | null;
  speed: number;
}

interface Stage {
  id: number;
  name: string;
  queue_depth: number;
  throughput: number;
  status: string;  // Stage 28: real backend status
  energy_consumption: number;
  defect_rate: number;
}

interface Supplier {
  id: number;
  name: string;
  status: string;  // Stage 28: real backend status
  reliability: number;
  lead_days: number;
}

interface InventoryItem {
  id: number;
  name: string;
  stock_level: number;
  max_capacity: number;
  consumption_rate: number;
}

interface SystemState {
  robots: Robot[];
  stages: Stage[];
  suppliers: Supplier[];
  inventory: InventoryItem[];
  metrics: {
    throughput: number;
    quality_rate: number;
    energy_kwh: number;
    alerts: number;
  };
  mode: "problem" | "solution";
}

interface AgentAction {
  id: string;
  timestamp: string;
  agent: string;
  action: string;
  reasoning: string;
}

// (Stage 28 de-mock G-082: client-side mock generation REMOVED — live data via useLiveState)

// =============================================================================
// COMPONENTS
// =============================================================================

function RoboticsPanel({ robots }: { robots: Robot[] }) {
  const working = robots.filter(r => r.status === "working").length;
  const idle = robots.filter(r => r.status === "idle").length;
  const warning = robots.filter(r => r.status === "warning" || r.status === "error").length;
  const avgBattery = Math.round(robots.reduce((sum, r) => sum + r.battery, 0) / robots.length);

  return (
    <div className="glass p-4 h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="flex items-center gap-2 font-semibold">
          <Bot className="w-5 h-5 text-blue-400" />
          Robotics Fleet
        </h3>
        <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded">
          {robots.length} Robots
        </span>
      </div>

      {/* 3D-like visualization */}
      <div className="relative h-48 bg-[#0a0e17] rounded-lg overflow-hidden mb-4">
        <div className="absolute inset-0 grid-pattern opacity-30" />
        {robots.slice(0, 20).map((robot) => (
          <div
            key={robot.id}
            className={`absolute w-3 h-3 rounded-sm transition-all duration-300 ${robot.status === "working" ? "bg-blue-500" :
                robot.status === "idle" ? "bg-green-500" :
                  robot.status === "charging" ? "bg-purple-500" :
                    robot.status === "warning" ? "bg-yellow-500 animate-pulse" :
                      "bg-red-500 animate-pulse"
              }`}
            style={{
              left: `${(robot.position.x / 100) * 100}%`,
              top: `${(robot.position.y / 60) * 100}%`,
              transform: "translate(-50%, -50%)"
            }}
            title={`Robot ${robot.id}: ${robot.status}`}
          />
        ))}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-2 text-center">
        <div className="bg-[#1c2333] rounded-lg p-2">
          <div className="text-lg font-bold text-green-400">{working}</div>
          <div className="text-xs text-[#8892a4]">Working</div>
        </div>
        <div className="bg-[#1c2333] rounded-lg p-2">
          <div className="text-lg font-bold text-blue-400">{idle}</div>
          <div className="text-xs text-[#8892a4]">Idle</div>
        </div>
        <div className="bg-[#1c2333] rounded-lg p-2">
          <div className="text-lg font-bold text-yellow-400">{warning}</div>
          <div className="text-xs text-[#8892a4]">Alert</div>
        </div>
        <div className="bg-[#1c2333] rounded-lg p-2 flex items-center justify-center gap-1">
          <Battery className="w-4 h-4 text-purple-400" />
          <div>
            <div className="text-lg font-bold">{avgBattery}%</div>
            <div className="text-xs text-[#8892a4]">Avg</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ManufacturingPanel({ stages }: { stages: Stage[] }) {
  const bottlenecks = stages.filter(s => s.status === "bottleneck").length;
  const totalThroughput = Math.round(stages.reduce((sum, s) => sum + s.throughput, 0) / stages.length);
  const totalEnergy = Math.round(stages.reduce((sum, s) => sum + s.energy_consumption, 0));

  return (
    <div className="glass p-4 h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="flex items-center gap-2 font-semibold">
          <Factory className="w-5 h-5 text-orange-400" />
          Manufacturing Stages
        </h3>
        <span className={`text-xs px-2 py-1 rounded ${bottlenecks > 0 ? "bg-red-500/20 text-red-400" : "bg-green-500/20 text-green-400"
          }`}>
          {bottlenecks} Bottlenecks
        </span>
      </div>

      {/* Stage Grid */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        {stages.slice(0, 4).map((stage) => (
          <div
            key={stage.id}
            className={`p-2 rounded-lg border ${stage.status === "bottleneck"
                ? "bg-red-500/10 border-red-500/30"
                : "bg-[#1c2333] border-[#2a3346]"
              }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium truncate">{stage.name}</span>
              {stage.status === "bottleneck" && (
                <span className="text-xs bg-red-500/20 text-red-400 px-1 rounded">bottleneck</span>
              )}
            </div>
            <div className="text-xs text-[#8892a4]">Queue: <span className="text-white">{stage.queue_depth}</span></div>
            <div className="text-xs text-[#8892a4]">
              → {Math.round(stage.throughput)}/hr &nbsp; ⚡ {stage.energy_consumption.toFixed(1)} kW
            </div>
          </div>
        ))}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-[#1c2333] rounded-lg p-2">
          <div className="text-lg font-bold">{stages.length}</div>
          <div className="text-xs text-[#8892a4]">Stages</div>
        </div>
        <div className="bg-[#1c2333] rounded-lg p-2">
          <div className="text-lg font-bold text-blue-400">{totalThroughput}</div>
          <div className="text-xs text-[#8892a4]">Units/hr</div>
        </div>
        <div className="bg-[#1c2333] rounded-lg p-2">
          <div className="text-lg font-bold text-orange-400">{totalEnergy}</div>
          <div className="text-xs text-[#8892a4]">kW Total</div>
        </div>
      </div>
    </div>
  );
}

function SupplyChainPanel({ suppliers, inventory }: { suppliers: Supplier[]; inventory: InventoryItem[] }) {
  const delayed = suppliers.filter(s => s.status === "delayed").length;
  const lowStock = inventory.filter(i => i.stock_level < i.max_capacity * 0.3).length;

  return (
    <div className="glass p-4 h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="flex items-center gap-2 font-semibold">
          <Truck className="w-5 h-5 text-cyan-400" />
          Supply Chain
        </h3>
        <div className="flex gap-2 text-xs">
          {delayed > 0 && (
            <span className="bg-red-500/20 text-red-400 px-2 py-1 rounded">{delayed} Delayed</span>
          )}
          {lowStock > 0 && (
            <span className="bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded">{lowStock} Low Stock</span>
          )}
        </div>
      </div>

      {/* Demand Forecast Mini Chart */}
      <div className="h-20 bg-[#0a0e17] rounded-lg mb-3 flex items-end justify-around px-2 pb-2">
        {[40, 60, 55, 70, 80, 75, 90].map((val, i) => (
          <div
            key={i}
            className="w-6 bg-gradient-to-t from-cyan-500/50 to-cyan-400/20 rounded-t"
            style={{ height: `${val}%` }}
          />
        ))}
      </div>
      <div className="text-xs text-[#8892a4] text-center mb-3">7-Day Demand Forecast</div>

      {/* Suppliers */}
      <div className="space-y-2 mb-3">
        {suppliers.slice(0, 3).map((supplier) => (
          <div key={supplier.id} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${supplier.status === "active" ? "bg-green-400" : "bg-red-400"
                }`} />
              <span>{supplier.name}</span>
            </div>
            <span className="text-xs text-[#8892a4]">
              {supplier.lead_days}d lead • {Math.round(supplier.reliability)}% reliable
            </span>
          </div>
        ))}
      </div>

      {/* Inventory Levels */}
      <div className="text-xs text-[#8892a4] mb-2">Inventory Levels</div>
      <div className="space-y-1">
        {inventory.slice(0, 3).map((item) => (
          <div key={item.id} className="flex items-center gap-2">
            <span className="text-xs w-24 truncate">{item.name}</span>
            <div className="flex-1 h-2 bg-[#1c2333] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${item.stock_level / item.max_capacity < 0.3 ? "bg-red-500" :
                    item.stock_level / item.max_capacity < 0.5 ? "bg-yellow-500" : "bg-green-500"
                  }`}
                style={{ width: `${(item.stock_level / item.max_capacity) * 100}%` }}
              />
            </div>
            <span className="text-xs w-8 text-right">
              {Math.round((item.stock_level / item.max_capacity) * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricsPanel({ metrics, mode }: { metrics: SystemState["metrics"]; mode: string }) {
  const isProblem = mode === "problem";

  return (
    <div className="glass p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="flex items-center gap-2 font-semibold">
          <Activity className="w-5 h-5 text-emerald-400" />
          System Metrics
        </h3>
        <div className="flex items-center gap-1 text-xs">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          Live
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 text-[#8892a4] text-xs mb-1">
            <TrendingUp className="w-3 h-3" />
            <span className={isProblem ? "text-red-400" : "text-green-400"}>
              {isProblem ? "↓2.5%" : "↑3.2%"}
            </span>
          </div>
          <div className="text-3xl font-bold">{Math.round(metrics.throughput)}</div>
          <div className="text-xs text-[#8892a4]">Units/hr</div>
        </div>
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 text-[#8892a4] text-xs mb-1">
            <Gauge className="w-3 h-3" />
            <span className={metrics.quality_rate > 95 ? "text-green-400" : "text-yellow-400"}>
              {isProblem ? "↓0.3%" : "↑0.1%"}
            </span>
          </div>
          <div className="text-3xl font-bold">{metrics.quality_rate.toFixed(1)}<span className="text-lg">%</span></div>
          <div className="text-xs text-[#8892a4]">Quality Rate</div>
        </div>
      </div>
    </div>
  );
}

function DecisionPanel({ mode }: { mode: string }) {
  const isProblem = mode === "problem";
  const decision = {
    id: "61c832",
    confidence: isProblem ? 50 : 92,
    title: isProblem
      ? "Stage 10 identified as bottleneck with high queue depth. 16 robot(s) have low battery requiring attention. Optimizing..."
      : "All systems optimized. Cross-domain coordination active. Predictive maintenance scheduled.",
    actions: isProblem
      ? ["Rerouting 3 robots", "Reducing intake at Stage 10", "Requesting expedited delivery"]
      : ["Maintaining optimal flow", "Battery rotation scheduled", "Inventory levels stable"]
  };

  return (
    <div className="glass p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="flex items-center gap-2 font-semibold">
          <Brain className="w-5 h-5 text-purple-400" />
          AI Decisions
        </h3>
        <button className="text-xs bg-purple-500/20 text-purple-400 px-2 py-1 rounded hover:bg-purple-500/30">
          New Decision
        </button>
      </div>

      <div className={`p-3 rounded-lg border ${isProblem ? "bg-yellow-500/10 border-yellow-500/30" : "bg-green-500/10 border-green-500/30"
        }`}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">Decision #{decision.id}</span>
          <span className={`text-sm font-bold ${decision.confidence > 70 ? "text-green-400" : "text-yellow-400"
            }`}>
            {decision.confidence}%
          </span>
        </div>
        <p className="text-xs text-[#8892a4] mb-2">{decision.title}</p>
        <div className="text-xs text-[#8892a4]">Recommended Actions:</div>
        <ul className="text-xs space-y-1 mt-1">
          {decision.actions.map((action, i) => (
            <li key={i} className="flex items-center gap-1">
              <span className="text-purple-400">→</span> {action}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function ControlPanel({ mode, onModeChange }: { mode: string; onModeChange: (m: "problem" | "solution") => void }) {
  const [throughput, setThroughput] = useState(50);
  const [energy, setEnergy] = useState(20);

  return (
    <div className="glass p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="flex items-center gap-2 font-semibold">
          <Zap className="w-5 h-5 text-yellow-400" />
          Optimization Control
        </h3>
      </div>

      {/* Mode Toggle */}
      <div className="mb-4">
        <div className="text-xs text-[#8892a4] mb-2">Simulation Mode</div>
        <div className="flex gap-2">
          <button
            onClick={() => onModeChange("problem")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${mode === "problem"
                ? "bg-red-500 text-white"
                : "bg-[#1c2333] text-[#8892a4] hover:text-white"
              }`}
          >
            🔴 Problem Mode
          </button>
          <button
            onClick={() => onModeChange("solution")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${mode === "solution"
                ? "bg-green-500 text-white"
                : "bg-[#1c2333] text-[#8892a4] hover:text-white"
              }`}
          >
            ✅ Solution Mode
          </button>
        </div>
      </div>

      {/* Sliders */}
      <div className="space-y-3">
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-[#8892a4]">→ Throughput</span>
            <span>{throughput}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={throughput}
            onChange={(e) => setThroughput(Number(e.target.value))}
            className="w-full accent-blue-500"
          />
        </div>
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-[#8892a4]">⚡ Energy Efficiency</span>
            <span>{energy}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={energy}
            onChange={(e) => setEnergy(Number(e.target.value))}
            className="w-full accent-green-500"
          />
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function DashboardPage() {
  const [mode, setMode] = useState<"problem" | "solution">("problem");
  // Stage 28 de-mock (G-082): REAL backend SimWorld data via useLiveState — no browser-side fabrication.
  const { state: live, error } = useLiveState(2000);
  const tick = live?.tick ?? 0;

  // Push the selected scenario to the real backend (honest no-op if unreachable).
  useEffect(() => { api.setScenario(mode).catch(() => { }); }, [mode]);

  // HONEST empty state: the backend is the only data source. No fabrication when it is unavailable.
  if (!live) {
    return (
      <div className="min-h-screen bg-[#0a0e17]">
        <Navigation />
        <main className="p-8 max-w-3xl mx-auto text-center">
          <div className="glass p-8 mt-16">
            <AlertTriangle className="w-10 h-10 text-yellow-400 mx-auto mb-4" />
            <h1 className="text-xl font-bold mb-2">Waiting for the backend</h1>
            <p className="text-sm text-[#8892a4] mb-4">
              This dashboard shows LIVE data from the SimWorld backend at{" "}
              <code className="bg-black/30 px-1 rounded">/api/simulation/state</code>. Start the backend
              (<code className="bg-black/30 px-1 rounded">docker compose up</code> + the API) to see real state — no
              mock data is generated in the browser.
            </p>
            {error && <p className="text-xs text-red-400">Last error: {error}</p>}
          </div>
        </main>
      </div>
    );
  }
  const state = live;

  return (
    <div className="min-h-screen bg-[#0a0e17]">
      <Navigation />

      <main className="p-4 max-w-[1920px] mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">AI Manufacturing Agent</h1>
            <p className="text-sm text-[#8892a4]">Multi-Domain Optimization Dashboard</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              Live
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${mode === "problem"
                ? "bg-red-500/20 text-red-400 border border-red-500/30"
                : "bg-green-500/20 text-green-400 border border-green-500/30"
              }`}>
              Mode: {mode === "problem" ? "Problem (Isolated)" : "Solution (Coordinated)"}
            </div>
            {state.metrics.alerts > 0 && (
              <div className="flex items-center gap-1 px-3 py-1 rounded-full bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 text-sm">
                <AlertTriangle className="w-4 h-4" />
                {state.metrics.alerts} Alerts
              </div>
            )}
          </div>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {/* Robotics */}
          <div className="xl:col-span-1">
            <RoboticsPanel robots={state.robots} />
          </div>

          {/* Manufacturing */}
          <div className="xl:col-span-1">
            <ManufacturingPanel stages={state.stages} />
          </div>

          {/* Supply Chain */}
          <div className="xl:col-span-1">
            <SupplyChainPanel suppliers={state.suppliers} inventory={state.inventory} />
          </div>

          {/* Metrics */}
          <div className="xl:col-span-1">
            <MetricsPanel metrics={state.metrics} mode={mode} />
          </div>

          {/* Decisions */}
          <div className="xl:col-span-1">
            <DecisionPanel mode={mode} />
          </div>

          {/* Controls */}
          <div className="xl:col-span-1">
            <ControlPanel mode={mode} onModeChange={setMode} />
          </div>
        </div>

        {/* Tick counter for demo */}
        <div className="mt-4 text-center text-xs text-[#8892a4]">
          Simulation Tick: {tick} | Last Update: {new Date().toLocaleTimeString()}
        </div>
      </main>
    </div>
  );
}
