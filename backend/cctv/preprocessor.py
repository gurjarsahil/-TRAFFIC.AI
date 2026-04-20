"""
Frame Preprocessor — Handles diverse real-world video inputs.
Auto-resize, FPS normalization, low-light enhancement.
"""
import math
import logging

logger = logging.getLogger(__name__)


class FramePreprocessor:
    """Normalizes frames from varied camera sources for consistent processing."""

    def __init__(self, target_width=640, target_fps=15):
        self.target_width = target_width
        self.target_fps = target_fps
        self._brightness_history = []

    def get_video_info(self, cap):
        """Extract video metadata from an OpenCV VideoCapture."""
        import cv2
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total / fps if fps > 0 else 0
        return {
            "fps": fps,
            "width": w,
            "height": h,
            "total_frames": total,
            "duration_sec": round(duration, 2),
            "resolution": f"{w}x{h}",
        }

    def compute_skip(self, source_fps):
        """Compute frame skip interval to normalize to target FPS."""
        if source_fps <= 0:
            return 1
        skip = max(1, round(source_fps / self.target_fps))
        return skip

    def resize_frame(self, frame):
        """Resize keeping aspect ratio to target_width."""
        import cv2
        h, w = frame.shape[:2]
        if w <= self.target_width:
            return frame, 1.0
        scale = self.target_width / w
        new_w = self.target_width
        new_h = int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, scale

    def normalize_brightness(self, frame):
        """Auto-enhance low-light frames using CLAHE."""
        import cv2
        import numpy as np

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        self._brightness_history.append(brightness)
        if len(self._brightness_history) > 30:
            self._brightness_history = self._brightness_history[-30:]

        # Only enhance if consistently dark
        if brightness < 80:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        return frame

    def preprocess(self, frame):
        """Full preprocessing pipeline: resize → normalize brightness."""
        frame, scale = self.resize_frame(frame)
        frame = self.normalize_brightness(frame)
        return frame, scale
