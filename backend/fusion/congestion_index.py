"""
Cross-Modal Fusion Engine — Enhanced with validation logic.
Combines CCTV visual density with GPS/API speed data, detects
false positives and early warnings when sources disagree.
"""
from config import Config


class CongestionIndexCalculator:
    """Fuses speed + density into Congestion Index with cross-modal validation."""

    def __init__(self):
        self.w1 = Config.CONGESTION_W1
        self.w2 = Config.CONGESTION_W2
        self.max_speed = Config.MAX_SPEED_KPH
        self.max_density = Config.MAX_DENSITY
        self.disagree_threshold = Config.CROSSMODAL_DISAGREE_THRESHOLD

    def normalize_speed(self, speed_kph):
        return min(max(speed_kph / self.max_speed, 0.0), 1.0)

    def normalize_density(self, vehicle_count):
        return min(max(vehicle_count / self.max_density, 0.0), 1.0)

    def compute(self, speed_kph, vehicle_count):
        """
        Compute CI with cross-modal validation.
        CI = w1 * density_norm + w2 * (1 - speed_norm)
        """
        s_norm = self.normalize_speed(speed_kph)
        d_norm = self.normalize_density(vehicle_count)

        speed_component = self.w2 * (1.0 - s_norm)
        density_component = self.w1 * d_norm

        ci = speed_component + density_component

        # ── Cross-Modal Validation ─────────────────────────────────
        speed_says_congested = s_norm < 0.4        # Speed < 24 kph
        density_says_congested = d_norm > 0.5      # > 25 vehicles

        validation_flag = None
        validation_type = "consistent"

        if speed_says_congested and not density_says_congested:
            # API says congested but CCTV doesn't see it
            validation_flag = Config.FALSE_POSITIVE_LABEL
            validation_type = "false_positive"
            ci *= 0.75  # Reduce confidence

        elif density_says_congested and not speed_says_congested:
            # CCTV sees blockage but API doesn't reflect it yet
            validation_flag = Config.EARLY_WARNING_LABEL
            validation_type = "early_warning"
            ci *= 1.1   # Boost — trust visual evidence

        ci = round(min(ci, 1.0), 4)

        return {
            "ci": ci,
            "speed_norm": round(s_norm, 4),
            "density_norm": round(d_norm, 4),
            "speed_contribution": round(speed_component, 4),
            "density_contribution": round(density_component, 4),
            "validation_flag": validation_flag,
            "validation_type": validation_type,
            "sources_agree": validation_type == "consistent",
        }

    def compute_batch(self, data_map):
        """Compute CI for all nodes with validation."""
        results = {}
        for node_id, data in data_map.items():
            results[node_id] = self.compute(
                data["speed_kph"], data["density"]
            )
        return results
