"use client";

import { useEffect, useState } from "react";
import Navigation from "@/components/Navigation";
import { api, type ModelMetric } from "@/lib/api";
import {
    BarChart3, Brain, Activity, TrendingUp, Settings, RefreshCw, Download, CheckCircle
} from "lucide-react";

// =============================================================================
// TYPES — the display shape, derived from the REAL backend `ModelMetric` (lib/api.ts).
// Fields the API does not carry (domain/purpose/lastTrained/trainingHistory) are OPTIONAL and shown as "—" /
// omitted — NEVER fabricated. Stage 34 (G-047): this page renders live metrics from `/api/metrics/models` or an
// HONEST "no metrics recorded" state; it no longer ships a hardcoded fake model array.
// =============================================================================

interface DisplayModel {
    id: string;
    name: string;
    type: "regression" | "classification" | "reinforcement" | "other";
    status: "active";
    metrics: Record<string, number>;
    hyperparameters: Record<string, string | number>;
    trainingSamples?: number;
    inferenceMs?: number;
}

function classifyType(t: string): DisplayModel["type"] {
    if (t === "regression" || t === "classification" || t === "reinforcement") return t;
    if (t === "rl") return "reinforcement";
    return "other";
}

function toDisplay(name: string, m: ModelMetric): DisplayModel {
    return {
        id: name,
        name,
        type: classifyType(String(m.model_type ?? "other")),
        status: "active",
        metrics: (m.latest_metrics as Record<string, number>) ?? {},
        hyperparameters: (m.hyperparameters as Record<string, string | number>) ?? {},
        trainingSamples: m.training_samples,
        inferenceMs: m.inference_time_ms,
    };
}

// =============================================================================
// COMPONENTS
// =============================================================================

const TYPE_COLORS: Record<DisplayModel["type"], { bg: string; border: string; text: string }> = {
    regression: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400" },
    classification: { bg: "bg-green-500/10", border: "border-green-500/30", text: "text-green-400" },
    reinforcement: { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-400" },
    other: { bg: "bg-gray-500/10", border: "border-gray-500/30", text: "text-gray-400" },
};

function ModelCard({ model, onSelect }: { model: DisplayModel; onSelect: (id: string) => void }) {
    const colors = TYPE_COLORS[model.type];
    const entries = Object.entries(model.metrics).slice(0, 4);
    return (
        <div
            className={`glass p-4 cursor-pointer hover:ring-2 hover:ring-purple-500/50 transition-all ${colors.bg} ${colors.border}`}
            onClick={() => onSelect(model.id)}
        >
            <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">{model.name}</h3>
                <span className={`text-xs px-2 py-1 rounded capitalize ${colors.bg} ${colors.text}`}>{model.type}</span>
            </div>
            {entries.length > 0 ? (
                <div className="grid grid-cols-2 gap-2 mb-3">
                    {entries.map(([key, value]) => (
                        <div key={key} className="bg-[#0a0e17] p-2 rounded text-center">
                            <div className="text-lg font-bold text-white">
                                {typeof value === "number" && Math.abs(value) < 1 ? value.toFixed(3) : value}
                            </div>
                            <div className="text-xs text-[#8892a4]">{key}</div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="text-xs text-[#8892a4] mb-3">No recorded metrics for this model.</div>
            )}
            <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-green-400" />
                    <span className="text-[#8892a4] capitalize">{model.status}</span>
                </div>
                {model.trainingSamples != null && (
                    <span className="text-[#8892a4]">{model.trainingSamples.toLocaleString()} samples</span>
                )}
            </div>
        </div>
    );
}

function ModelDetailsPanel({ model }: { model: DisplayModel | null }) {
    if (!model) {
        return (
            <div className="glass p-6 h-full flex items-center justify-center text-[#8892a4]">
                <div className="text-center">
                    <Brain className="w-16 h-16 mx-auto mb-4 opacity-30" />
                    <p>Select a model to view detailed metrics and configuration</p>
                </div>
            </div>
        );
    }
    return (
        <div className="glass p-6">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">{model.name}</h2>
                <div className="flex gap-2">
                    <button className="p-2 bg-[#1c2333] rounded-lg" aria-label="refresh"><RefreshCw className="w-4 h-4" /></button>
                    <button className="p-2 bg-[#1c2333] rounded-lg" aria-label="settings"><Settings className="w-4 h-4" /></button>
                    <button className="p-2 bg-[#1c2333] rounded-lg" aria-label="download"><Download className="w-4 h-4" /></button>
                </div>
            </div>
            <div className="mb-6">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Activity className="w-4 h-4 text-cyan-400" />Performance Metrics</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {Object.entries(model.metrics).map(([key, value]) => (
                        <div key={key} className="bg-[#1c2333] p-3 rounded-lg text-center">
                            <div className="text-xl font-bold text-white">
                                {typeof value === "number" && Math.abs(value) < 1 ? value.toFixed(3) : value}
                            </div>
                            <div className="text-xs text-[#8892a4]">{key}</div>
                        </div>
                    ))}
                </div>
            </div>
            <div className="mb-6">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Settings className="w-4 h-4 text-orange-400" />Hyperparameters</h3>
                <div className="bg-[#1c2333] rounded-lg p-4 grid grid-cols-2 gap-3">
                    {Object.entries(model.hyperparameters).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between text-sm">
                            <span className="text-[#8892a4]">{key.replace(/_/g, " ")}</span>
                            <span className="font-mono text-white">{String(value)}</span>
                        </div>
                    ))}
                </div>
            </div>
            <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg flex items-center gap-2 text-sm text-[#8892a4]">
                <CheckCircle className="w-4 h-4 text-purple-400" />
                <span>Live metrics from <span className="font-mono text-white">/api/metrics/models</span>
                {model.inferenceMs != null && <> · inference ~{model.inferenceMs} ms</>}</span>
            </div>
        </div>
    );
}

function EmptyState() {
    return (
        <div className="glass p-10 text-center text-[#8892a4]">
            <TrendingUp className="w-14 h-14 mx-auto mb-4 opacity-30" />
            <p className="text-white font-semibold mb-1">No live model metrics recorded</p>
            <p className="text-sm max-w-xl mx-auto">
                The backend serves <span className="font-mono">/api/metrics/models</span> only once real metrics are
                recorded (it returns 503 until then — it does not fabricate). The models&apos; real, held-out metrics
                are documented in the model cards (<span className="font-mono">compliance/model-cards/</span>) and
                <span className="font-mono"> models/*.metrics.json</span>. This page shows live values when the backend
                has them.
            </p>
        </div>
    );
}

// =============================================================================
// DOCUMENTED MODEL & DATASET REGISTRY — real, sourced from the signed model cards
// (compliance/model-cards/*.md) + KB_02/KB_03. These are held-out BENCHMARK / TRAINING
// metrics (not live inference metrics). Every dataset carries a real link to verify it.
// =============================================================================

interface RegistryModel {
    name: string; stage: string; type: DisplayModel["type"]; arch: string;
    dataset: string; datasetLink: string; datasetKind: "benchmark" | "synthetic" | "corpus" | "pretrained";
    metrics: { label: string; value: string }[]; why: string;
}

const MODEL_REGISTRY: RegistryModel[] = [
    { name: "pdm_failure_predictor", stage: "Stage 4", type: "classification", arch: "XGBoost (gradient-boosted trees), recall-tuned threshold 0.779",
      dataset: "AI4I 2020 Predictive Maintenance (UCI #601)", datasetLink: "https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset", datasetKind: "benchmark",
      metrics: [{ label: "ROC-AUC", value: "0.971" }, { label: "PR-AUC", value: "0.847" }, { label: "threshold", value: "0.779" }],
      why: "Tabular sensor data → boosted trees beat the MLP (PR-AUC 0.847 vs 0.679); recall-tuned because a missed failure costs more than a false alarm." },
    { name: "rul_transformer_cmapss", stage: "Stage 8", type: "regression", arch: "Transformer encoder: Linear(14→64) → sinusoidal PE → 2× encoder (4 heads, FFN 128, GELU) → mean-pool → MLP head",
      dataset: "NASA C-MAPSS FD001 (turbofan RUL)", datasetLink: "https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data", datasetKind: "benchmark",
      metrics: [{ label: "test RMSE", value: "13.80" }, { label: "NASA score", value: "372" }, { label: "vs CNN/LSTM", value: "beats 18.45 / 16.14" }],
      why: "Attention captures long-range degradation better than recurrence on the canonical RUL benchmark — proves the architecture on real data, not just the sim." },
    { name: "defect_classifier", stage: "Stage 9", type: "classification", arch: "ResNet-18 transfer learning (fine-tune layer4 + fc), RGB 128×128 → 6 classes",
      dataset: "NEU-CLS steel surface defects (6 classes)", datasetLink: "https://www.kaggle.com/datasets/kaustubhdikshit/neu-surface-defect-database", datasetKind: "benchmark",
      metrics: [{ label: "accuracy", value: "99.3%" }, { label: "macro-F1", value: "0.993" }, { label: "vs tiny-CNN", value: "+11.1 pt" }],
      why: "Transfer learning from ImageNet features beats a from-scratch CNN by 11 points — the right call when labelled industrial images are scarce." },
    { name: "demand_forecaster", stage: "Stage 5", type: "regression", arch: "LSTM — window 24, hidden 128, 1 layer, 15 cyclical features, log1p target",
      dataset: "UCI Bike Sharing #275 (seasonal demand proxy)", datasetLink: "https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset", datasetKind: "benchmark",
      metrics: [{ label: "MAE", value: "32.9" }, { label: "MAPE", value: "21.0%" }, { label: "vs persistence", value: "+59%" }],
      why: "A sequence model for a time series; cyclical encodings + log target from a grid search. Proxy → re-fit on a customer's real orders at pilot." },
    { name: "rl_intervention_maskable_ppo", stage: "Stage 7", type: "reinforcement", arch: "MaskablePPO (SB3-contrib) with action masking, 250k steps",
      dataset: "Gymnasium maintenance-scheduling MDP (documented model)", datasetLink: "https://gymnasium.farama.org/", datasetKind: "synthetic",
      metrics: [{ label: "return", value: "−125.1" }, { label: "vs best rule", value: "−137.4" }, { label: "paired wins", value: "36 / 50" }],
      why: "Action masking + a richer MDP (group batching, crew contention) let RL genuinely beat the best rule — the first version that earned its place. CRN-paired eval." },
    { name: "world_model_ttf", stage: "Stage 8", type: "regression", arch: "1-layer LSTM h48 → MLP head → scalar time-to-failure",
      dataset: "SimWorld crack rollouts (deterministic digital twin)", datasetLink: "https://simpy.readthedocs.io/", datasetKind: "synthetic",
      metrics: [{ label: "TTF MAE", value: "0.067 min" }, { label: "vs naive", value: "+97.8%" }],
      why: "Forecasts the horizon the diagnosis/verify steps need. Replaced an earlier np.random stub — now genuinely learned." },
    { name: "injection_classifier", stage: "Stage 31", type: "classification", arch: "Logistic Regression over bge-small embeddings (+ optional LLM judge)",
      dataset: "OWASP-LLM01 prompt-injection corpus (217 examples)", datasetLink: "https://owasp.org/www-project-top-10-for-large-language-model-applications/", datasetKind: "corpus",
      metrics: [{ label: "detection", value: "0.9935 → 1.0" }, { label: "FPR", value: "→ 0" }, { label: "eval", value: "held-out 5-fold CV" }],
      why: "A calibrated learned tier over semantic embeddings beats brittle regex; held-out cross-validation, not train-on-test." },
    { name: "yolov8n (vision)", stage: "utility", type: "other", arch: "YOLOv8n object detection (pretrained, real inference — de-mocked)",
      dataset: "COCO (pretrained weights)", datasetLink: "https://cocodataset.org/", datasetKind: "pretrained",
      metrics: [{ label: "mode", value: "real inference" }, { label: "fallback", value: "honest-unavailable" }],
      why: "Real object detection for the vision path; replaced a random-detection fallback. Fine-tune on warehouse imagery is a pilot item." },
];

const KIND_BADGE: Record<RegistryModel["datasetKind"], string> = {
    benchmark: "bg-blue-500/15 text-blue-300 border-blue-500/30",
    synthetic: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    corpus: "bg-green-500/15 text-green-300 border-green-500/30",
    pretrained: "bg-purple-500/15 text-purple-300 border-purple-500/30",
};

function ModelRegistry() {
    return (
        <div className="mt-8">
            <div className="flex items-center gap-2 mb-1">
                <Brain className="w-5 h-5 text-purple-400" />
                <h2 className="text-lg font-bold">Documented model &amp; dataset registry</h2>
            </div>
            <p className="text-sm text-[#8892a4] mb-4">
                The 8 trained models, their datasets (with links to verify), and their <b>held-out benchmark / training
                metrics</b> from the signed model cards (<span className="font-mono">compliance/model-cards/</span> +
                <span className="font-mono"> models/*.metrics.json</span>). These are reproducible eval numbers — distinct
                from the <i>live</i> inference metrics above.
            </p>
            <div className="flex flex-wrap gap-2 mb-4 text-xs">
                <span className={`px-2 py-1 rounded border ${KIND_BADGE.benchmark}`}>■ public benchmark</span>
                <span className={`px-2 py-1 rounded border ${KIND_BADGE.corpus}`}>■ public corpus</span>
                <span className={`px-2 py-1 rounded border ${KIND_BADGE.synthetic}`}>■ synthetic / sim</span>
                <span className={`px-2 py-1 rounded border ${KIND_BADGE.pretrained}`}>■ pretrained</span>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {MODEL_REGISTRY.map((m) => (
                    <div key={m.name} className="glass p-4">
                        <div className="flex items-start justify-between mb-2 gap-2">
                            <div>
                                <h3 className="font-semibold font-mono text-sm text-white">{m.name}</h3>
                                <span className="text-xs text-[#8892a4]">{m.stage} · {m.type}</span>
                            </div>
                            <span className={`text-[10px] px-2 py-1 rounded border whitespace-nowrap ${KIND_BADGE[m.datasetKind]}`}>{m.datasetKind}</span>
                        </div>
                        <p className="text-xs text-[#b9c2d0] mb-3">{m.arch}</p>
                        <div className="grid grid-cols-3 gap-2 mb-3">
                            {m.metrics.map((mm) => (
                                <div key={mm.label} className="bg-[#0a0e17] p-2 rounded text-center">
                                    <div className="text-sm font-bold text-white">{mm.value}</div>
                                    <div className="text-[10px] text-[#8892a4]">{mm.label}</div>
                                </div>
                            ))}
                        </div>
                        <div className="text-xs text-[#8892a4] mb-2">
                            <span className="text-[#b9c2d0] font-semibold">Dataset:</span> {m.dataset}{" "}
                            <a href={m.datasetLink} target="_blank" rel="noopener noreferrer"
                               className="text-cyan-400 hover:underline">↗ verify</a>
                        </div>
                        <p className="text-xs text-[#7d8798] italic">{m.why}</p>
                    </div>
                ))}
            </div>
            <p className="text-xs text-[#6b7280] mt-4">
                Honest scope: benchmark/sim datasets are <b>proxies</b> — every model is designed to be re-fit on a
                customer&apos;s real telemetry at pilot (ledger G-035). Full dataset catalog with licences:
                <span className="font-mono"> knowledge-base/KB_03_Datasets_Catalog.md</span>.
            </p>
        </div>
    );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function ModelMetricsPage() {
    const [models, setModels] = useState<DisplayModel[] | null>(null);   // null = loading
    const [selectedModel, setSelectedModel] = useState<string | null>(null);
    const [filter, setFilter] = useState<string>("all");

    useEffect(() => {
        let alive = true;
        api.getModelMetrics()
            .then((raw: Record<string, ModelMetric>) => {
                if (alive) setModels(Object.entries(raw).map(([n, m]) => toDisplay(n, m)));
            })
            .catch(() => { if (alive) setModels([]); });   // honest empty on failure, never fabricated
        return () => { alive = false; };
    }, []);

    const loading = models === null;
    const list = models ?? [];
    const filteredModels = filter === "all" ? list : list.filter((m) => m.type === filter);
    const selected = list.find((m) => m.id === selectedModel) || null;

    return (
        <div className="min-h-screen bg-[#0a0e17]">
            <Navigation />
            <main className="p-4 max-w-[1920px] mx-auto">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2"><BarChart3 className="w-6 h-6 text-cyan-400" />Model Metrics</h1>
                        <p className="text-sm text-[#8892a4]">Live performance metrics from the backend — real values or an honest empty state.</p>
                    </div>
                    <select value={filter} onChange={(e) => setFilter(e.target.value)}
                            className="bg-[#1c2333] border border-[#2a3346] rounded-lg px-3 py-2 text-sm">
                        <option value="all">All Models</option>
                        <option value="regression">Regression</option>
                        <option value="classification">Classification</option>
                        <option value="reinforcement">Reinforcement</option>
                        <option value="other">Other</option>
                    </select>
                </div>

                {loading ? (
                    <div className="glass p-10 text-center text-[#8892a4]">Loading live metrics…</div>
                ) : list.length === 0 ? (
                    <EmptyState />
                ) : (
                    <>
                        <div className="grid grid-cols-4 gap-4 mb-6">
                            <div className="glass p-4 text-center"><div className="text-2xl font-bold text-purple-400">{list.length}</div><div className="text-xs text-[#8892a4]">Total Models</div></div>
                            <div className="glass p-4 text-center"><div className="text-2xl font-bold text-blue-400">{list.filter(m => m.type === "regression").length}</div><div className="text-xs text-[#8892a4]">Regression</div></div>
                            <div className="glass p-4 text-center"><div className="text-2xl font-bold text-green-400">{list.filter(m => m.type === "classification").length}</div><div className="text-xs text-[#8892a4]">Classification</div></div>
                            <div className="glass p-4 text-center"><div className="text-2xl font-bold text-orange-400">{list.filter(m => m.type === "reinforcement").length}</div><div className="text-xs text-[#8892a4]">Reinforcement</div></div>
                        </div>
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                            <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
                                {filteredModels.map((model) => (
                                    <ModelCard key={model.id} model={model} onSelect={setSelectedModel} />
                                ))}
                            </div>
                            <div className="lg:col-span-1"><ModelDetailsPanel model={selected} /></div>
                        </div>
                    </>
                )}

                {/* Always-visible real registry: models + datasets (with links) + benchmark metrics */}
                <ModelRegistry />
            </main>
        </div>
    );
}
