"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface LiveMetrics {
    conflicts: number;
    robot_collisions: number;
    bottlenecks: number;
    stockouts: number;
    throughput: number;
    energy_kwh: number;
    response_time_s: number;
    robot_efficiency: number;
    production_efficiency: number;
    supply_chain_health: number;
    overall_score: number;
}

interface Improvements {
    conflict_reduction_pct: number;
    collision_reduction_pct: number;
    bottleneck_reduction_pct: number;
    stockout_reduction_pct: number;
    throughput_improvement_pct: number;
    energy_savings_pct: number;
    response_time_improvement_pct: number;
    overall_score_improvement_pct: number;
}

interface Props {
    scenario: "problem" | "solution";
    metrics: {
        current: LiveMetrics;
        problem: LiveMetrics;
        solution: LiveMetrics;
        improvements: Improvements;
    } | null;
}

export default function LiveMetricsPanel({ scenario, metrics }: Props) {
    const isProblem = scenario === "problem";
    const current = metrics?.current;
    const improvements = metrics?.improvements;

    if (!current) {
        return (
            <div className="glass p-4 text-center text-[#8892a4]">
                Waiting for simulation data...
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Mode Indicator */}
            <div className={`glass p-4 border-2 ${isProblem ? "border-[#ff336650]" : "border-[#00ff8850]"}`}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${isProblem ? "bg-[#ff3366] animate-pulse" : "bg-[#00ff88]"}`} />
                        <span className={`font-bold ${isProblem ? "text-[#ff3366]" : "text-[#00ff88]"}`}>
                            {isProblem ? "PROBLEM MODE" : "SOLUTION MODE"}
                        </span>
                    </div>
                    <span className="text-sm text-[#8892a4]">
                        {isProblem ? "Isolated Agents" : "Embodied Coordination"}
                    </span>
                </div>
            </div>

            {/* Overall Score */}
            <div className="glass p-6">
                <div className="text-center">
                    <div className="text-sm text-[#8892a4] mb-2">Overall System Score</div>
                    <motion.div
                        key={current.overall_score}
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className={`text-5xl font-bold ${current.overall_score > 80 ? "text-[#00ff88]" :
                                current.overall_score > 60 ? "text-[#ffcc00]" : "text-[#ff3366]"
                            }`}
                    >
                        {current.overall_score.toFixed(0)}%
                    </motion.div>
                    {!isProblem && improvements && (
                        <div className="text-sm text-[#00ff88] mt-2">
                            +{improvements.overall_score_improvement_pct.toFixed(1)}% vs Problem Mode
                        </div>
                    )}
                </div>

                {/* Efficiency Bars */}
                <div className="mt-6 space-y-3">
                    <EfficiencyBar
                        label="Robot Fleet"
                        value={current.robot_efficiency}
                        color={isProblem ? "#ff3366" : "#00ff88"}
                    />
                    <EfficiencyBar
                        label="Production Line"
                        value={current.production_efficiency}
                        color={isProblem ? "#ff3366" : "#00ff88"}
                    />
                    <EfficiencyBar
                        label="Supply Chain"
                        value={current.supply_chain_health}
                        color={isProblem ? "#ff3366" : "#00ff88"}
                    />
                </div>
            </div>

            {/* Issue Counters */}
            <div className="grid grid-cols-2 gap-3">
                <IssueCounter
                    label="Collisions"
                    value={current.robot_collisions}
                    isProblem={isProblem}
                    improvement={improvements?.collision_reduction_pct}
                />
                <IssueCounter
                    label="Bottlenecks"
                    value={current.bottlenecks}
                    isProblem={isProblem}
                    improvement={improvements?.bottleneck_reduction_pct}
                />
                <IssueCounter
                    label="Stockouts"
                    value={current.stockouts}
                    isProblem={isProblem}
                    improvement={improvements?.stockout_reduction_pct}
                />
                <IssueCounter
                    label="Conflicts"
                    value={current.conflicts}
                    isProblem={isProblem}
                    improvement={improvements?.conflict_reduction_pct}
                />
            </div>

            {/* Performance Metrics */}
            <div className="glass p-4 space-y-3">
                <h4 className="text-sm font-medium text-[#8892a4]">Performance</h4>

                <div className="flex justify-between items-center">
                    <span className="text-sm text-[#8892a4]">Throughput</span>
                    <div className="text-right">
                        <span className={`font-mono font-bold ${isProblem ? "text-[#ffcc00]" : "text-[#00ff88]"}`}>
                            {current.throughput.toFixed(0)}
                        </span>
                        <span className="text-xs text-[#8892a4] ml-1">units/hr</span>
                    </div>
                </div>

                <div className="flex justify-between items-center">
                    <span className="text-sm text-[#8892a4]">Energy Usage</span>
                    <div className="text-right">
                        <span className={`font-mono font-bold ${isProblem ? "text-[#ff3366]" : "text-[#00ff88]"}`}>
                            {current.energy_kwh.toFixed(1)}
                        </span>
                        <span className="text-xs text-[#8892a4] ml-1">kWh</span>
                    </div>
                </div>

                <div className="flex justify-between items-center">
                    <span className="text-sm text-[#8892a4]">Response Time</span>
                    <div className="text-right">
                        <span className={`font-mono font-bold ${current.response_time_s > 3 ? "text-[#ff3366]" : "text-[#00ff88]"
                            }`}>
                            {current.response_time_s.toFixed(1)}
                        </span>
                        <span className="text-xs text-[#8892a4] ml-1">sec</span>
                    </div>
                </div>
            </div>

            {/* Improvement Summary (Solution Mode Only) */}
            {!isProblem && improvements && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass p-4 border-2 border-[#00ff8850]"
                >
                    <h4 className="text-sm font-medium text-[#00ff88] mb-3">
                        Embodied Agent Impact
                    </h4>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                        <ImprovementStat label="Collisions" value={improvements.collision_reduction_pct} />
                        <ImprovementStat label="Bottlenecks" value={improvements.bottleneck_reduction_pct} />
                        <ImprovementStat label="Stockouts" value={improvements.stockout_reduction_pct} />
                        <ImprovementStat label="Throughput" value={improvements.throughput_improvement_pct} invert />
                        <ImprovementStat label="Energy" value={improvements.energy_savings_pct} />
                        <ImprovementStat label="Response" value={improvements.response_time_improvement_pct} />
                    </div>
                </motion.div>
            )}
        </div>
    );
}

function EfficiencyBar({ label, value, color }: { label: string; value: number; color: string }) {
    return (
        <div>
            <div className="flex justify-between text-xs mb-1">
                <span className="text-[#8892a4]">{label}</span>
                <span style={{ color }}>{value.toFixed(1)}%</span>
            </div>
            <div className="h-2 bg-[#1c2333] rounded-full overflow-hidden">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, value)}%` }}
                    transition={{ duration: 0.5 }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: color }}
                />
            </div>
        </div>
    );
}

function IssueCounter({ label, value, isProblem, improvement }: {
    label: string;
    value: number;
    isProblem: boolean;
    improvement?: number;
}) {
    return (
        <div className={`glass p-3 ${value > 0 && isProblem ? "border border-[#ff336650]" : ""}`}>
            <div className="text-xs text-[#8892a4]">{label}</div>
            <div className="flex items-end justify-between">
                <AnimatePresence mode="popLayout">
                    <motion.span
                        key={value}
                        initial={{ y: -10, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        exit={{ y: 10, opacity: 0 }}
                        className={`text-2xl font-bold ${value === 0 ? "text-[#00ff88]" : isProblem ? "text-[#ff3366]" : "text-[#ffcc00]"
                            }`}
                    >
                        {value}
                    </motion.span>
                </AnimatePresence>
                {!isProblem && improvement !== undefined && improvement > 0 && (
                    <span className="text-xs text-[#00ff88]">-{improvement.toFixed(0)}%</span>
                )}
            </div>
        </div>
    );
}

function ImprovementStat({ label, value, invert = false }: { label: string; value: number; invert?: boolean }) {
    const isPositive = invert ? value > 0 : value > 0;
    const display = invert ? `+${value.toFixed(1)}%` : `-${value.toFixed(1)}%`;

    return (
        <div className="flex justify-between">
            <span className="text-[#8892a4]">{label}</span>
            <span className={isPositive ? "text-[#00ff88]" : "text-[#8892a4]"}>
                {isPositive ? display : "0%"}
            </span>
        </div>
    );
}
