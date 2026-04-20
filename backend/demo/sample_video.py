"""
Sample Video Generator — Creates synthetic traffic video frames for demo mode.
Generates animated frames with simulated vehicle movements.
"""
import random
import math
import logging

logger = logging.getLogger(__name__)


class SampleVideoGenerator:
    """Generates synthetic video frames simulating traffic scenes."""

    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self._tick = 0
        self._vehicles = []
        self._init_vehicles(15)

    def _init_vehicles(self, count):
        """Create initial set of moving vehicle rectangles."""
        for _ in range(count):
            self._vehicles.append({
                "x": random.randint(0, self.width),
                "y": random.randint(100, self.height - 100),
                "w": random.randint(30, 60),
                "h": random.randint(20, 35),
                "vx": random.choice([-3, -2, 2, 3, 4]),
                "vy": random.uniform(-0.5, 0.5),
                "color": (
                    random.randint(100, 255),
                    random.randint(100, 255),
                    random.randint(100, 255),
                ),
            })

    def generate_frame(self, density_factor=1.0):
        """
        Generate a synthetic traffic frame.

        Args:
            density_factor: float, multiplier for vehicle count

        Returns:
            numpy array (H, W, 3) BGR image
        """
        try:
            import numpy as np
            import cv2

            # Dark road background
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

            # Draw road
            cv2.rectangle(frame, (0, 100), (self.width, self.height - 100),
                         (40, 40, 40), -1)
            # Lane markings
            for x in range(0, self.width, 40):
                cv2.line(frame, (x, self.height // 2), (x + 20, self.height // 2),
                        (200, 200, 200), 2)

            # Move and draw vehicles
            self._tick += 1
            target_count = int(15 * density_factor)

            while len(self._vehicles) < target_count:
                self._vehicles.append({
                    "x": -50 if random.random() > 0.5 else self.width + 50,
                    "y": random.randint(120, self.height - 120),
                    "w": random.randint(30, 60),
                    "h": random.randint(20, 35),
                    "vx": random.choice([-3, -2, 2, 3, 4]),
                    "vy": random.uniform(-0.3, 0.3),
                    "color": (
                        random.randint(100, 255),
                        random.randint(100, 255),
                        random.randint(100, 255),
                    ),
                })

            while len(self._vehicles) > target_count and len(self._vehicles) > 3:
                self._vehicles.pop()

            for v in self._vehicles:
                v["x"] += v["vx"]
                v["y"] += v["vy"]

                # Wrap around
                if v["x"] > self.width + 100:
                    v["x"] = -50
                elif v["x"] < -100:
                    v["x"] = self.width + 50

                v["y"] = max(110, min(v["y"], self.height - 110))

                # Draw vehicle rectangle
                x1, y1 = int(v["x"]), int(v["y"])
                x2, y2 = x1 + v["w"], y1 + v["h"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), v["color"], -1)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)

            return frame

        except ImportError:
            logger.warning("OpenCV/NumPy not available for frame generation")
            return None

    def get_vehicle_count(self):
        return len(self._vehicles)
