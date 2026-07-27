"""
Vision Model for Robot / Object Detection (Stage 9).
Real YOLOv8 inference from video frames — honest about unavailability.

De-mocked 2026-06-13 (Stage 9): the previous fabricated-detection fallback (random boxes
when ultralytics/weights were absent) is removed — `detect()` now raises
`ModelUnavailableError` (mirrors `failure_predictor` / `world_model`), NEVER fabricating
detections. The real pretrained YOLOv8n (`backend/yolov8n.pt`) provides genuine inference.
Quality & Inspection defect classification (G-016) is the companion
`backend/ml/defect_classifier.py`.
"""

import asyncio
from typing import Optional
from pathlib import Path

import numpy as np
import structlog

from ml.failure_predictor import ModelUnavailableError  # reuse the honest-unavailable contract

logger = structlog.get_logger(__name__)


class VisionModel:
    """
    YOLOv8-based robot detection model.
    
    Detects robots from video frames and extracts:
    - Robot ID (tracked across frames)
    - Position (x, y coordinates)
    - Bounding box
    - Confidence score
    """
    
    def __init__(self, model_path: str = "yolov8n.pt"):
        self.model_path = model_path
        self.model = None
        self.is_loaded = False
        self.confidence_threshold = 0.5
        self.iou_threshold = 0.45
        self.device = "cpu"  # Use CPU for Cloud Run compatibility
        
        # Robot tracker for ID persistence
        self._tracker = {}
        self._next_robot_id = 1
        self._max_distance_threshold = 50  # pixels
    
    def _resolve_weights(self) -> Optional[Path]:
        """Find the YOLO weights: the configured path, else the in-repo yolov8n.pt."""
        candidates = [Path(self.model_path)]
        here = Path(__file__).resolve()
        candidates += [here.parents[1] / "yolov8n.pt", here.parents[2] / "models" / "yolov8n.pt"]
        for c in candidates:
            if c.exists():
                return c
        return None

    def is_available(self) -> bool:
        try:
            self._ensure_loaded()
            return True
        except ModelUnavailableError:
            return False

    def _ensure_loaded(self) -> None:
        """Load ultralytics YOLO + weights, or raise ModelUnavailableError. Never fabricates."""
        if self.model is not None:
            return
        try:
            from ultralytics import YOLO
        except Exception as e:  # pragma: no cover - environment dependent
            raise ModelUnavailableError(f"ultralytics not available: {e}")
        weights = self._resolve_weights()
        if weights is None:
            raise ModelUnavailableError(
                f"YOLO weights not found (looked for {self.model_path} + in-repo yolov8n.pt). "
                "No fabricated detections — provide weights or install the pretrained model."
            )
        self.model = YOLO(str(weights))
        self.is_loaded = True
        logger.info("Vision model loaded", weights=str(weights))

    async def load(self) -> None:
        """Async-compat load. Does not raise on absence (sets availability); `detect` is the
        honest gate. Callers that need the gate up-front can use `is_available()`."""
        try:
            self._ensure_loaded()
        except ModelUnavailableError as e:
            logger.warning("vision model unavailable", error=str(e))

    async def detect(self, frame: np.ndarray) -> list[dict]:
        """Detect objects in a frame via real YOLOv8 inference.

        Returns a list of detections (id, position, confidence, bounding_box, class_id).
        Raises ``ModelUnavailableError`` if ultralytics/weights are absent — NEVER fabricates.
        """
        self._ensure_loaded()
        results = await asyncio.to_thread(
            self.model.predict,
            frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
        )
        detections = []
        for result in results:
            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                center_x = (xyxy[0] + xyxy[2]) / 2
                center_y = (xyxy[1] + xyxy[3]) / 2
                robot_id = self._track_robot(center_x, center_y)
                detections.append({
                    "robot_id": robot_id,
                    "position": {"x": float(center_x), "y": float(center_y)},
                    "confidence": confidence,
                    "bounding_box": [float(x) for x in xyxy],
                    "class_id": class_id,
                })
        return detections
    
    def _track_robot(self, x: float, y: float) -> int:
        """
        Simple tracking to maintain robot IDs across frames.
        Uses nearest neighbor matching.
        """
        from datetime import datetime
        
        current_time = datetime.utcnow()
        
        # Find closest existing track
        min_distance = float('inf')
        matched_id = None
        
        for robot_id, track in self._tracker.items():
            distance = np.sqrt(
                (track["x"] - x) ** 2 + 
                (track["y"] - y) ** 2
            )
            if distance < min_distance:
                min_distance = distance
                matched_id = robot_id
        
        # If match is close enough, update existing track
        if matched_id is not None and min_distance < self._max_distance_threshold:
            self._tracker[matched_id] = {
                "x": x, 
                "y": y, 
                "last_seen": current_time
            }
            return matched_id
        
        # Create new track
        new_id = self._next_robot_id
        self._next_robot_id += 1
        self._tracker[new_id] = {
            "x": x, 
            "y": y, 
            "last_seen": current_time
        }
        
        # Clean up old tracks (not seen in 5 seconds)
        stale_ids = []
        for robot_id, track in self._tracker.items():
            if (current_time - track["last_seen"]).total_seconds() > 5:
                stale_ids.append(robot_id)
        for robot_id in stale_ids:
            del self._tracker[robot_id]
        
        return new_id

    async def detect_batch(self, frames: list[np.ndarray]) -> list[list[dict]]:
        """Detect objects in multiple frames via real YOLOv8 inference.

        Raises ``ModelUnavailableError`` if ultralytics/weights are absent — NEVER fabricates.
        """
        self._ensure_loaded()
        results = await asyncio.to_thread(
            self.model.predict,
            frames,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
        )
        all_detections = []
        for result in results:
            frame_detections = []
            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0])
                center_x = (xyxy[0] + xyxy[2]) / 2
                center_y = (xyxy[1] + xyxy[3]) / 2
                robot_id = self._track_robot(center_x, center_y)
                frame_detections.append({
                    "robot_id": robot_id,
                    "position": {"x": float(center_x), "y": float(center_y)},
                    "confidence": confidence,
                    "bounding_box": [float(x) for x in xyxy],
                })
            all_detections.append(frame_detections)
        return all_detections

    def set_confidence_threshold(self, threshold: float) -> None:
        """Set the confidence threshold for detections."""
        self.confidence_threshold = max(0.1, min(0.99, threshold))
        logger.info("Confidence threshold updated", threshold=self.confidence_threshold)
    
    def set_iou_threshold(self, threshold: float) -> None:
        """Set the IoU threshold for NMS."""
        self.iou_threshold = max(0.1, min(0.99, threshold))
        logger.info("IoU threshold updated", threshold=self.iou_threshold)
    
    def reset_tracker(self) -> None:
        """Reset the robot tracker."""
        self._tracker.clear()
        self._next_robot_id = 1
        logger.info("Robot tracker reset")
    
    @property
    def model_info(self) -> dict:
        """Get model information."""
        return {
            "model_path": self.model_path,
            "is_loaded": self.is_loaded,
            "confidence_threshold": self.confidence_threshold,
            "iou_threshold": self.iou_threshold,
            "device": self.device,
            "tracked_robots": len(self._tracker)
        }
