"""
Enhanced Explainability Engine — Cause Classification + Confidence Scoring.
Classifies congestion causes: volume, accident, signal delay, propagation ripple.
"""
from config import Config


class Explainer:
    """Generates cause-classified explanations with anomaly flags."""

    CAUSE_TYPES = {
        "high_volume":   {"icon": "🚗", "label": "High Traffic Volume",   "color": "#f59e0b"},
        "sudden_stop":   {"icon": "🚨", "label": "Possible Accident",     "color": "#ef4444"},
        "external_ripple": {"icon": "🌊", "label": "Propagation Ripple", "color": "#8b5cf6"},
        "signal_delay":  {"icon": "🚦", "label": "Signal / Bottleneck",  "color": "#f97316"},
        "normal":        {"icon": "✅", "label": "Normal Flow",           "color": "#22c55e"},
    }

    def classify_cause(self, ci_data, prev_speed_norm=None, propagation_add=0.0):
        """
        Determine the primary cause of congestion.

        Returns: (cause_key, confidence)
        """
        ci = ci_data["ci"]
        d_norm = ci_data["density_norm"]
        s_norm = ci_data["speed_norm"]

        if ci < 0.25:
            return "normal", 0.95

        causes = {}

        # High density = volume-driven congestion
        if d_norm > Config.CAUSE_HIGH_DENSITY_THRESHOLD:
            causes["high_volume"] = 0.4 + d_norm * 0.4

        # Sudden speed drop with moderate density = possible accident
        if prev_speed_norm is not None:
            speed_drop = prev_speed_norm - s_norm
            if speed_drop > Config.CAUSE_SUDDEN_STOP_SPEED_DROP and s_norm < 0.25:
                causes["sudden_stop"] = 0.5 + speed_drop * 0.5

        # External propagation influence
        if propagation_add > Config.CAUSE_PROPAGATION_ADDITION:
            causes["external_ripple"] = 0.3 + min(propagation_add * 2, 0.5)

        # Signal/bottleneck: moderate CI without clear cause
        if d_norm < 0.5 and s_norm < 0.5 and not causes:
            causes["signal_delay"] = 0.4

        if not causes:
            causes["high_volume"] = 0.5  # Default

        # Pick top cause
        primary = max(causes, key=causes.get)
        confidence = min(causes[primary], 0.98)

        return primary, round(confidence, 2)

    def explain_congestion(self, node_id, node_name, ci_data, prediction,
                           propagation_effects, prev_speed=None, propagation_add=0.0):
        """Generate full explanation with cause classification."""
        ci = ci_data["ci"]
        speed_pct = round(ci_data["speed_contribution"] / max(ci, 0.001) * 100, 1) if ci > 0.01 else 0
        density_pct = round(ci_data["density_contribution"] / max(ci, 0.001) * 100, 1) if ci > 0.01 else 0

        # Severity
        if ci < 0.25:
            severity, color = "Low", "#22c55e"
        elif ci < 0.5:
            severity, color = "Moderate", "#f59e0b"
        elif ci < 0.75:
            severity, color = "High", "#f97316"
        else:
            severity, color = "Critical", "#ef4444"

        # Cause classification
        cause_key, cause_confidence = self.classify_cause(
            ci_data, prev_speed, propagation_add
        )
        cause_info = self.CAUSE_TYPES[cause_key]

        # Prediction trend
        if prediction and len(prediction) >= 2:
            if prediction[-1] > prediction[0] + 0.05:
                trend = "rising"
            elif prediction[-1] < prediction[0] - 0.05:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Anomaly flag
        anomaly_flag = cause_key in ("sudden_stop",)
        cross_modal = ci_data.get("validation_flag")

        # Narrative
        narrative = f"**{node_name}** ({node_id}) — {severity} ({ci:.2f})\n"
        narrative += f"  • Primary cause: {cause_info['icon']} {cause_info['label']}\n"
        narrative += f"  • Speed factor: {speed_pct:.0f}%  |  Density factor: {density_pct:.0f}%\n"
        narrative += f"  • Trend: {trend.capitalize()} over next {len(prediction)*5} min\n"
        if cross_modal:
            narrative += f"  • Cross-modal: {cross_modal}\n"
        if anomaly_flag:
            narrative += f"  • ⚠️ ANOMALY: Possible incident detected\n"

        # Confidence (sources agreement boosts it)
        confidence = self._compute_confidence(ci_data, prediction, cause_confidence)

        return {
            "node_id": node_id,
            "node_name": node_name,
            "severity": severity,
            "severity_color": color,
            "congestion_index": ci,
            "cause": {
                "key": cause_key,
                "label": cause_info["label"],
                "icon": cause_info["icon"],
                "color": cause_info["color"],
                "confidence": cause_confidence,
            },
            "contribution_breakdown": {
                "speed_pct": speed_pct,
                "density_pct": density_pct,
                "speed_component": ci_data["speed_contribution"],
                "density_component": ci_data["density_contribution"],
            },
            "prediction_trend": trend,
            "prediction_values": prediction,
            "prediction_confidence": confidence,
            "anomaly_flag": anomaly_flag,
            "cross_modal_flag": cross_modal,
            "validation_type": ci_data.get("validation_type", "consistent"),
            "narrative": narrative,
        }

    def _compute_confidence(self, ci_data, prediction, cause_conf):
        sources_agree = ci_data.get("sources_agree", True)
        base = 0.85 if sources_agree else 0.55
        base = (base + cause_conf) / 2
        if prediction and len(prediction) > 6:
            base *= 0.92
        return round(base, 2)

    def explain_all(self, road_network, ci_results, predictions,
                    propagation_report, prev_speeds=None, propagation_adds=None):
        """Generate explanations for all nodes."""
        prev_speeds = prev_speeds or {}
        propagation_adds = propagation_adds or {}
        explanations = {}
        for nid, ci_data in ci_results.items():
            node_data = road_network.get_node(nid)
            pred = predictions.get(nid, [])
            p_add = propagation_adds.get(nid, 0.0)
            prev_s = prev_speeds.get(nid)
            explanations[nid] = self.explain_congestion(
                nid, node_data["name"], ci_data, pred,
                propagation_report, prev_s, p_add
            )
        return explanations
