"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import {
    LayoutDashboard,
    Bot,
    Factory,
    Truck,
    Brain,
    Network,
    BarChart3,
    Mic,
    Menu,
    X,
    Wifi,
    WifiOff,
    Play
} from "lucide-react";

const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/factory", label: "Factory Sim", icon: Play },
    { href: "/robotics", label: "Robotics", icon: Bot },
    { href: "/manufacturing", label: "Manufacturing", icon: Factory },
    { href: "/supply-chain", label: "Supply Chain", icon: Truck },
    { href: "/embodied-agent", label: "Embodied AI", icon: Brain },
    { href: "/knowledge-graph", label: "Knowledge Graph", icon: Network },
    { href: "/model-metrics", label: "Model Metrics", icon: BarChart3 },
    { href: "/voice", label: "Voice Interface", icon: Mic },
];

export default function Navigation() {
    const pathname = usePathname();
    const [isOpen, setIsOpen] = useState(false);
    const [connected, setConnected] = useState(false);
    const [mode, setMode] = useState<"problem" | "solution">("problem");

    // Check backend connection
    useEffect(() => {
        const checkConnection = async () => {
            try {
                const res = await fetch("http://localhost:8000/");
                setConnected(res.ok);
            } catch {
                setConnected(false);
            }
        };
        checkConnection();
        const interval = setInterval(checkConnection, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <header className="sticky top-0 z-50 bg-[#0d1321]/90 backdrop-blur-xl border-b border-[#1c2333]">
            <div className="max-w-[1920px] mx-auto px-4">
                <div className="flex items-center justify-between h-14">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#7c3aed] to-[#06b6d4] flex items-center justify-center">
                            <Brain className="w-5 h-5 text-white" />
                        </div>
                        <span className="font-bold text-lg hidden sm:block">AI Embodied Agent</span>
                    </Link>

                    {/* Desktop Navigation */}
                    <nav className="hidden lg:flex items-center gap-1">
                        {navItems.map((item) => {
                            const Icon = item.icon;
                            const isActive = pathname === item.href;
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${isActive
                                        ? "bg-[#7c3aed]/20 text-[#a78bfa] border border-[#7c3aed]/30"
                                        : "text-[#8892a4] hover:text-white hover:bg-[#1c2333]"
                                        }`}
                                >
                                    <Icon className="w-4 h-4" />
                                    <span className="hidden xl:inline">{item.label}</span>
                                </Link>
                            );
                        })}
                    </nav>

                    {/* Right Side Controls */}
                    <div className="flex items-center gap-3">
                        {/* Mode Toggle */}
                        <div className="hidden md:flex items-center gap-2 bg-[#1c2333] rounded-lg p-1">
                            <button
                                onClick={() => setMode("problem")}
                                className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${mode === "problem"
                                    ? "bg-[#ef4444] text-white"
                                    : "text-[#8892a4] hover:text-white"
                                    }`}
                            >
                                Problem
                            </button>
                            <button
                                onClick={() => setMode("solution")}
                                className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${mode === "solution"
                                    ? "bg-[#10b981] text-white"
                                    : "text-[#8892a4] hover:text-white"
                                    }`}
                            >
                                Solution
                            </button>
                        </div>

                        {/* Connection Status */}
                        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs ${connected ? "bg-[#10b981]/10 text-[#10b981]" : "bg-[#ef4444]/10 text-[#ef4444]"
                            }`}>
                            {connected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
                            <span className="hidden sm:inline">{connected ? "Connected" : "Offline"}</span>
                        </div>

                        {/* Mobile Menu */}
                        <button
                            onClick={() => setIsOpen(!isOpen)}
                            className="lg:hidden p-2 text-[#8892a4] hover:text-white"
                        >
                            {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                        </button>
                    </div>
                </div>

                {/* Mobile Navigation */}
                {isOpen && (
                    <nav className="lg:hidden py-4 border-t border-[#1c2333] grid grid-cols-2 gap-2">
                        {navItems.map((item) => {
                            const Icon = item.icon;
                            const isActive = pathname === item.href;
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    onClick={() => setIsOpen(false)}
                                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${isActive
                                        ? "bg-[#7c3aed]/20 text-[#a78bfa]"
                                        : "text-[#8892a4] hover:text-white hover:bg-[#1c2333]"
                                        }`}
                                >
                                    <Icon className="w-4 h-4" />
                                    {item.label}
                                </Link>
                            );
                        })}
                    </nav>
                )}
            </div>
        </header>
    );
}
