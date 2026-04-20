"""
Smart Alert System — Generates predictive alerts based on forecasted congestion.
"High probability congestion in 20 mins at Node X"
"""
import time
from config import Config


class SmartAlertEngine:
    """Scans predictions and generates forward-looking alerts."""

    def __init__(self):
        self.threshold = Config.ALERT_PREDICTION_THRESHOLD
        self.lookahead = Config.ALERT_LOOKAHEAD_STEPS
        self.max_alerts = Config.MAX_ACTIVE_ALERTS
        self.active_alerts = {}   # node_id -> alert
        self._alert_id_counter = 0

    def scan(self, predictions, road_network, explanations):
        """
        Scan predictions for upcoming congestion events.

        Args:
            predictions: {node_id: [ci_t+1, ci_t+2, ...]}
            road_network: RoadNetwork instance
            explanations: {node_id: explanation_dict}

        Returns: list of new alerts generated this cycle
        """
        new_alerts = []

        for nid, pred_values in predictions.items():
            scan_window = pred_values[:self.lookahead]
            if not scan_window:
                continue

            # Check if any predicted step exceeds threshold
            for step_idx, pred_ci in enumerate(scan_window):
                if pred_ci >= self.threshold:
                    minutes_ahead = (step_idx + 1) * Config.PREDICTION_STEP_MINUTES
                    node = road_network.get_node(nid)
                    current_ci = node.get("congestion_index", 0)

                    # Don't alert if already congested
                    if current_ci >= self.threshold:
                        break

                    # Don't duplicate existing alert
                    if nid in self.active_alerts:
                        existing = self.active_alerts[nid]
                        if time.time() - existing["timestamp"] < 120:
                            break

                    exp = explanations.get(nid, {})
                    cause = exp.get("cause", {})

                    self._alert_id_counter += 1
                    alert = {
                        "id": f"SA-{self._alert_id_counter:04d}",
                        "node_id": nid,
                        "node_name": node.get("name", nid),
                        "type": "predictive",
                        "severity": self._severity(pred_ci),
                        "predicted_ci": round(pred_ci, 3),
                        "current_ci": round(current_ci, 3),
                        "minutes_ahead": minutes_ahead,
                        "cause": cause.get("label", "Traffic Volume"),
                        "cause_icon": cause.get("icon", "🚗"),
                        "confidence": round(min(0.5 + pred_ci * 0.4, 0.95), 2),
                        "message": (
                            f"⚡ High probability congestion in {minutes_ahead} min "
                            f"at {node.get('name', nid)} — "
                            f"Predicted CI: {pred_ci:.2f}"
                        ),
                        "timestamp": time.time(),
                    }

                    self.active_alerts[nid] = alert
                    new_alerts.append(alert)
                    break  # One alert per node per scan

        # Prune stale alerts (> 5 minutes without re-trigger)
        stale = [
            nid for nid, a in self.active_alerts.items()
            if time.time() - a["timestamp"] > 300
        ]
        for nid in stale:
            del self.active_alerts[nid]

        # Cap total alerts
        if len(self.active_alerts) > self.max_alerts:
            sorted_alerts = sorted(
                self.active_alerts.items(),
                key=lambda x: x[1]["predicted_ci"],
                reverse=True
            )
            self.active_alerts = dict(sorted_alerts[:self.max_alerts])

        return new_alerts

    def _severity(self, ci):
        if ci >= 0.85:
            return "critical"
        elif ci >= 0.7:
            return "high"
        return "moderate"

    def get_active_alerts(self):
        return list(self.active_alerts.values())

    def clear_alert(self, node_id):
        if node_id in self.active_alerts:
            del self.active_alerts[node_id]
