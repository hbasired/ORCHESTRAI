'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

interface DomainCardProps {
    title: string;
    icon: React.ReactNode;
    agents: string[];
    problems: string[];
    color: string;
}

function DomainCard({ title, icon, agents, problems, color }: DomainCardProps) {
    return (
        <div className="glass rounded-2xl p-6 hover:border-opacity-50 transition-all group">
            <div className={`w-14 h-14 rounded-xl ${color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                {icon}
            </div>
            <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
            <div className="space-y-2 mb-4">
                <p className="text-sm text-gray-400">AI Agents:</p>
                <div className="flex flex-wrap gap-2">
                    {agents.map((agent, i) => (
                        <span key={i} className="text-xs px-2 py-1 rounded bg-[#1c2333] text-cyan-400">
                            {agent}
                        </span>
                    ))}
                </div>
            </div>
            <div className="space-y-1">
                <p className="text-sm text-gray-400">Problems when isolated:</p>
                <ul className="text-sm text-red-400 space-y-1">
                    {problems.map((problem, i) => (
                        <li key={i} className="flex items-start gap-2">
                            <span className="text-red-500">⚠</span>
                            {problem}
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
}

export default function LandingPage() {
    const [animationStep, setAnimationStep] = useState(0);

    useEffect(() => {
        const timer = setInterval(() => {
            setAnimationStep(prev => (prev + 1) % 4);
        }, 3000);
        return () => clearInterval(timer);
    }, []);

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white">
            {/* Background effects */}
            <div className="absolute inset-0 grid-pattern opacity-10" />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-to-b from-cyan-500/10 to-transparent rounded-full blur-3xl" />

            {/* Hero Section */}
            <section className="relative min-h-screen flex flex-col items-center justify-center px-4 py-20">
                <div className="text-center max-w-4xl mx-auto">
                    {/* Logo */}
                    <div className="flex items-center justify-center gap-4 mb-8">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-400 via-purple-500 to-pink-500 flex items-center justify-center animate-pulse">
                            <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                        </div>
                    </div>

                    <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                        AI Embodied Agent
                    </h1>

                    <p className="text-xl md:text-2xl text-gray-300 mb-4">
                        Unified Intelligence for Manufacturing
                    </p>

                    <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-12">
                        A fully autonomous Electronics PCB Assembly plant powered by coordinated AI agents.
                        Watch how the Embodied Agent transforms isolated domain operations into a unified,
                        cost-optimized, and energy-efficient production system.
                    </p>

                    <Link
                        href="/login"
                        className="inline-flex items-center gap-3 px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold text-lg hover:shadow-lg hover:shadow-cyan-500/25 transition-all hover:scale-105"
                    >
                        Enter Platform
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                    </Link>
                </div>

                {/* Scroll indicator */}
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
                    <svg className="w-6 h-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                </div>
            </section>

            {/* Problem Section */}
            <section className="relative py-20 px-4">
                <div className="max-w-6xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold mb-4">
                            The <span className="text-red-400">Problem</span>: Isolated Operations
                        </h2>
                        <p className="text-gray-400 max-w-2xl mx-auto">
                            Traditional manufacturing plants run domain-specific AI agents independently.
                            Each optimizes locally, but hurts global performance.
                        </p>
                    </div>

                    {/* Domain cards */}
                    <div className="grid md:grid-cols-3 gap-6 mb-12">
                        <DomainCard
                            title="Robotics Domain"
                            icon={
                                <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                                </svg>
                            }
                            agents={['PPO Navigation', 'Path Planner', 'Fleet Manager']}
                            problems={[
                                'Robots collide at intersections',
                                'Battery emergencies during critical tasks',
                                'Uneven distribution across stations'
                            ]}
                            color="bg-gradient-to-br from-blue-500 to-cyan-400"
                        />

                        <DomainCard
                            title="Manufacturing Domain"
                            icon={
                                <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                                </svg>
                            }
                            agents={['LSTM Queue Predictor', 'CNN Defect Detector', 'ANN Energy Optimizer']}
                            problems={[
                                'Queue overflow at bottleneck stations',
                                'Parts not arriving from supply chain',
                                'Energy spikes from uncoordinated ops'
                            ]}
                            color="bg-gradient-to-br from-orange-500 to-yellow-400"
                        />

                        <DomainCard
                            title="Supply Chain Domain"
                            icon={
                                <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                                </svg>
                            }
                            agents={['ANN Demand Forecaster', 'Q-Learning Inventory', 'JIT Optimizer']}
                            problems={[
                                'Orders placed without production context',
                                'Deliveries arrive when warehouse full',
                                'Stockouts of critical components'
                            ]}
                            color="bg-gradient-to-br from-green-500 to-emerald-400"
                        />
                    </div>

                    {/* Conflict visualization */}
                    <div className="glass rounded-2xl p-8">
                        <h3 className="text-xl font-bold mb-6 text-center text-red-400">Cross-Domain Conflicts</h3>
                        <div className="grid md:grid-cols-2 gap-6">
                            <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/30">
                                <div className="flex items-center gap-3 mb-3">
                                    <span className="text-2xl">🤖</span>
                                    <span className="text-lg font-medium">↔️</span>
                                    <span className="text-2xl">🏭</span>
                                </div>
                                <p className="text-sm text-gray-300">
                                    <strong className="text-red-400">Robot-Manufacturing Conflict:</strong> Robots assigned to charging
                                    when stations desperately need parts. Production line starves while robots sit idle at charging stations.
                                </p>
                            </div>

                            <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/30">
                                <div className="flex items-center gap-3 mb-3">
                                    <span className="text-2xl">🏭</span>
                                    <span className="text-lg font-medium">↔️</span>
                                    <span className="text-2xl">📦</span>
                                </div>
                                <p className="text-sm text-gray-300">
                                    <strong className="text-red-400">Manufacturing-Supply Conflict:</strong> Supply chain orders based on
                                    forecasts, ignoring current production bottlenecks. Parts arrive for stations that are already backed up.
                                </p>
                            </div>

                            <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/30">
                                <div className="flex items-center gap-3 mb-3">
                                    <span className="text-2xl">📦</span>
                                    <span className="text-lg font-medium">↔️</span>
                                    <span className="text-2xl">🤖</span>
                                </div>
                                <p className="text-sm text-gray-300">
                                    <strong className="text-red-400">Supply-Robot Conflict:</strong> Deliveries scheduled without robot
                                    availability. Trucks wait at dock while all robots are in manufacturing area.
                                </p>
                            </div>

                            <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/30">
                                <div className="flex items-center gap-3 mb-3">
                                    <span className="text-2xl">⚡</span>
                                    <span className="text-lg font-medium">↔️</span>
                                    <span className="text-2xl">💰</span>
                                </div>
                                <p className="text-sm text-gray-300">
                                    <strong className="text-red-400">Energy-Cost Conflict:</strong> Each domain optimizes energy independently.
                                    No coordination leads to peak demand charges and wasted capacity.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Solution Section */}
            <section className="relative py-20 px-4 bg-gradient-to-b from-transparent via-cyan-950/20 to-transparent">
                <div className="max-w-6xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold mb-4">
                            The <span className="text-cyan-400">Solution</span>: Embodied Agent
                        </h2>
                        <p className="text-gray-400 max-w-2xl mx-auto">
                            A unified AI coordinator that perceives the entire system and makes cross-domain decisions.
                            Powered by LLM reasoning for intelligent coordination.
                        </p>
                    </div>

                    {/* Coordination diagram */}
                    <div className="glass rounded-2xl p-8 mb-12">
                        <div className="flex flex-col items-center">
                            {/* Central brain */}
                            <div className="relative mb-8">
                                <div className="w-32 h-32 rounded-full bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center z-10 relative animate-pulse">
                                    <div className="text-center">
                                        <svg className="w-12 h-12 text-white mx-auto mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                        </svg>
                                        <span className="text-xs font-bold">Embodied Agent</span>
                                    </div>
                                </div>
                            </div>

                            {/* Connected domains */}
                            <div className="grid grid-cols-3 gap-12 w-full max-w-2xl">
                                <div className="text-center">
                                    <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center mx-auto mb-2">
                                        <span className="text-2xl">🤖</span>
                                    </div>
                                    <span className="text-sm font-medium">Robotics</span>
                                    <div className="text-xs text-gray-500 mt-1">Coordinated fleet</div>
                                </div>

                                <div className="text-center">
                                    <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-orange-500 to-yellow-400 flex items-center justify-center mx-auto mb-2">
                                        <span className="text-2xl">🏭</span>
                                    </div>
                                    <span className="text-sm font-medium">Manufacturing</span>
                                    <div className="text-xs text-gray-500 mt-1">Optimized flow</div>
                                </div>

                                <div className="text-center">
                                    <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-green-500 to-emerald-400 flex items-center justify-center mx-auto mb-2">
                                        <span className="text-2xl">📦</span>
                                    </div>
                                    <span className="text-sm font-medium">Supply Chain</span>
                                    <div className="text-xs text-gray-500 mt-1">JIT delivery</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Embodied Agent Architecture */}
                    <div className="glass rounded-2xl p-8 mb-12">
                        <h3 className="text-xl font-bold mb-6 text-center text-cyan-400">The Embodied Architecture</h3>
                        <p className="text-gray-400 text-center mb-8 max-w-2xl mx-auto">
                            Unlike traditional AI systems, our Embodied Agent possesses three distinct faculties that enable true coordination.
                        </p>
                        <div className="grid md:grid-cols-3 gap-6">
                            <div className="bg-purple-500/10 rounded-xl p-5 border border-purple-500/30">
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="w-12 h-12 rounded-lg bg-purple-500/20 flex items-center justify-center">
                                        <span className="text-2xl">🧠</span>
                                    </div>
                                    <span className="text-lg font-bold text-purple-400">The Brain</span>
                                </div>
                                <p className="text-sm text-gray-300 mb-3">
                                    <strong className="text-purple-300">LangGraph Orchestration</strong> - Stateful reasoning with cyclic decision loops.
                                    ReAct pattern: Reason → Act → Observe → Repeat.
                                </p>
                                <div className="text-xs text-gray-500 space-y-1">
                                    <div>• Multi-turn reasoning</div>
                                    <div>• Human-in-the-loop checkpoints</div>
                                    <div>• Cross-domain planning</div>
                                </div>
                            </div>

                            <div className="bg-blue-500/10 rounded-xl p-5 border border-blue-500/30">
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center">
                                        <span className="text-2xl">🦾</span>
                                    </div>
                                    <span className="text-lg font-bold text-blue-400">The Body</span>
                                </div>
                                <p className="text-sm text-gray-300 mb-3">
                                    <strong className="text-blue-300">SimPy Simulation</strong> - Physical representation with constraints.
                                    Location, battery, speed, resource contention.
                                </p>
                                <div className="text-xs text-gray-500 space-y-1">
                                    <div>• Discrete event simulation</div>
                                    <div>• VDA 5050 AGV protocol</div>
                                    <div>• Real-time position tracking</div>
                                </div>
                            </div>

                            <div className="bg-green-500/10 rounded-xl p-5 border border-green-500/30">
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="w-12 h-12 rounded-lg bg-green-500/20 flex items-center justify-center">
                                        <span className="text-2xl">📊</span>
                                    </div>
                                    <span className="text-lg font-bold text-green-400">The Memory</span>
                                </div>
                                <p className="text-sm text-gray-300 mb-3">
                                    <strong className="text-green-300">Neo4j Knowledge Graph</strong> - Structured, persistent memory.
                                    GraphRAG for context-aware retrieval.
                                </p>
                                <div className="text-xs text-gray-500 space-y-1">
                                    <div>• Reasoning traces for audit</div>
                                    <div>• Factory topology modeling</div>
                                    <div>• ESG compliance tracking</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Carbon-Aware Scheduling */}
                    <div className="glass rounded-2xl p-6 mb-12">
                        <div className="flex items-center gap-4 mb-4">
                            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center">
                                <span className="text-2xl">🌿</span>
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-green-400">Carbon-Aware Scheduling</h3>
                                <p className="text-sm text-gray-400">Optimize for both efficiency and sustainability</p>
                            </div>
                        </div>
                        <div className="grid md:grid-cols-2 gap-4">
                            <div className="bg-[#1a2235] rounded-lg p-4">
                                <p className="text-sm text-gray-300">
                                    Jobs shift to <strong className="text-green-400">"green windows"</strong> when renewable energy is available.
                                    The agent balances delivery deadlines with carbon intensity forecasts.
                                </p>
                            </div>
                            <div className="bg-[#1a2235] rounded-lg p-4">
                                <p className="text-sm text-gray-300">
                                    <strong className="text-cyan-400">Scope 3 Tracking</strong>: Carbon tokens follow products through the supply chain,
                                    enabling accurate ESG reporting.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Impact metrics */}
                    <div className="grid md:grid-cols-4 gap-6">
                        {[
                            { label: 'Productivity', value: '+32%', icon: '📈', color: 'text-green-400' },
                            { label: 'Energy Savings', value: '-24%', icon: '⚡', color: 'text-yellow-400' },
                            { label: 'Cost Reduction', value: '-18%', icon: '💰', color: 'text-cyan-400' },
                            { label: 'Defect Rate', value: '-45%', icon: '✅', color: 'text-purple-400' },
                        ].map((metric, i) => (
                            <div key={i} className="glass rounded-xl p-6 text-center">
                                <div className="text-3xl mb-2">{metric.icon}</div>
                                <div className={`text-3xl font-bold ${metric.color} mb-1`}>{metric.value}</div>
                                <div className="text-sm text-gray-400">{metric.label}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="relative py-20 px-4">
                <div className="max-w-4xl mx-auto text-center">
                    <h2 className="text-3xl md:text-4xl font-bold mb-6">
                        Experience the Difference
                    </h2>
                    <p className="text-gray-400 mb-8">
                        See the full Electronics PCB Assembly simulation. Toggle between Problem (isolated agents)
                        and Solution (Embodied Agent) modes to witness the transformation.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Link
                            href="/login"
                            className="inline-flex items-center justify-center gap-3 px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold text-lg hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
                        >
                            Launch Platform
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                        </Link>

                        <a
                            href="https://github.com"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center justify-center gap-3 px-8 py-4 rounded-xl border border-gray-600 text-gray-300 font-semibold text-lg hover:border-gray-400 hover:text-white transition-all"
                        >
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                            </svg>
                            View Source
                        </a>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t border-[#2a3444] py-8 px-4">
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center">
                            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <span className="text-sm text-gray-400">AI Embodied Agent v2.0</span>
                    </div>

                    <div className="text-sm text-gray-500">
                        Manufacturing Intelligence Platform • {new Date().getFullYear()}
                    </div>
                </div>
            </footer>
        </div>
    );
}
