"""
Exponential Moving Average Predictor — Extended to 45-minute horizon.
"""
from config import Config

class EMAPredictor:
    """Predicts future congestion using Exponential Moving Average."""

    def __init__(self, alpha=None):
        self.alpha = alpha or Config.EMA_ALPHA
        self._state = {}

    def update(self, node_id, ci_value):
        if node_id not in self._state:
            self._state[node_id] = ci_value
        else:
            self._state[node_id] = (
                self.alpha * ci_value + (1 - self.alpha) * self._state[node_id]
            )
        return self._state[node_id]

    def predict(self, node_id, steps=None):
        steps = steps or Config.PREDICTION_HORIZON
        current = self._state.get(node_id, 0.0)
        predictions = []
        for i in range(1, steps + 1):
            decay = 0.97 ** i
            pred = current * decay + 0.3 * (1 - decay)
            predictions.append(round(pred, 4))
        return predictions

    def get_current(self, node_id):
        return self._state.get(node_id, 0.0)

    def update_batch(self, ci_map):
        for nid, ci in ci_map.items():
            self.update(nid, ci)
