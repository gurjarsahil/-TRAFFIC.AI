"""
Demo Data Generator v2 — Generates synthetic densities AND CCTV frame data
(vehicle positions for frontend canvas). Includes anomaly scenarios.
"""
import random
import math
import time

class DemoDataGenerator:
    """Generates synthetic traffic data including CCTV vehicle positions."""

    def __init__(self, road_network):
        self.network = road_network
        self._tick = 0
        self._hotspots = ["N03", "N10", "N12", "N16"]
        self._incident_node = None
        self._incident_tick = 0
        self._stopped_vehicles = {}           # node_id -> list of stopped positions
        self._cctv_vehicles = self._init_vehicles()

    def _init_vehicles(self):
        """Create initial vehicle set for CCTV canvas simulation."""
        vehicles = []
        for i in range(22):
            vehicles.append({
                "id": i,
                "x": random.randint(20, 620),
                "y": random.randint(80, 360),
                "w": random.randint(28, 55),
                "h": random.randint(18, 30),
                "vx": random.choice([-3, -2, -1.5, 1.5, 2, 3, 3.5]),
                "vy": random.uniform(-0.4, 0.4),
                "color": random.choice([
                    "#3b82f6", "#ef4444", "#f59e0b", "#22c55e",
                    "#8b5cf6", "#06b6d4", "#ec4899", "#f97316",
                    "#64748b", "#a855f7", "#14b8a6",
                ]),
                "stopped": False,
                "cls": random.choice(["car", "car", "car", "truck", "bus", "motorcycle"]),
            })
        return vehicles

    def tick(self):
        self._tick += 1

    def generate_densities(self):
        hour = (self._tick % 288) / 12
        rush = self._rush_factor(hour)
        densities = {}
        for nid, data in self.network.get_all_nodes():
            base = random.randint(3, 15)
            if nid in self._hotspots:
                base += random.randint(8, 20)
            base = int(base * rush)
            base += random.randint(-3, 5)
            if nid == self._incident_node:
                remaining = self._incident_tick - self._tick
                if remaining > 0:
                    base = int(base * 2.5)
                else:
                    self._incident_node = None
            densities[nid] = max(0, min(base, 60))

        if not self._incident_node and random.random() < 0.01:
            self._incident_node = random.choice(
                [nid for nid, _ in self.network.get_all_nodes()]
            )
            self._incident_tick = self._tick + random.randint(5, 15)

        return densities

    def generate_cctv_frame(self, active_node_id="N10"):
        """
        Generate CCTV frame data: vehicle positions + bounding boxes
        for real-time canvas rendering in the frontend.

        Returns: dict with vehicles list, anomalies, and frame metadata
        """
        node = self.network.get_node(active_node_id)
        density = node.get("vehicle_count", 15)
        ci = node.get("congestion_index", 0.3)

        # Adjust vehicle count to match density
        target_count = max(5, min(density, 35))
        while len(self._cctv_vehicles) < target_count:
            self._cctv_vehicles.append({
                "id": len(self._cctv_vehicles),
                "x": random.choice([-40, 660]),
                "y": random.randint(80, 360),
                "w": random.randint(28, 55),
                "h": random.randint(18, 30),
                "vx": random.choice([-2.5, -2, 2, 2.5, 3]),
                "vy": random.uniform(-0.3, 0.3),
                "color": random.choice(["#3b82f6", "#ef4444", "#f59e0b", "#22c55e", "#8b5cf6"]),
                "stopped": False,
                "cls": random.choice(["car", "car", "truck", "bus"]),
            })
        while len(self._cctv_vehicles) > target_count and len(self._cctv_vehicles) > 5:
            self._cctv_vehicles.pop()

        anomalies = []
        for v in self._cctv_vehicles:
            # Slow down vehicles based on congestion
            speed_mult = max(0.1, 1.0 - ci * 0.85)

            if v["stopped"]:
                # Some stopped vehicles resume
                if random.random() < 0.05:
                    v["stopped"] = False
            else:
                v["x"] += v["vx"] * speed_mult
                v["y"] += v["vy"] * speed_mult

            # Wrap around
            if v["x"] > 680:
                v["x"] = -40
            elif v["x"] < -60:
                v["x"] = 680

            v["y"] = max(70, min(v["y"], 370))

            # Random stops during high congestion (anomaly)
            if ci > 0.6 and not v["stopped"] and random.random() < 0.03:
                v["stopped"] = True
                anomalies.append({
                    "type": "stopped_vehicle",
                    "vehicle_id": v["id"],
                    "x": round(v["x"]),
                    "y": round(v["y"]),
                })

        # Sudden clustering anomaly
        cluster_detected = False
        if ci > 0.7:
            xs = [v["x"] for v in self._cctv_vehicles if 0 < v["x"] < 640]
            if xs:
                cluster_zone = sum(1 for x in xs if abs(x - (sum(xs)/len(xs))) < 100)
                if cluster_zone > len(xs) * 0.6:
                    cluster_detected = True
                    anomalies.append({
                        "type": "sudden_clustering",
                        "center_x": round(sum(xs) / len(xs)),
                        "center_y": 220,
                    })

        vehicles_data = []
        for v in self._cctv_vehicles:
            vehicles_data.append({
                "id": v["id"],
                "x": round(v["x"], 1),
                "y": round(v["y"], 1),
                "w": v["w"],
                "h": v["h"],
                "color": v["color"],
                "stopped": v["stopped"],
                "cls": v["cls"],
            })

        return {
            "node_id": active_node_id,
            "node_name": node.get("name", active_node_id),
            "frame_width": 640,
            "frame_height": 400,
            "vehicle_count": len(vehicles_data),
            "vehicles": vehicles_data,
            "anomalies": anomalies,
            "cluster_detected": cluster_detected,
            "congestion_index": round(ci, 3),
            "timestamp": time.time(),
        }

    @staticmethod
    def _rush_factor(hour):
        morning = 1 + 1.2 * math.exp(-0.5 * ((hour - 9) / 1.5) ** 2)
        evening = 1 + 1.5 * math.exp(-0.5 * ((hour - 18) / 1.8) ** 2)
        return max(morning, evening)

    def simulate_blockage(self, node_id, duration_ticks=10):
        self._incident_node = node_id
        self._incident_tick = self._tick + duration_ticks
        return {
            "status": "blockage_simulated",
            "node": node_id,
            "duration_ticks": duration_ticks,
        }
