// Stage 28 (adoption UX, research §35.8): TRUST-CALIBRATION component. A recommendation is NEVER a bare score —
// it surfaces confidence + an uncertainty band + the counterfactual + the GraphRAG citations that ground it.
// Data comes from the REAL backend `/adoption/recommendation`; honest empty-state when unavailable (no fabrication).
"use client";

import { useEffect, useState } from "react";
import { ShieldCheck, AlertTriangle, Link2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Recommendation {
    query: string;
    recommendation: string;
    confidence: number;
    uncertainty_band: [number, number] | null;
    counterfactual: string;
    grounding: { grounded: boolean; citations: string[]; context: string[] };
    hitl_required: boolean;
}

export default function TrustCalibration({ query }: { query: string }) {
    const [rec, setRec] = useState<Recommendation | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let alive = true;
        fetch(`${API_BASE}/adoption/recommendation?query=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(d => { if (alive) { setRec(d); setError(null); } })
            .catch(e => { if (alive) setError(e instanceof Error ? e.message : "backend unavailable"); });
        return () => { alive = false; };
    }, [query]);

    if (error) return <div className="glass p-4 text-sm text-red-400">Recommendation unavailable: {error}</div>;
    if (!rec) return <div className="glass p-4 text-sm text-[#8892a4]">Loading recommendation…</div>;

    const pct = Math.round(rec.confidence * 100);
    const grounded = rec.grounding.grounded;

    return (
        <div className="glass p-4">
            <div className="flex items-center gap-2 mb-3">
                {grounded ? <ShieldCheck className="w-5 h-5 text-green-400" /> : <AlertTriangle className="w-5 h-5 text-yellow-400" />}
                <h3 className="font-semibold">Recommendation</h3>
                {rec.hitl_required && (
                    <span className="ml-auto text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded">
                        human confirm required
                    </span>
                )}
            </div>

            <p className="text-sm mb-3">{rec.recommendation}</p>

            {/* Confidence + uncertainty band — never a bare score */}
            <div className="mb-3">
                <div className="flex justify-between text-xs text-[#8892a4] mb-1">
                    <span>Confidence</span><span>{pct}%{rec.uncertainty_band && ` (band ${Math.round(rec.uncertainty_band[0] * 100)}–${Math.round(rec.uncertainty_band[1] * 100)}%)`}</span>
                </div>
                <div className="h-2 bg-[#1c2333] rounded overflow-hidden">
                    <div className={`h-full ${grounded ? "bg-green-500" : "bg-yellow-500"}`} style={{ width: `${pct}%` }} />
                </div>
            </div>

            {/* Counterfactual — what happens if we do nothing */}
            <div className="text-xs text-[#8892a4] mb-3">
                <span className="text-white">If no action:</span> {rec.counterfactual}
            </div>

            {/* GraphRAG citations — the trust anchor (grounded, not model priors) */}
            <div className="flex items-start gap-2 text-xs">
                <Link2 className="w-4 h-4 text-blue-400 mt-0.5" />
                {grounded ? (
                    <div className="flex flex-wrap gap-1">
                        {rec.grounding.citations.map((c, i) => (
                            <span key={i} className="bg-blue-500/15 text-blue-300 px-1.5 py-0.5 rounded">{c}</span>
                        ))}
                    </div>
                ) : (
                    <span className="text-yellow-400">No grounding found — escalated to a human (no guess made).</span>
                )}
            </div>
        </div>
    );
}
