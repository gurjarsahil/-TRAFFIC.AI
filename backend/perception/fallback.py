"""
CPU Fallback Detector — Simplified vehicle detection using OpenCV
when YOLO/GPU is unavailable. Uses background subtraction for basic
motion/vehicle estimation.
"""
import logging
import time

logger = logging.getLogger(__name__)


class FallbackDetector:
    """
    Lightweight CPU-only detector using OpenCV background subtraction.
    Used when YOLO model fails to load or in extreme resource-constrained mode.
    """

    def __init__(self, config):
        self.config = config
        self._bg_subtractor = None
        self._loaded = False
        self._cache = {}
        self._cache_time = 0

    def load(self):
        """Initialize OpenCV background subtractor."""
        try:
            import cv2
            self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=50, detectShadows=True
            )
            self._loaded = True
            logger.info("✅ Fallback detector initialized (OpenCV MOG2)")
        except ImportError:
            logger.warning("⚠️  OpenCV not available for fallback detection")
            self._loaded = False

    def detect(self, frame):
        """
        Estimate vehicle presence using background subtraction.

        Returns:
            dict with estimated vehicle_count and density
        """
        if time.time() - self._cache_time < self.config.CACHE_TTL_SEC and self._cache:
            return self._cache

        if not self._loaded or self._bg_subtractor is None:
            return self._empty_result()

        start = time.time()
        try:
            import cv2
            import numpy as np

            # Apply background subtraction
            fg_mask = self._bg_subtractor.apply(frame)

            # Threshold and clean
            _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

            # Find contours (approximate vehicle blobs)
            contours, _ = cv2.findContours(
                cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            # Filter by area (rough vehicle-sized blobs)
            min_area = 800
            max_area = 50000
            vehicle_contours = [
                c for c in contours
                if min_area < cv2.contourArea(c) < max_area
            ]

            vehicle_count = len(vehicle_contours)
            density = min(vehicle_count / self.config.MAX_DENSITY, 1.0)
            inference_ms = (time.time() - start) * 1000

            # Generate approximate bounding boxes
            boxes = []
            for c in vehicle_contours[:20]:  # Limit to 20
                x, y, w, h = cv2.boundingRect(c)
                boxes.append([x, y, x + w, y + h, 0.5, -1])  # -1 = unknown class

            result = {
                "vehicle_count": vehicle_count,
                "bounding_boxes": boxes,
                "density_estimate": round(density, 4),
                "inference_time_ms": round(inference_ms, 2),
                "device": "cpu-fallback",
            }
            self._cache = result
            self._cache_time = time.time()
            return result

        except Exception as e:
            logger.error(f"Fallback detection error: {e}")
            return self._empty_result()

    def _empty_result(self):
        return {
            "vehicle_count": 0,
            "bounding_boxes": [],
            "density_estimate": 0.0,
            "inference_time_ms": 0.0,
            "device": "cpu-fallback",
        }

    @property
    def is_loaded(self):
        return self._loaded
