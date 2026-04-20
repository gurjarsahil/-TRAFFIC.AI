"""
Road Network Graph — Models the urban road network as a directed graph.
Nodes = intersections, Edges = road segments.
Includes a demo city layout (Mumbai-inspired grid).
"""
import networkx as nx
import random, math

class RoadNetwork:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_demo_network()

    # ── Demo city: 20-node grid inspired by a metro area ──────────────
    def _build_demo_network(self):
        """Build a realistic demo road network with named intersections."""
        nodes = [
            {"id": "N01", "name": "Marine Drive Junction",     "lat": 18.9440, "lon": 72.8235},
            {"id": "N02", "name": "Churchgate Circle",         "lat": 18.9350, "lon": 72.8270},
            {"id": "N03", "name": "CST Overpass",              "lat": 18.9400, "lon": 72.8360},
            {"id": "N04", "name": "Fort Crossing",             "lat": 18.9340, "lon": 72.8350},
            {"id": "N05", "name": "Colaba Causeway",           "lat": 18.9220, "lon": 72.8320},
            {"id": "N06", "name": "Worli Sea Link Entry",      "lat": 19.0170, "lon": 72.8150},
            {"id": "N07", "name": "Haji Ali Junction",         "lat": 18.9825, "lon": 72.8120},
            {"id": "N08", "name": "Mahalaxmi Bridge",          "lat": 18.9820, "lon": 72.8270},
            {"id": "N09", "name": "Lower Parel Flyover",       "lat": 18.9950, "lon": 72.8300},
            {"id": "N10", "name": "Dadar TT Circle",           "lat": 19.0180, "lon": 72.8430},
            {"id": "N11", "name": "Sion Junction",             "lat": 19.0410, "lon": 72.8620},
            {"id": "N12", "name": "Kurla Connector",           "lat": 19.0700, "lon": 72.8790},
            {"id": "N13", "name": "Andheri Flyover",           "lat": 19.1190, "lon": 72.8460},
            {"id": "N14", "name": "Goregaon Link Road",        "lat": 19.1550, "lon": 72.8490},
            {"id": "N15", "name": "Borivali Highway Entry",    "lat": 19.2290, "lon": 72.8560},
            {"id": "N16", "name": "BKC Junction",              "lat": 19.0650, "lon": 72.8680},
            {"id": "N17", "name": "Powai Lake Crossing",       "lat": 19.0760, "lon": 72.9060},
            {"id": "N18", "name": "Ghatkopar Metro Hub",       "lat": 19.0860, "lon": 72.9080},
            {"id": "N19", "name": "Thane Creek Bridge",        "lat": 19.1860, "lon": 72.9750},
            {"id": "N20", "name": "Navi Mumbai Connector",     "lat": 19.0330, "lon": 73.0290},
        ]

        for n in nodes:
            self.graph.add_node(
                n["id"],
                name=n["name"],
                lat=n["lat"],
                lon=n["lon"],
                congestion_index=0.0,
                predicted_ci=0.0,
                speed_norm=1.0,
                density_norm=0.0,
                vehicle_count=0,
                history=[],
            )

        # Edges: (src, dst, distance_km, flow_direction_weight)
        edges = [
            ("N01", "N02", 1.2, 0.9), ("N02", "N01", 1.2, 0.7),
            ("N02", "N04", 0.8, 0.85), ("N04", "N02", 0.8, 0.6),
            ("N01", "N03", 1.5, 0.8), ("N03", "N01", 1.5, 0.5),
            ("N03", "N04", 0.6, 0.9), ("N04", "N03", 0.6, 0.7),
            ("N04", "N05", 1.4, 0.75), ("N05", "N04", 1.4, 0.8),
            ("N01", "N07", 3.8, 0.85), ("N07", "N01", 3.8, 0.6),
            ("N07", "N08", 1.3, 0.9), ("N08", "N07", 1.3, 0.7),
            ("N07", "N06", 3.5, 0.8), ("N06", "N07", 3.5, 0.75),
            ("N08", "N09", 1.5, 0.85), ("N09", "N08", 1.5, 0.6),
            ("N09", "N10", 2.5, 0.9), ("N10", "N09", 2.5, 0.7),
            ("N06", "N10", 0.5, 0.8), ("N10", "N06", 0.5, 0.6),
            ("N10", "N11", 2.8, 0.85), ("N11", "N10", 2.8, 0.7),
            ("N11", "N12", 3.2, 0.8), ("N12", "N11", 3.2, 0.65),
            ("N12", "N16", 0.8, 0.9), ("N16", "N12", 0.8, 0.7),
            ("N12", "N13", 5.0, 0.75), ("N13", "N12", 5.0, 0.6),
            ("N13", "N14", 4.0, 0.85), ("N14", "N13", 4.0, 0.7),
            ("N14", "N15", 7.5, 0.8), ("N15", "N14", 7.5, 0.6),
            ("N16", "N17", 3.0, 0.85), ("N17", "N16", 3.0, 0.7),
            ("N17", "N18", 1.2, 0.9), ("N18", "N17", 1.2, 0.75),
            ("N18", "N19", 10.0, 0.7), ("N19", "N18", 10.0, 0.5),
            ("N19", "N20", 8.5, 0.65), ("N20", "N19", 8.5, 0.5),
            ("N11", "N16", 2.5, 0.8), ("N16", "N11", 2.5, 0.6),
            ("N12", "N18", 3.5, 0.7), ("N18", "N12", 3.5, 0.55),
        ]

        for src, dst, dist, flow_w in edges:
            self.graph.add_edge(
                src, dst,
                distance_km=dist,
                flow_weight=flow_w,
                historical_weight=random.uniform(0.5, 1.0),
            )

    # ── Accessors ──────────────────────────────────────────────────────
    def get_node(self, node_id):
        return self.graph.nodes[node_id]

    def get_all_nodes(self):
        return list(self.graph.nodes(data=True))

    def get_neighbors(self, node_id):
        """Return successor nodes with edge data."""
        return [
            (nbr, self.graph.nodes[nbr], self.graph.edges[node_id, nbr])
            for nbr in self.graph.successors(node_id)
        ]

    def update_node(self, node_id, **kwargs):
        for k, v in kwargs.items():
            self.graph.nodes[node_id][k] = v

    def get_edge(self, src, dst):
        return self.graph.edges.get((src, dst))

    def to_serializable(self):
        """Export graph for frontend consumption."""
        nodes = []
        for nid, data in self.graph.nodes(data=True):
            nodes.append({
                "id": nid,
                "name": data["name"],
                "lat": data["lat"],
                "lon": data["lon"],
                "congestion_index": round(data.get("congestion_index", 0), 4),
                "predicted_ci": round(data.get("predicted_ci", 0), 4),
                "speed_norm": round(data.get("speed_norm", 1), 4),
                "density_norm": round(data.get("density_norm", 0), 4),
                "vehicle_count": data.get("vehicle_count", 0),
                "history": data.get("history", [])[-20:],  # last 20 entries
            })
        edges = []
        for src, dst, data in self.graph.edges(data=True):
            edges.append({
                "source": src,
                "target": dst,
                "distance_km": data["distance_km"],
                "flow_weight": round(data["flow_weight"], 3),
            })
        return {"nodes": nodes, "edges": edges}
