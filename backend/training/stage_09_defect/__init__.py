"""Stage 9 — defect classification (Quality & Inspection, G-016) training package.

Contents:
- dataset.py : load the REAL NEU surface-defect classification set (`newguyme/neu_cls`, 6 classes)
               via HuggingFace datasets; cache, resize to grayscale 64x64, stratified split.
- train.py   : train a small CNN classifier -> models/defect_classifier.{pt,metrics.json}.

Free-cost: torch CPU + torchvision + a small public CC dataset. The companion robot/object
detector (real YOLOv8n) lives in backend/ml/vision_model.py (de-mocked in Stage 9).
"""
