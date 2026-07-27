"""Stage 31 (G-077) — a LEARNED prompt-injection detection tier (research §42.1).

The Stage-20 detector was heuristic-regex + semantic-kNN (single cosine threshold). This adds a THIRD tier: a
logistic-regression classifier over bge-small embeddings, TRAINED on the real Stage-20 corpus (153 attacks + 64
benign). A learned decision boundary beats a single kNN threshold on BOTH recall and FPR (arxiv 2410.22284).

Honesty discipline:
 * The REPORTED lift is measured by STRATIFIED K-FOLD cross-validation (train on k-1 folds, score the held-out fold)
   so it is NOT train-on-test. The SHIPPED model is then fit on all data (the deployment artefact).
 * Honest-unavailable: if sklearn / the embedder / the trained model is missing, `is_available()` is False and the
   tier is skipped — it NEVER fabricates a verdict.
 * The binding actuation gate remains `safety/validator` (Rule 3); this is defence-in-depth (no detector is
   fool-proof — arxiv 2504.11168).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
_MODEL_PATH = _MODELS_DIR / "injection_classifier.joblib"
_CORPUS = Path(__file__).resolve().parents[1] / "training" / "evals" / "redteam" / "owasp_llm01_corpus.jsonl"
_DEFAULT_THRESHOLD = 0.5


def _embedder():
    name = os.environ.get("PROMPT_GUARD_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name, device="cpu")


def _load_corpus() -> tuple[list[str], list[int]]:
    prompts, labels = [], []
    for line in _CORPUS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        prompts.append(r["prompt"])
        labels.append(1 if r["label"] == "attack" else 0)
    return prompts, labels


class InjectionClassifier:
    """bge-embedding + logistic-regression injection classifier. Honest about unavailability."""

    def __init__(self, model_path: Optional[Path] = None):
        self._path = model_path or _MODEL_PATH
        self._clf = None
        self._model = None       # embedder
        self._checked = False

    def is_available(self) -> bool:
        try:
            self._load()
            return True
        except Exception:  # noqa: BLE001
            return False

    def _load(self) -> None:
        if self._clf is not None:
            return
        import joblib
        if not self._path.exists():
            raise FileNotFoundError(f"trained injection classifier not found: {self._path} — run fit_and_save()")
        self._clf = joblib.load(self._path)
        self._model = _embedder()

    def predict_proba(self, text: str) -> float:
        """P(injection) in [0,1]. Raises if unavailable (caller checks is_available first / catches)."""
        self._load()
        v = self._model.encode([text], normalize_embeddings=True)
        return float(self._clf.predict_proba(v)[0][1])

    def predict(self, text: str, *, threshold: float = _DEFAULT_THRESHOLD) -> bool:
        return self.predict_proba(text) >= threshold


# ---- training + honest held-out evaluation --------------------------------------------------------------------

def _fit_lr(X, y):
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(max_iter=1000, class_weight="balanced", C=1.0)
    clf.fit(X, y)
    return clf


def cross_val_eval(k: int = 5, *, threshold: float = _DEFAULT_THRESHOLD) -> dict[str, Any]:
    """STRATIFIED k-fold held-out metrics for the LEARNED tier alone (honest — never train-on-test)."""
    import numpy as np
    from sklearn.model_selection import StratifiedKFold
    prompts, labels = _load_corpus()
    y = np.array(labels)
    model = _embedder()
    X = np.asarray(model.encode(prompts, normalize_embeddings=True))
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    tp = fp = tn = fn = 0
    for tr, te in skf.split(X, y):
        clf = _fit_lr(X[tr], y[tr])
        proba = clf.predict_proba(X[te])[:, 1]
        pred = (proba >= threshold).astype(int)
        for p, t in zip(pred, y[te]):
            if t == 1 and p == 1: tp += 1
            elif t == 1 and p == 0: fn += 1
            elif t == 0 and p == 1: fp += 1
            else: tn += 1
    n_attack = int((y == 1).sum())
    n_benign = int((y == 0).sum())
    detection = tp / n_attack if n_attack else 0.0
    fpr = fp / n_benign if n_benign else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = 2 * precision * detection / (precision + detection) if (precision + detection) else 0.0
    return {"tier": "learned_lr", "k_folds": k, "threshold": threshold,
            "n_attacks": n_attack, "n_benign": n_benign,
            "detection_rate": round(detection, 4), "false_positive_rate": round(fpr, 4),
            "precision": round(precision, 4), "f1": round(f1, 4),
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "note": "STRATIFIED 5-fold cross-validation (held-out) — NOT train-on-test; honest generalisation estimate"}


def combined_cv_eval(k: int = 5, *, threshold: float = _DEFAULT_THRESHOLD) -> dict[str, Any]:
    """Held-out CV of the REAL combined detector (heuristic must-catch OR the learned tier). Honest end-to-end lift
    vs. the Stage-20 heuristic+kNN — the classifier is trained on train folds and scored on the held-out fold."""
    import numpy as np
    from sklearn.model_selection import StratifiedKFold
    from security.prompt_guard import _heuristic
    prompts, labels = _load_corpus()
    y = np.array(labels)
    model = _embedder()
    X = np.asarray(model.encode(prompts, normalize_embeddings=True))
    heur = np.array([1 if _heuristic(p)[0] else 0 for p in prompts])
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    tp = fp = tn = fn = 0
    for tr, te in skf.split(X, y):
        clf = _fit_lr(X[tr], y[tr])
        proba = clf.predict_proba(X[te])[:, 1]
        for j, idx in enumerate(te):
            blocked = 1 if (heur[idx] == 1 or proba[j] >= threshold) else 0   # combined detector = heuristic OR learned
            t = int(y[idx])
            if t == 1 and blocked: tp += 1
            elif t == 1 and not blocked: fn += 1
            elif t == 0 and blocked: fp += 1
            else: tn += 1
    n_attack = int((y == 1).sum()); n_benign = int((y == 0).sum())
    return {"tier": "combined_heuristic_or_learned", "k_folds": k,
            "n_attacks": n_attack, "n_benign": n_benign,
            "detection_rate": round(tp / n_attack if n_attack else 0.0, 4),
            "false_positive_rate": round(fp / n_benign if n_benign else 0.0, 4),
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "baseline_stage20": {"detection_rate": 0.9935, "false_positive_rate": 0.0156},
            "note": "held-out 5-fold CV of the combined detector (heuristic OR learned); classifier never train-on-test"}


def fit_and_save(out: Optional[Path] = None) -> Path:
    """Fit the FINAL classifier on ALL corpus data and save the deployment artefact."""
    import joblib
    import numpy as np
    out = out or _MODEL_PATH
    prompts, labels = _load_corpus()
    model = _embedder()
    X = np.asarray(model.encode(prompts, normalize_embeddings=True))
    clf = _fit_lr(X, np.array(labels))
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, out)
    return out


_default: Optional[InjectionClassifier] = None


def get_injection_classifier() -> InjectionClassifier:
    global _default
    if _default is None:
        _default = InjectionClassifier()
    return _default


__all__ = ["InjectionClassifier", "get_injection_classifier", "cross_val_eval", "fit_and_save"]
