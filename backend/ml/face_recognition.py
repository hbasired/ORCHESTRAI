"""
Face Recognition CNN Model

Simple CNN architecture for face embeddings used for authentication.
Uses OpenCV for face detection and a custom CNN for embedding generation.
"""

import numpy as np
from typing import Optional, Tuple, List
import base64
import io
import structlog

logger = structlog.get_logger(__name__)

# Try to import ML libraries
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available, face recognition disabled")

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available, using fallback face matching")


class FaceRecognitionCNN(nn.Module):
    """
    Simple CNN for generating face embeddings.
    
    Architecture:
    - Input: 160x160x3 RGB face image
    - 3 conv blocks with batch norm and pooling
    - Fully connected layers to 128-dim embedding
    """
    
    def __init__(self, embedding_dim: int = 128):
        super().__init__()
        
        # Convolutional blocks
        self.conv1 = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)  # 160 -> 80
        )
        
        self.conv2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)  # 80 -> 40
        )
        
        self.conv3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)  # 40 -> 20
        )
        
        self.conv4 = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4))  # -> 4x4
        )
        
        # Fully connected layers
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(256 * 4 * 4, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, embedding_dim)
        )
        
        self.embedding_dim = embedding_dim
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Generate 128-dim embedding from face image."""
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        x = self.fc(x)
        # L2 normalize the embedding
        x = F.normalize(x, p=2, dim=1)
        return x


class FaceRecognitionService:
    """
    Face recognition service for user authentication.
    
    Features:
    - Face detection using OpenCV Haar cascades
    - Face embedding using CNN
    - Cosine similarity matching
    - Supabase integration for user storage
    """
    
    FACE_SIZE = (160, 160)
    # Lower threshold for better tolerance with distance/accessories (cap, spectacles)
    SIMILARITY_THRESHOLD = 0.45  # Reduced from 0.75 for better robustness
    
    def __init__(self):
        self.model: Optional[FaceRecognitionCNN] = None
        self.face_cascade = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize face recognition components."""
        try:
            if CV2_AVAILABLE:
                # Load face detector
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                logger.info("Face cascade loaded")
            
            if TORCH_AVAILABLE:
                # Initialize CNN model
                self.model = FaceRecognitionCNN(embedding_dim=128)
                self.model.eval()
                logger.info("Face recognition CNN initialized")
            
            self._initialized = CV2_AVAILABLE or TORCH_AVAILABLE
            return self._initialized
            
        except Exception as e:
            logger.error("Face recognition initialization failed", error=str(e))
            return False
    
    def detect_face(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect and extract face from image.
        
        Args:
            image: BGR image from OpenCV
            
        Returns:
            Cropped face image (160x160 RGB) or None if no face
        """
        if not CV2_AVAILABLE or self.face_cascade is None:
            return None
            
        try:
            # Convert to grayscale for detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Multi-scale face detection for distance tolerance
            # Try with different minSize for near/far detection
            faces = []
            
            # Try larger minimum size first (for close faces)
            for min_size in [(100, 100), (60, 60), (30, 30)]:
                detected = self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=4,  # Slightly lower for better detection
                    minSize=min_size
                )
                if len(detected) > 0:
                    faces = detected
                    break
            
            if len(faces) == 0:
                logger.debug("No face detected in image at any scale")
                return None
            
            # Use the largest face
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            
            # Add margin around face
            margin = int(w * 0.2)
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(image.shape[1] - x, w + 2 * margin)
            h = min(image.shape[0] - y, h + 2 * margin)
            
            # Crop and resize
            face_crop = image[y:y+h, x:x+w]
            face_resized = cv2.resize(face_crop, self.FACE_SIZE)
            face_rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)
            
            return face_rgb
            
        except Exception as e:
            logger.error("Face detection failed", error=str(e))
            return None
    
    def generate_embedding(self, face_image: np.ndarray) -> Optional[List[float]]:
        """
        Generate 128-dim embedding from face image.
        
        Args:
            face_image: 160x160 RGB face image
            
        Returns:
            128-dim embedding as list of floats
        """
        if not TORCH_AVAILABLE or self.model is None:
            # Fallback: use simple pixel average as "embedding"
            return self._fallback_embedding(face_image)
            
        try:
            # Normalize and convert to tensor
            face_norm = face_image.astype(np.float32) / 255.0
            face_tensor = torch.from_numpy(face_norm).permute(2, 0, 1).unsqueeze(0)
            
            # Generate embedding
            with torch.no_grad():
                embedding = self.model(face_tensor)
            
            return embedding.squeeze().tolist()
            
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            return None
    
    def _fallback_embedding(self, face_image: np.ndarray) -> List[float]:
        """
        Fallback embedding when PyTorch not available.
        Uses downsampled image as simple embedding.
        """
        # Resize to 16x16 and flatten
        small = cv2.resize(face_image, (16, 16)) if CV2_AVAILABLE else face_image[::10, ::10]
        flat = small.flatten().astype(np.float32) / 255.0
        # Take first 128 values
        embedding = flat[:128].tolist()
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = [x / norm for x in embedding]
        return embedding
    
    def compare_embeddings(self, emb1: List[float], emb2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Returns:
            Similarity score between -1 and 1 (higher is more similar)
        """
        if len(emb1) != len(emb2):
            return 0.0
            
        v1 = np.array(emb1)
        v2 = np.array(emb2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 * norm2 == 0:
            return 0.0
            
        return float(dot_product / (norm1 * norm2))
    
    def decode_base64_image(self, base64_data: str) -> Optional[np.ndarray]:
        """Decode base64 image to numpy array."""
        try:
            # Remove data URL prefix if present
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            image_bytes = base64.b64decode(base64_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            
            if CV2_AVAILABLE:
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            else:
                # Fallback using PIL
                from PIL import Image
                image = np.array(Image.open(io.BytesIO(image_bytes)))
                if len(image.shape) == 3:
                    image = image[:, :, ::-1]  # RGB to BGR
            
            return image
            
        except Exception as e:
            logger.error("Image decode failed", error=str(e))
            return None
    
    def load_image_file(self, file_path: str) -> Optional[np.ndarray]:
        """Load image from file path."""
        try:
            if CV2_AVAILABLE:
                return cv2.imread(file_path)
            else:
                from PIL import Image
                img = Image.open(file_path)
                return np.array(img)[:, :, ::-1]  # RGB to BGR
        except Exception as e:
            logger.error("Image load failed", path=file_path, error=str(e))
            return None
    
    async def register_face(self, image_data: str) -> Optional[List[float]]:
        """
        Register a new face by generating its embedding.
        
        Args:
            image_data: Base64 encoded image or file path
            
        Returns:
            Face embedding or None if failed
        """
        # Load image
        if image_data.startswith('data:') or len(image_data) > 500:
            image = self.decode_base64_image(image_data)
        else:
            image = self.load_image_file(image_data)
        
        if image is None:
            logger.error("Could not load image for registration")
            return None
        
        # Detect and crop face
        face = self.detect_face(image)
        if face is None:
            logger.error("No face detected in registration image")
            return None
        
        # Generate embedding
        embedding = self.generate_embedding(face)
        if embedding is None:
            logger.error("Could not generate face embedding")
            return None
        
        logger.info("Face registered successfully", embedding_dim=len(embedding))
        return embedding
    
    async def verify_face(self, image_data: str, stored_embedding: List[float]) -> Tuple[bool, float]:
        """
        Verify a face against stored embedding.
        
        Args:
            image_data: Base64 encoded image from camera
            stored_embedding: Previously registered face embedding
            
        Returns:
            (match: bool, similarity: float)
        """
        # Load image
        if image_data.startswith('data:') or len(image_data) > 500:
            image = self.decode_base64_image(image_data)
        else:
            image = self.load_image_file(image_data)
        
        if image is None:
            return False, 0.0
        
        # Detect face
        face = self.detect_face(image)
        if face is None:
            return False, 0.0
        
        # Generate embedding
        current_embedding = self.generate_embedding(face)
        if current_embedding is None:
            return False, 0.0
        
        # Compare
        similarity = self.compare_embeddings(current_embedding, stored_embedding)
        is_match = similarity >= self.SIMILARITY_THRESHOLD
        
        logger.info(
            "Face verification",
            is_match=is_match,
            similarity=round(similarity, 3),
            threshold=self.SIMILARITY_THRESHOLD
        )
        
        return is_match, similarity
    
    async def verify_face_multi(self, image_data: str, stored_embeddings: List[List[float]]) -> Tuple[bool, float]:
        """
        Verify a face against multiple stored embeddings.
        Useful for matching when user has registered multiple face angles/distances.
        
        Args:
            image_data: Base64 encoded image from camera
            stored_embeddings: List of previously registered face embeddings
            
        Returns:
            (match: bool, best_similarity: float)
        """
        if not stored_embeddings:
            return False, 0.0
        
        # Load and process current face
        if image_data.startswith('data:') or len(image_data) > 500:
            image = self.decode_base64_image(image_data)
        else:
            image = self.load_image_file(image_data)
        
        if image is None:
            return False, 0.0
        
        face = self.detect_face(image)
        if face is None:
            return False, 0.0
        
        current_embedding = self.generate_embedding(face)
        if current_embedding is None:
            return False, 0.0
        
        # Compare against all stored embeddings, take the best match
        best_similarity = 0.0
        for stored_emb in stored_embeddings:
            similarity = self.compare_embeddings(current_embedding, stored_emb)
            if similarity > best_similarity:
                best_similarity = similarity
        
        is_match = best_similarity >= self.SIMILARITY_THRESHOLD
        
        logger.info(
            "Face verification (multi-embedding)",
            is_match=is_match,
            best_similarity=round(best_similarity, 3),
            num_embeddings=len(stored_embeddings),
            threshold=self.SIMILARITY_THRESHOLD
        )
        
        return is_match, best_similarity


# Global instance
_face_service: Optional[FaceRecognitionService] = None


async def get_face_service() -> FaceRecognitionService:
    """Get or create global face recognition service."""
    global _face_service
    if _face_service is None:
        _face_service = FaceRecognitionService()
        await _face_service.initialize()
    return _face_service
