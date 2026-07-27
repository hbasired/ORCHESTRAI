"""
Video Processor for Robot Detection
Processes video streams and runs YOLOv8 inference.
"""

import asyncio
from typing import Optional
from datetime import datetime
from pathlib import Path

import numpy as np
import structlog

from config import settings

logger = structlog.get_logger(__name__)


class VideoProcessor:
    """
    Video processor for robot detection from warehouse cameras.
    
    Features:
    - Real-time video capture (2K @ 30fps)
    - Async frame processing with YOLOv8
    - Frame skipping for performance
    - Optional cloud storage upload
    """
    
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.is_running = False
        
        # Configuration
        self.video_source = settings.video_source
        self.frame_skip = settings.video_frame_skip
        self.resolution = settings.video_resolution
        
        # Video capture
        self._capture = None
        self._process_task: Optional[asyncio.Task] = None
        
        # Vision model
        self._vision_model = None
        
        # Statistics
        self._frames_processed = 0
        self._frames_skipped = 0
        self._detection_count = 0
        self._last_fps = 0.0
        
        # Frame buffer for batch processing
        self._frame_buffer = []
        self._buffer_size = 4
    
    async def start(self) -> None:
        """Start the video processor."""
        try:
            import cv2
            from ml.vision_model import VisionModel
            
            # Initialize vision model
            self._vision_model = VisionModel()
            await self._vision_model.load()
            
            # Open video capture
            source = self.video_source
            if source.isdigit():
                source = int(source)
            
            self._capture = cv2.VideoCapture(source)
            
            if not self._capture.isOpened():
                # Honest (Stage 9): no mock mode — the loop emits nothing when there is no capture.
                logger.warning("Could not open video source; no frames will be processed (no fabrication)", source=source)
                self._capture = None
            else:
                # Set resolution
                self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                logger.info("Video capture opened", source=source, resolution=self.resolution)
            
            self.is_running = True
            
            # Start processing loop
            self._process_task = asyncio.create_task(self._process_loop())
            
            logger.info("Video processor started")
            
        except ImportError:
            # Honest (Stage 9): when OpenCV is unavailable we do NOT fabricate detections.
            # Video processing is simply disabled; no fake robot positions are emitted.
            logger.warning("OpenCV not installed — video processing disabled (no fabricated detections)")
            self.is_running = False
        except Exception as e:
            logger.error("Failed to start video processor", error=str(e))
    
    async def _process_loop(self) -> None:
        """Main processing loop for video frames."""
        import cv2
        
        frame_count = 0
        start_time = datetime.utcnow()
        
        while self.is_running:
            try:
                if self._capture is None or not self._capture.isOpened():
                    await asyncio.sleep(1)
                    continue
                
                # Read frame
                ret, frame = await asyncio.to_thread(self._capture.read)
                
                if not ret:
                    logger.warning("Failed to read frame")
                    await asyncio.sleep(0.1)
                    continue
                
                frame_count += 1
                
                # Frame skipping for performance
                if frame_count % self.frame_skip != 0:
                    self._frames_skipped += 1
                    continue
                
                # Add to buffer
                self._frame_buffer.append(frame)
                
                # Process when buffer is full
                if len(self._frame_buffer) >= self._buffer_size:
                    await self._process_batch()
                
                # Calculate FPS
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > 0:
                    self._last_fps = self._frames_processed / elapsed
                
                # Small delay to prevent CPU saturation
                await asyncio.sleep(0.001)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Frame processing error", error=str(e))
                await asyncio.sleep(0.1)
        
        # Process remaining frames
        if self._frame_buffer:
            await self._process_batch()

    # _mock_process_loop REMOVED (Stage 9, 2026-06-13): it fabricated random robot detections
    # when no video source was available. Honest behaviour now: if OpenCV/video is unavailable,
    # video processing is disabled (see start()) — no fabricated detections are ever emitted.

    async def _process_batch(self) -> None:
        """Process a batch of frames."""
        if not self._frame_buffer or not self._vision_model:
            self._frame_buffer.clear()
            return
        
        try:
            # Batch inference
            all_detections = await self._vision_model.detect_batch(self._frame_buffer)
            
            # Use detections from last frame
            if all_detections:
                latest_detections = all_detections[-1]
                await self._update_robot_positions(latest_detections)
                self._detection_count += len(latest_detections)
            
            self._frames_processed += len(self._frame_buffer)
            
        except Exception as e:
            logger.error("Batch processing error", error=str(e))
        finally:
            self._frame_buffer.clear()
    
    async def _update_robot_positions(self, detections: list[dict]) -> None:
        """Update robot positions in state manager."""
        for detection in detections:
            robot_id = detection.get("robot_id")
            if robot_id:
                await self.state_manager.update_robot_state(robot_id, {
                    "position": detection.get("position", {}),
                    "detection_confidence": detection.get("confidence", 0)
                })
    
    async def process_single_frame(self, frame: np.ndarray) -> list[dict]:
        """
        Process a single frame and return detections.
        
        Args:
            frame: BGR image array
            
        Returns:
            List of robot detections
        """
        if not self._vision_model:
            return []
        
        detections = await self._vision_model.detect(frame)
        self._frames_processed += 1
        self._detection_count += len(detections)
        
        return detections
    
    async def stop(self) -> None:
        """Stop the video processor."""
        self.is_running = False
        
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        
        if self._capture:
            self._capture.release()
        
        logger.info("Video processor stopped",
                   frames_processed=self._frames_processed,
                   frames_skipped=self._frames_skipped,
                   detections=self._detection_count)
    
    @property
    def stats(self) -> dict:
        """Get processor statistics."""
        return {
            "is_running": self.is_running,
            "video_source": self.video_source,
            "resolution": self.resolution,
            "frame_skip": self.frame_skip,
            "frames_processed": self._frames_processed,
            "frames_skipped": self._frames_skipped,
            "detection_count": self._detection_count,
            "fps": round(self._last_fps, 2),
            "buffer_size": len(self._frame_buffer)
        }


class VideoRecorder:
    """
    Records video clips for logging and debugging.
    """
    
    def __init__(self, output_dir: str = "./recordings"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._writer = None
        self._is_recording = False
        self._current_file: Optional[Path] = None
    
    def start_recording(self, filename: str = None, fps: int = 30, resolution: tuple = (1920, 1080)) -> str:
        """Start recording video."""
        try:
            import cv2
            
            if filename is None:
                filename = f"recording_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            
            self._current_file = self.output_dir / filename
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self._writer = cv2.VideoWriter(
                str(self._current_file),
                fourcc,
                fps,
                resolution
            )
            
            self._is_recording = True
            logger.info("Started recording", file=str(self._current_file))
            
            return str(self._current_file)
            
        except Exception as e:
            logger.error("Failed to start recording", error=str(e))
            return ""
    
    def write_frame(self, frame: np.ndarray) -> None:
        """Write a frame to the recording."""
        if self._writer and self._is_recording:
            self._writer.write(frame)
    
    def stop_recording(self) -> str:
        """Stop recording and return the file path."""
        if self._writer:
            self._writer.release()
            self._writer = None
        
        self._is_recording = False
        
        file_path = str(self._current_file) if self._current_file else ""
        logger.info("Stopped recording", file=file_path)
        
        return file_path
    
    @property
    def is_recording(self) -> bool:
        return self._is_recording
