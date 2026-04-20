"""
Linear Trend Projection — Extended to 45-minute horizon.
"""
import numpy as np
from config import Config

class LinearTrendPredictor:
    def __init__(self, window=None):
        self.window = window or Config.TREND_WINDOW

    def predict(self, history, steps=None):
        steps = steps or Config.PREDICTION_HORIZON
        h = history[-self.window:] if len(history) >= 2 else history
        if len(h) < 2:
            return [h[0] if h else 0.0] * steps
        x = np.arange(len(h))
        y = np.array(h)
        coeffs = np.polyfit(x, y, 1)
        slope, intercept = coeffs
        predictions = []
        for i in range(1, steps + 1):
            val = slope * (len(h) - 1 + i) + intercept
            predictions.append(round(float(np.clip(val, 0.0, 1.0)), 4))
        return predictions

    def get_trend_direction(self, history):
        h = history[-self.window:] if len(history) >= 3 else history
        if len(h) < 3:
            return "stable"
        x = np.arange(len(h))
        y = np.array(h)
        slope = np.polyfit(x, y, 1)[0]
        if slope > 0.02:
            return "rising"
        elif slope < -0.02:
            return "falling"
        return "stable"
