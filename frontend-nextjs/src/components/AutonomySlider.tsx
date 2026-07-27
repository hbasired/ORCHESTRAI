// Stage 28 (adoption UX, research §35.8): PROGRESSIVE-AUTONOMY control. The shadow→assisted→supervised→autonomous
// ladder (mapped to the pilot canary + HITL). Trust is built incrementally; every level is gated by the safety
// validator + HITL interrupt — promotion never bypasses them. Data from the REAL backend `/adoption/autonomy`.
"use client";

import { useEffect, useState } from "react";
import { Layers } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Rung { level: string; desc: string; hitl: string; }
interface AutonomyState { current: string; ladder: Rung[]; note: string; }

export default function AutonomySlider() {
    const [a, setA] = useState<AutonomyState | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let alive = true;
        fetch(`${API_BASE}/adoption/autonomy`).then(r => r.json())
            .then(d => { if (alive) { setA(d); setError(null); } })
            .catch(e => { if (alive) setError(e instanceof Error ? e.message : "backend unavailable"); });
        return () => { alive = false; };
    }, []);

    if (error) return <div className="glass p-4 text-sm text-red-400">Autonomy state unavailable: {error}</div>;
    if (!a) return <div className="glass p-4 text-sm text-[#8892a4]">Loading autonomy state…</div>;

    const curIdx = a.ladder.findIndex(r => r.level === a.current);

    return (
        <div className="glass p-4">
            <div className="flex items-center gap-2 mb-3">
                <Layers className="w-5 h-5 text-purple-400" />
                <h3 className="font-semibold">Autonomy Level</h3>
                <span className="ml-auto text-xs bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded uppercase">
                    {a.current}
                </span>
            </div>

            <div className="flex gap-1 mb-3">
                {a.ladder.map((r, i) => (
                    <div key={r.level} className="flex-1 text-center">
                        <div className={`h-2 rounded ${i <= curIdx ? "bg-purple-500" : "bg-[#1c2333]"}`} />
                        <div className={`text-[10px] mt-1 capitalize ${i === curIdx ? "text-purple-300 font-semibold" : "text-[#8892a4]"}`}>
                            {r.level}
                        </div>
                    </div>
                ))}
            </div>

            <div className="space-y-1.5 text-xs">
                {a.ladder.map((r, i) => (
                    <div key={r.level} className={`flex gap-2 ${i === curIdx ? "text-white" : "text-[#8892a4]"}`}>
                        <span className="capitalize w-20 shrink-0">{r.level}</span>
                        <span className="flex-1">{r.desc}</span>
                        <span className="text-blue-300 shrink-0">HITL: {r.hitl}</span>
                    </div>
                ))}
            </div>

            <p className="text-[11px] text-[#8892a4] mt-3">{a.note}</p>
        </div>
    );
}
