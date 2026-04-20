"""
Async Processing Pipeline v2 — Orchestrates all enhanced system layers.
Integrates: cross-modal validation, cause classification, smart alerts,
CCTV frame data, anomaly detection, and prev-speed tracking.
"""
import asyncio
import time
import logging
import json

from config import Config
from propagation.road_graph import RoadNetwork
from ingestion.gps_simulator import GPSSimulator
from ingestion.data_sources import DataSourceManager
from fusion.congestion_index import CongestionIndexCalculator
from prediction.ema import EMAPredictor
from prediction.linear_trend import LinearTrendPredictor
from propagation.spread_engine import SpreadEngine
from explainability.explainer import Explainer
from alerts.incident_detector import IncidentDetector
from alerts.smart_alerts import SmartAlertEngine
from demo.demo_data import DemoDataGenerator

logger = logging.getLogger(__name__)


class TrafficPipeline:
    """
    Production pipeline v2:
    1. Data Ingestion (GPS + DL density)
    2. Cross-Modal Data Fusion (CI + validation)
    3. Prediction (EMA + Linear Trend, 45-min horizon)
    4. Graph Propagation (congestion spread)
    5. Cause Classification
    6. Incident Detection + Smart Alerts
    7. Explainability
    8. CCTV Frame Generation
    """

    def __init__(self):
        self.road_network = RoadNetwork()
        self.gps_sim = GPSSimulator(self.road_network, Config.MAX_SPEED_KPH)
        self.data_sources = DataSourceManager(self.gps_sim)
        self.ci_calculator = CongestionIndexCalculator()
        self.ema = EMAPredictor()
        self.linear = LinearTrendPredictor()
        self.spread_engine = SpreadEngine(self.road_network)
        self.explainer = Explainer()
        self.incident_detector = IncidentDetector()
        self.smart_alerts = SmartAlertEngine()
        self.demo_gen = DemoDataGenerator(self.road_network)

        # State tracking
        self._running = False
        self._tick = 0
        self._last_result = None
        self._subscribers = []
        self._prev_speeds = {}       # Previous speed_norm per node
        self._cctv_active_node = "N10"  # Default CCTV camera node

        self.mode = Config.MODE
        self.demo_mode = Config.DEMO_MODE

        logger.info(f"Pipeline v2 | Mode: {self.mode} | Demo: {self.demo_mode}")

    async def start(self):
        self._running = True
        logger.info("🚀 Pipeline v2 started")
        while self._running:
            try:
                result = await self._process_cycle()
                self._last_result = result
                await self._broadcast(result)
            except Exception as e:
                logger.error(f"Pipeline error: {e}", exc_info=True)
            await asyncio.sleep(Config.PIPELINE_INTERVAL_SEC)

    async def stop(self):
        self._running = False

    async def _process_cycle(self):
        self._tick += 1
        t0 = time.time()

        # ─── 1. Data Ingestion ─────────────────────────────────────
        self.data_sources.tick()
        raw_data = self.data_sources.get_all_data()

        if self.demo_mode:
            self.demo_gen.tick()
            densities = self.demo_gen.generate_densities()
            for nid in raw_data:
                raw_data[nid]["density"] = densities.get(nid, 0)

        # ─── 2. Cross-Modal Fusion ─────────────────────────────────
        ci_results = self.ci_calculator.compute_batch(raw_data)

        # Count cross-modal flags
        false_positives = sum(
            1 for v in ci_results.values() if v["validation_type"] == "false_positive"
        )
        early_warnings = sum(
            1 for v in ci_results.values() if v["validation_type"] == "early_warning"
        )

        # ─── 3. Update Network ─────────────────────────────────────
        for nid, ci_data in ci_results.items():
            node = self.road_network.get_node(nid)
            history = node.get("history", [])
            history.append(ci_data["ci"])
            if len(history) > Config.HISTORY_BUFFER_SIZE:
                history = history[-Config.HISTORY_BUFFER_SIZE:]

            self.road_network.update_node(
                nid,
                congestion_index=ci_data["ci"],
                speed_norm=ci_data["speed_norm"],
                density_norm=ci_data["density_norm"],
                vehicle_count=raw_data[nid]["density"],
                history=history,
                validation_type=ci_data["validation_type"],
            )

        # ─── 4. Prediction (CPU) ──────────────────────────────────
        ci_values = {nid: d["ci"] for nid, d in ci_results.items()}
        self.ema.update_batch(ci_values)

        predictions = {}
        for nid in ci_values:
            ema_pred = self.ema.predict(nid)
            node = self.road_network.get_node(nid)
            history = node.get("history", [])
            linear_pred = self.linear.predict(history)

            combined = []
            for i in range(len(ema_pred)):
                lp = linear_pred[i] if i < len(linear_pred) else ema_pred[i]
                avg = (ema_pred[i] + lp) / 2.0
                combined.append(round(avg, 4))
            predictions[nid] = combined

            self.road_network.update_node(
                nid, predicted_ci=combined[0] if combined else 0
            )
            trend = self.linear.get_trend_direction(history)
            self.road_network.graph.nodes[nid]["trend"] = trend

        # ─── 5. Propagation ────────────────────────────────────────
        propagation_effects = self.spread_engine.propagate()
        propagation_report = self.spread_engine.get_propagation_report()

        for nid, added in propagation_effects.items():
            node = self.road_network.get_node(nid)
            new_ci = min(1.0, node["congestion_index"] + added * 0.3)
            self.road_network.update_node(nid, congestion_index=new_ci)

        future_spread = self.spread_engine.simulate_future(steps=9)

        # ─── 6. Incidents ──────────────────────────────────────────
        incidents = self.incident_detector.check_all(ci_results, self.road_network)

        # ─── 7. Explainability + Cause Classification ──────────────
        explanations = self.explainer.explain_all(
            self.road_network, ci_results, predictions,
            propagation_report,
            prev_speeds=self._prev_speeds,
            propagation_adds=propagation_effects,
        )

        # Store current speeds for next cycle's cause classification
        self._prev_speeds = {
            nid: d["speed_norm"] for nid, d in ci_results.items()
        }

        # ─── 8. Smart Alerts ──────────────────────────────────────
        new_smart_alerts = self.smart_alerts.scan(
            predictions, self.road_network, explanations
        )

        # ─── 9. CCTV Frame Data ───────────────────────────────────
        cctv_frame = None
        if self.demo_mode:
            cctv_frame = self.demo_gen.generate_cctv_frame(self._cctv_active_node)

        # ─── Build Payload ─────────────────────────────────────────
        cycle_ms = (time.time() - t0) * 1000

        result = {
            "tick": self._tick,
            "timestamp": time.time(),
            "cycle_time_ms": round(cycle_ms, 2),
            "mode": self.mode,
            "demo_mode": self.demo_mode,
            "network": self.road_network.to_serializable(),
            "predictions": predictions,
            "future_spread": future_spread,
            "incidents": incidents,
            "active_incidents": self.incident_detector.get_active_incidents(),
            "smart_alerts": self.smart_alerts.get_active_alerts(),
            "new_smart_alerts": new_smart_alerts,
            "cctv_frame": cctv_frame,
            "explanations": {
                nid: {
                    "severity": e["severity"],
                    "severity_color": e["severity_color"],
                    "narrative": e["narrative"],
                    "contribution_breakdown": e["contribution_breakdown"],
                    "prediction_trend": e["prediction_trend"],
                    "prediction_confidence": e["prediction_confidence"],
                    "cause": e["cause"],
                    "anomaly_flag": e["anomaly_flag"],
                    "cross_modal_flag": e.get("cross_modal_flag"),
                    "validation_type": e.get("validation_type", "consistent"),
                }
                for nid, e in explanations.items()
            },
            "system": {
                "device": Config.DEVICE,
                "gpu_available": Config.GPU_AVAILABLE,
                "total_nodes": len(ci_results),
                "congested_nodes": sum(1 for v in ci_results.values() if v["ci"] > 0.5),
                "false_positives": false_positives,
                "early_warnings": early_warnings,
                "active_alert_count": len(self.smart_alerts.get_active_alerts()),
                "prediction_horizon": f"{Config.PREDICTION_HORIZON * Config.PREDICTION_STEP_MINUTES}min",
            },
        }
        return result

    def subscribe(self, ws):
        self._subscribers.append(ws)

    def unsubscribe(self, ws):
        if ws in self._subscribers:
            self._subscribers.remove(ws)

    async def _broadcast(self, data):
        if not self._subscribers:
            return
        message = json.dumps(data, default=str)
        disconnected = []
        for ws in self._subscribers:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.unsubscribe(ws)

    def get_last_result(self):
        return self._last_result

    def simulate_blockage(self, node_id, duration=10):
        if self.demo_mode:
            return self.demo_gen.simulate_blockage(node_id, duration)
        return {"error": "Demo mode only"}

    def set_mode(self, mode):
        if mode in ("GPU", "LITE"):
            self.mode = mode
            Config.MODE = mode
            return {"status": "ok", "mode": mode}
        return {"error": "Invalid mode"}

    def set_cctv_node(self, node_id):
        """Switch CCTV camera to a different node."""
        try:
            self.road_network.get_node(node_id)
            self._cctv_active_node = node_id
            return {"status": "ok", "cctv_node": node_id}
        except KeyError:
            return {"error": "Node not found"}
