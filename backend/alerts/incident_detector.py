"""
Incident Detection — Detects sudden traffic anomalies.
Triggers: density spike + speed drop → alert
"""
import time
from config import Config

class IncidentDetector:
    """Detects potential traffic incidents from sudden metric changes."""

    def __init__(self):
        self.density_threshold = Config.DENSITY_SPIKE_THRESHOLD
        self.speed_threshold = Config.SPEED_DROP_THRESHOLD
        self.min_confidence = Config.INCIDENT_CONFIDENCE_MIN
        self._previous = {}  # node_id -> prev values
        self.active_incidents = {}  # node_id -> incident info

    def check(self, node_id, speed_norm, density_norm, node_name=""):
        """
        Check a single node for incident conditions.

        Returns incident dict if detected, None otherwise.
        """
        prev = self._previous.get(node_id, {
            "speed_norm": speed_norm,
            "density_norm": density_norm,
        })

        speed_drop = prev["speed_norm"] - speed_norm
        density_spike = density_norm - prev["density_norm"]

        # Update previous values
        self._previous[node_id] = {
            "speed_norm": speed_norm,
            "density_norm": density_norm,
        }

        # Check incident conditions
        is_incident = (
            density_norm > self.density_threshold
            and speed_norm < self.speed_threshold
        )

        # Also check sudden changes
        is_sudden = speed_drop > 0.3 and density_spike > 0.2

        if is_incident or is_sudden:
            confidence = self._calc_confidence(
                speed_norm, density_norm, speed_drop, density_spike
            )
            if confidence >= self.min_confidence:
                incident = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "type": "sudden_change" if is_sudden else "congestion_spike",
                    "severity": self._severity(confidence),
                    "confidence": round(confidence, 2),
                    "speed_norm": round(speed_norm, 4),
                    "density_norm": round(density_norm, 4),
                    "speed_drop": round(speed_drop, 4),
                    "density_spike": round(density_spike, 4),
                    "timestamp": time.time(),
                    "message": self._build_message(
                        node_name, node_id, is_sudden, confidence
                    ),
                }
                self.active_incidents[node_id] = incident
                return incident

        # Clear old incidents if conditions normalize
        if node_id in self.active_incidents:
            if speed_norm > 0.5 and density_norm < 0.5:
                del self.active_incidents[node_id]

        return None

    def check_all(self, ci_results, road_network):
        """Check all nodes and return list of incidents."""
        incidents = []
        for nid, data in ci_results.items():
            node = road_network.get_node(nid)
            result = self.check(
                nid, data["speed_norm"], data["density_norm"], node["name"]
            )
            if result:
                incidents.append(result)
        return incidents

    def _calc_confidence(self, speed, density, speed_drop, density_spike):
        """Calculate incident confidence score."""
        base = 0.5
        if speed < 0.2:
            base += 0.2
        if density > 0.8:
            base += 0.15
        if speed_drop > 0.4:
            base += 0.1
        if density_spike > 0.3:
            base += 0.1
        return min(base, 1.0)

    def _severity(self, confidence):
        if confidence > 0.85:
            return "critical"
        elif confidence > 0.7:
            return "high"
        return "moderate"

    def _build_message(self, name, nid, is_sudden, confidence):
        kind = "Sudden traffic anomaly" if is_sudden else "Traffic congestion spike"
        return f"🚨 {kind} detected at {name} ({nid}) — Confidence: {confidence:.0%}"

    def get_active_incidents(self):
        return list(self.active_incidents.values())
