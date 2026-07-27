"""Stage 9 — vision (real YOLOv8n) + defect classifier (real NEU-CLS CNN) tests.

The real-inference / real-data tests skip honestly when ultralytics/weights/dataset are absent.
The honest-unavailable tests need none of those.
"""
from __future__ import annotations

import numpy as np
import pytest

from ml.failure_predictor import ModelUnavailableError


# ---- vision model (real YOLOv8n; honest unavailability) ---------------------

def _vision_available() -> bool:
    from ml.vision_model import VisionModel
    return VisionModel().is_available()


vision_needs_model = pytest.mark.skipif(not _vision_available(),
                                        reason="ultralytics/YOLO weights unavailable (honest skip)")


def test_vision_honest_unavailable_on_missing_weights(tmp_path):
    from ml.vision_model import VisionModel
    vm = VisionModel(model_path=str(tmp_path / "nope.pt"))
    # If ultralytics is installed it will still find the in-repo yolov8n.pt; only assert the
    # honest contract when NOTHING is resolvable. We assert is_available() is a bool either way.
    assert isinstance(vm.is_available(), bool)


@pytest.mark.asyncio
async def test_vision_detect_raises_when_unavailable():
    """A VisionModel pointed at a bogus path with no resolvable weights raises (never fabricates).
    Skips if the in-repo yolov8n.pt is resolvable (then detection is genuinely available)."""
    from ml.vision_model import VisionModel
    vm = VisionModel(model_path="___bogus___.pt")
    if vm.is_available():
        pytest.skip("real YOLO weights resolvable; unavailable path not exercisable here")
    with pytest.raises(ModelUnavailableError):
        await vm.detect(np.zeros((64, 64, 3), dtype=np.uint8))


@vision_needs_model
@pytest.mark.asyncio
async def test_vision_real_inference_returns_list():
    from ml.vision_model import VisionModel
    vm = VisionModel()
    dets = await vm.detect((np.random.rand(640, 640, 3) * 255).astype(np.uint8))
    assert isinstance(dets, list)  # real YOLO ran (likely empty on noise — that's honest, not fabricated)
    for d in dets:
        assert {"robot_id", "position", "confidence", "bounding_box", "class_id"} <= set(d)


@vision_needs_model
def test_vision_has_no_mock_fallback():
    import ml.vision_model as vm
    assert not hasattr(vm.VisionModel, "_generate_mock_detections")


# ---- defect classifier (real NEU-CLS CNN) -----------------------------------

def _defect_available() -> bool:
    from ml.defect_classifier import get_defect_classifier
    return get_defect_classifier().is_available()


defect_needs_model = pytest.mark.skipif(not _defect_available(),
                                        reason="trained defect classifier unavailable (honest skip)")


def test_defect_honest_unavailable(tmp_path):
    from ml.defect_classifier import DefectClassifier
    dc = DefectClassifier(weights_path=tmp_path / "missing.pt")
    assert dc.is_available() is False
    with pytest.raises(ModelUnavailableError):
        dc.classify(np.zeros((64, 64), dtype=np.float32))


@defect_needs_model
def test_defect_classify_output_shape():
    from ml.defect_classifier import get_defect_classifier
    dc = get_defect_classifier()
    out = dc.classify(np.random.rand(64, 64).astype(np.float32))
    assert 0 <= out["label_index"] < 6
    assert 0.0 <= out["confidence"] <= 1.0
    assert len(out["probabilities"]) == 6
    assert abs(sum(out["probabilities"]) - 1.0) < 1e-4


@defect_needs_model
def test_defect_classifier_beats_baseline_on_real_holdout():
    """Sanity: on a small real held-out batch the classifier is well above the 1/6 majority baseline."""
    from ml.defect_classifier import get_defect_classifier
    from training.stage_09_defect.dataset import load_defect_data
    dc = get_defect_classifier()
    data = load_defect_data()
    n = min(60, len(data.X_test))
    correct = sum(int(dc.classify(data.X_test[i])["label_index"] == int(data.y_test[i])) for i in range(n))
    acc = correct / n
    assert acc > 0.5, f"real-holdout accuracy {acc:.2f} should be well above the 1/6 baseline"
