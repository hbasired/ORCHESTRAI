"use client";

// =============================================================================
// Voice Assistant — LIVE, honest. The backend Whisper (STT) + Piper (TTS) pipeline
// is NOT initialized in this environment (GET /api/voice/status), and the raw voice
// LLM is not grounded — so we DO NOT use it (it could hallucinate plant state).
// Instead: answers come from the GROUNDED /factory/ask (real evidence + citations),
// and the browser's own speech engine handles mic input + read-aloud (real, client-side).
// =============================================================================

import { useCallback, useEffect, useRef, useState } from "react";
import Navigation from "@/components/Navigation";
import { Mic, Volume2, Send, Brain, Square } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface VoiceStatus { stt_initialized: boolean; tts_initialized: boolean; whisper_model?: string; piper_voice?: string; }
interface AskResult { grounded: boolean; answer: string; citations: string[]; }

// minimal typing for the browser Web Speech API (not in the default TS DOM lib)
type SR = { lang: string; interimResults: boolean; onresult: (e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void; onend: () => void; start: () => void; stop: () => void };
function getRecognition(): SR | null {
    if (typeof window === "undefined") return null;
    const w = window as unknown as { SpeechRecognition?: new () => SR; webkitSpeechRecognition?: new () => SR };
    const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
    return Ctor ? new Ctor() : null;
}

export default function VoicePage() {
    const [status, setStatus] = useState<VoiceStatus | null>(null);
    const [question, setQuestion] = useState("what is happening on the line and why?");
    const [answer, setAnswer] = useState<AskResult | null>(null);
    const [busy, setBusy] = useState(false);
    const [listening, setListening] = useState(false);
    const [speechOK, setSpeechOK] = useState(false);
    const recRef = useRef<SR | null>(null);

    useEffect(() => {
        fetch(`${API_BASE}/api/voice/status`).then((r) => r.ok ? r.json() : null).then(setStatus).catch(() => setStatus(null));
        setSpeechOK(getRecognition() !== null && typeof window !== "undefined" && "speechSynthesis" in window);
    }, []);

    const ask = useCallback(async (q: string) => {
        setBusy(true); setAnswer(null);
        try {
            const r = await fetch(`${API_BASE}/factory/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q }) });
            const d: AskResult = await r.json(); setAnswer(d);
            if (typeof window !== "undefined" && "speechSynthesis" in window && d.answer) {
                const u = new SpeechSynthesisUtterance(d.answer); window.speechSynthesis.cancel(); window.speechSynthesis.speak(u);
            }
        } catch { setAnswer({ grounded: false, answer: "Backend unreachable — no fabricated answer.", citations: [] }); }
        finally { setBusy(false); }
    }, []);

    const startListening = () => {
        const rec = getRecognition(); if (!rec) return;
        rec.lang = "en-US"; rec.interimResults = false;
        rec.onresult = (e) => { const t = e.results[0][0].transcript; setQuestion(t); setListening(false); ask(t); };
        rec.onend = () => setListening(false);
        recRef.current = rec; setListening(true); rec.start();
    };
    const stopListening = () => { recRef.current?.stop(); setListening(false); };
    const readAloud = () => { if (answer && "speechSynthesis" in window) { const u = new SpeechSynthesisUtterance(answer.answer); window.speechSynthesis.cancel(); window.speechSynthesis.speak(u); } };

    return (
        <div className="min-h-screen bg-[#0a0e17] text-white">
            <Navigation />
            <main className="p-4 max-w-[1000px] mx-auto">
                <h1 className="text-2xl font-bold flex items-center gap-2 mb-1"><Mic className="w-6 h-6 text-cyan-400" />Voice Assistant</h1>
                <p className="text-sm text-[#8892a4] mb-4">Ask the factory by voice or text. Answers are <b>grounded in real backend evidence</b> (/factory/ask) — it never invents plant state.</p>

                {/* honest pipeline status */}
                <div className="glass p-3 mb-4 text-xs text-[#8892a4]">
                    <span className="font-semibold text-white">Backend voice pipeline: </span>
                    STT (Whisper) <b className={status?.stt_initialized ? "text-green-400" : "text-yellow-400"}>{status ? (status.stt_initialized ? "ready" : "not initialized") : "…"}</b> ·
                    TTS (Piper) <b className={status?.tts_initialized ? "text-green-400" : "text-yellow-400"}>{status ? (status.tts_initialized ? "ready" : "not initialized") : "…"}</b>.
                    {status && !status.tts_initialized && <> Since Whisper/Piper aren&apos;t initialized here, this page uses your <b>browser&apos;s</b> speech engine for mic + read-aloud {speechOK ? "(available)" : "(not available in this browser — use text)"}. The <i>answer</i> always comes from the grounded backend.</>}
                </div>

                {/* ask */}
                <div className="glass p-4 mb-4">
                    <div className="flex gap-2">
                        <input value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask(question)}
                               className="flex-1 bg-[#0d1220] border border-[#2a3346] rounded-lg px-3 py-2 text-sm" placeholder="ask the factory…" />
                        {speechOK && (listening
                            ? <button onClick={stopListening} className="px-3 bg-red-500/90 hover:bg-red-500 rounded-lg" aria-label="stop"><Square className="w-4 h-4" /></button>
                            : <button onClick={startListening} disabled={busy} className="px-3 bg-purple-500/90 hover:bg-purple-500 rounded-lg disabled:opacity-40" aria-label="speak"><Mic className="w-4 h-4" /></button>)}
                        <button onClick={() => ask(question)} disabled={busy} className="px-3 bg-cyan-500/90 hover:bg-cyan-500 text-black rounded-lg disabled:opacity-40" aria-label="ask"><Send className="w-4 h-4" /></button>
                    </div>
                    {listening && <div className="text-xs text-purple-400 mt-2 animate-pulse">🎤 listening… speak now</div>}
                    {busy && <div className="text-xs text-[#8892a4] mt-2">gathering evidence…</div>}
                </div>

                {answer && (
                    <div className="glass p-4">
                        <div className="flex items-center justify-between mb-2">
                            <div className={`text-xs flex items-center gap-1 ${answer.grounded ? "text-green-400" : "text-yellow-400"}`}><Brain className="w-3.5 h-3.5" />{answer.grounded ? "grounded in evidence" : "no evidence (honest-empty)"}</div>
                            {speechOK && <button onClick={readAloud} className="text-xs flex items-center gap-1 text-cyan-400 hover:underline"><Volume2 className="w-3.5 h-3.5" />read aloud</button>}
                        </div>
                        <p className="text-sm text-[#dbe2ea]">{answer.answer}</p>
                        {answer.citations?.length > 0 && <div className="flex flex-wrap gap-1 mt-2">{answer.citations.map((c, i) => <span key={i} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1c2333] text-cyan-400">{c}</span>)}</div>}
                    </div>
                )}

                <p className="text-xs text-[#6b7280] mt-4">Honest by design: the ungrounded voice-LLM endpoint is deliberately NOT used (it can hallucinate plant state); answers come from grounded evidence, and the mic/speech uses your browser&apos;s real engine — nothing fabricated.</p>
            </main>
        </div>
    );
}
