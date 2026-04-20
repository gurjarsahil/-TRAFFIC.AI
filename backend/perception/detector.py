"""
Perception Layer — YOLO-based Vehicle Detection with GPU/CPU Toggle.
Uses pretrained YOLOv8n for real-time inference.
"""
import time
import logging

logger = logging.getLogger(__name__)

class VehicleDetector:
    """
    GPU-accelerated vehicle detection using YOLOv8n.
    Falls back to CPU with reduced frame rate if GPU is unavailable.
    """

    def __init__(self, config):
        self.config = config
        self.model = None
        self.device = config.DEVICE
        self.frame_interval = (
            config.GPU_FRAME_INTERVAL if config.GPU_AVAILABLE
            else config.CPU_FRAME_INTERVAL
        )
        self._frame_count = 0
        self._cache = {}
        self._cache_time = 0
        self._loaded = False

    def load_model(self):
        """Load YOLOv8n model (lazy loading)."""
        if self._loaded:
            return
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.config.YOLO_MODEL)
            if self.device == "cuda":
                self.model.to("cuda")
                logger.info("✅ YOLO model loaded on GPU (CUDA)")
            else:
                logger.info("⚠️  YOLO model loaded on CPU (Lite Mode)")
            self._loaded = True
        except Exception as e:
            logger.warning(f"⚠️  YOLO model failed to load: {e}. Using demo mode.")
            self._loaded = False

    def detect(self, frame, confidence=None, frame_interval=None):
        """
        Run detection on a single frame.

        Args:
            frame: numpy array (H, W, 3) BGR image
            confidence: optional override for detection confidence
            frame_interval: optional override for frame interval

        Returns:
            dict with detection results.
        """
        self._frame_count += 1
        
        # Use provided or default interval
        interval = frame_interval if frame_interval is not None else self.frame_interval
        conf_thresh = confidence if confidence is not None else self.config.DETECTION_CONFIDENCE

        # Skip frames based on interval
        if self._frame_count % interval != 0:
            return self._cache if self._cache else self._empty_result()

        # Check cache TTL (disable if RL is active usually, but keep for safety)
        if time.time() - self._cache_time < self.config.CACHE_TTL_SEC and self._cache and interval > 1:
            return self._cache

        if not self._loaded or self.model is None:
            return self._empty_result()

        start = time.time()
        try:
            results = self.model(
                frame,
                conf=conf_thresh,
                verbose=False,
            )

            boxes = []
            vehicle_count = 0
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    if cls_id in self.config.VEHICLE_CLASSES:
                        vehicle_count += 1
                        coords = box.xyxy[0].tolist()
                        conf = float(box.conf[0])
                        boxes.append(coords + [conf, cls_id])

            inference_ms = (time.time() - start) * 1000
            density = min(vehicle_count / self.config.MAX_DENSITY, 1.0)

            result = {
                "vehicle_count": vehicle_count,
                "bounding_boxes": boxes,
                "density_estimate": round(density, 4),
                "inference_time_ms": round(inference_ms, 2),
                "device": self.device,
            }
            self._cache = result
            self._cache_time = time.time()
            return result

        except Exception as e:
            logger.error(f"Detection error: {e}")
            return self._empty_result()

    def _empty_result(self):
        return {
            "vehicle_count": 0,
            "bounding_boxes": [],
            "density_estimate": 0.0,
            "inference_time_ms": 0.0,
            "device": self.device,
        }

    @property
    def is_loaded(self):
        return self._loaded
