"""Singleton InsightFace model loader.

Loads the buffalo_l model exactly once at application startup.
Configured for CPU-only inference (ctx_id=-1).
"""

import logging
import os
import threading
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FaceAnalyzerSingleton:
    """Thread-safe singleton for InsightFace FaceAnalysis model.

    The model is loaded lazily on first access and reused for all
    subsequent requests. This avoids the ~2-3s model loading time
    on every request.
    """

    _instance: "FaceAnalyzerSingleton | None" = None
    _lock: threading.Lock = threading.Lock()
    _model: Any = None
    _is_loaded: bool = False

    def __new__(cls) -> "FaceAnalyzerSingleton":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def load_model(
        self,
        model_name: str = "buffalo_l",
        model_root: str = "./models",
        det_size: tuple[int, int] = (640, 640),
    ) -> None:
        """Load the InsightFace model.

        Args:
            model_name: Name of the pretrained model pack.
            model_root: Directory for model storage/download.
            det_size: Detection input size (width, height).

        First run will download ~300MB model to model_root.
        """
        if self._is_loaded:
            logger.info("FaceAnalysis model already loaded, skipping.")
            return

        with self._lock:
            if self._is_loaded:
                return

            # Ensure model directory exists with write permissions
            os.makedirs(model_root, exist_ok=True)

            logger.info(
                "Loading InsightFace model '%s' from '%s' (CPU mode)...",
                model_name,
                model_root,
            )

            from insightface.app import FaceAnalysis

            self._model = FaceAnalysis(
                name=model_name,
                root=model_root,
            )
            # ctx_id=-1 forces CPU inference (no GPU required)
            self._model.prepare(ctx_id=-1, det_size=det_size)

            self._is_loaded = True
            logger.info("InsightFace model loaded successfully (CPU mode).")

    @property
    def model(self) -> Any:
        """Access the loaded model instance.

        Raises:
            RuntimeError: If model has not been loaded yet.
        """
        if not self._is_loaded or self._model is None:
            raise RuntimeError(
                "FaceAnalysis model has not been loaded. Call load_model() first."
            )
        return self._model

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._is_loaded

    def detect_faces(
        self,
        image: np.ndarray,
        min_confidence: float = 0.5,
    ) -> list[Any]:
        """Detect faces in an image and filter by confidence threshold.

        Args:
            image: Input image as a numpy array (BGR format).
            min_confidence: Minimum detection confidence score.

        Returns:
            List of detected face objects above confidence threshold.
        """
        faces = self.model.get(image)
        
        # Debug logging for all detection scores
        for i, face in enumerate(faces):
            logger.debug(f"Face {i} det_score: {face.det_score:.4f}")

        # Filter by detection confidence
        filtered = [f for f in faces if f.det_score >= min_confidence]
        
        logger.info(
            "Detected %d faces (%d above %.2f confidence threshold)",
            len(faces),
            len(filtered),
            min_confidence,
        )
        return filtered

    def get_embedding(self, face: Any) -> np.ndarray:
        """Extract and L2-normalize the embedding from a detected face.

        Args:
            face: A detected face object from InsightFace.

        Returns:
            L2-normalized 512-dim embedding as numpy array.
        """
        # get_embedding already returns face.normed_embedding which is L2-normalized by InsightFace
        return face.normed_embedding


# Global singleton instance
face_analyzer = FaceAnalyzerSingleton()
