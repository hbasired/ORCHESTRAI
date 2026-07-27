// Stage 28 (adoption UX, research §35.8): the persona-shaped adoption page — trust calibration + progressive
// autonomy + WIIFM (loss-aversion), all fed by REAL backend data (/adoption/*). No fabrication: every panel is a
// real endpoint or an honest empty-state. This is the "adoption-as-a-feature" differentiator — competitors optimise
// model accuracy, not operator adoption.
"use client";

import { useEffect, useState } from "react";
import Navigation from "@/components/Navigation";
import TrustCalibration from "@/components/TrustCalibration";
import AutonomySlider from "@/components/AutonomySlider";
import { TrendingDown, Users } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Wiifm {
    available: boolean;
    headlines: { metric: string; prevented: number; ci: [number, number]; framing: string; honest_label: string }[];
    reason?: string;
}
interface Personas { [k: string]: { label: string; wants: string; surfaces: string[] }; }

export default function AdoptionPage() {
    const [wiifm, setWiifm] = useState<Wiifm | null>(null);
    const [personas, setPersonas] = useState<Personas | null>(null);

    useEffect(() => {
        fetch(`${API_BASE}/adoption/wiifm`).then(r => r.json()).then(setWiifm).catch(() => setWiifm(null));
        fetch(`${API_BASE}/adoption/personas`).then(r => r.json()).then(d => setPersonas(d.personas)).catch(() => setPersonas(null));
    }, []);

    return (
        <div className="min-h-screen bg-[#0a0e17]">
            <Navigation />
            <main className="p-6 max-w-5xl mx-auto space-y-6">
                <div>
                    <h1 className="text-2xl font-bold">Adoption</h1>
                    <p className="text-sm text-[#8892a4]">
                        Design-thinking + behavioural science, on real data — trust calibration, progressive autonomy,
                        and prevented-loss framing.
                    </p>
                </div>

                {/* WIIFM / loss-aversion headline — prevented loss, not promised gain */}
                <div className="glass p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <TrendingDown className="w-5 h-5 text-green-400" />
                        <h3 className="font-semibold">What you get (prevented loss)</h3>
                    </div>
                    {wiifm?.available ? (
                        wiifm.headlines.map((h, i) => (
                            <div key={i} className="mb-2">
                                <div className="text-lg font-bold text-green-400">
                                    {h.prevented.toFixed(0)} {h.metric}
                                </div>
                                <p className="text-sm text-[#8892a4]">{h.framing}</p>
                                <p className="text-[11px] text-[#8892a4] mt-1">Honest scope: {h.honest_label}</p>
                            </div>
                        ))
                    ) : (
                        <p className="text-sm text-[#8892a4]">
                            {wiifm?.reason || "Waiting for a measured A/B result from the backend."}
                        </p>
                    )}
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                    <TrustCalibration query="stage crack torque anomaly response" />
                    <AutonomySlider />
                </div>

                {/* Persona map (design-thinking: which real surface each role needs) */}
                <div className="glass p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <Users className="w-5 h-5 text-blue-400" />
                        <h3 className="font-semibold">Built for your role</h3>
                    </div>
                    {personas ? (
                        <div className="grid sm:grid-cols-2 gap-3 text-sm">
                            {Object.entries(personas).map(([k, p]) => (
                                <div key={k} className="bg-[#1c2333] rounded-lg p-3">
                                    <div className="font-medium">{p.label}</div>
                                    <div className="text-xs text-[#8892a4]">{p.wants}</div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-[#8892a4]">Persona map unavailable (backend offline).</p>
                    )}
                </div>
            </main>
        </div>
    );
}
