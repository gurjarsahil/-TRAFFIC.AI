"""
Graph-Based Congestion Propagation Engine — "Anti-Gravity" Core Innovation.
Simulates how congestion spreads through the road network over time.
"""
from config import Config

class SpreadEngine:
    """
    Propagates congestion through the road graph.

    When a node's CI exceeds a threshold, congestion "spills" to
    neighboring nodes based on:
      - distance (closer = more affected)
      - traffic flow direction (flow weight)
      - historical patterns (historical weight)
    """

    def __init__(self, road_network, decay=None, threshold=None, max_hops=None):
        self.network = road_network
        self.decay = decay or Config.PROPAGATION_DECAY
        self.threshold = threshold or Config.PROPAGATION_THRESHOLD
        self.max_hops = max_hops or Config.MAX_PROPAGATION_HOPS

    def propagate(self):
        """
        Run one propagation cycle across the entire network.
        Returns a dict of propagation effects: {node_id: added_ci}
        """
        effects = {}
        graph = self.network.graph

        for nid, data in graph.nodes(data=True):
            ci = data.get("congestion_index", 0)
            if ci < self.threshold:
                continue

            # BFS-like spread up to max_hops
            self._spread_from(nid, ci, effects)

        return effects

    def _spread_from(self, source_id, source_ci, effects):
        """Spread congestion from a single source node."""
        visited = {source_id}
        frontier = [(source_id, source_ci, 0)]  # (node, ci, hop)

        while frontier:
            current_id, current_ci, hop = frontier.pop(0)
            if hop >= self.max_hops:
                continue

            for nbr_id, nbr_data, edge_data in self.network.get_neighbors(current_id):
                if nbr_id in visited:
                    continue
                visited.add(nbr_id)

                # Compute propagated CI
                distance_factor = 1.0 / (1.0 + edge_data["distance_km"])
                flow_factor = edge_data["flow_weight"]
                hist_factor = edge_data.get("historical_weight", 0.7)

                propagated = (
                    current_ci
                    * self.decay
                    * distance_factor
                    * flow_factor
                    * hist_factor
                )

                if propagated > 0.01:  # Minimum meaningful effect
                    effects[nbr_id] = effects.get(nbr_id, 0) + round(propagated, 4)
                    frontier.append((nbr_id, propagated, hop + 1))

    def simulate_future(self, steps=6):
        """
        Simulate congestion spread over multiple future time steps.
        Returns: list of dicts [{node_id: predicted_ci}, ...]
        """
        import copy
        snapshots = []
        temp_graph = copy.deepcopy(self.network.graph)

        for step in range(steps):
            effects = {}
            for nid, data in temp_graph.nodes(data=True):
                ci = data.get("congestion_index", 0)
                if ci < self.threshold:
                    continue
                visited = {nid}
                frontier = [(nid, ci, 0)]
                while frontier:
                    curr, curr_ci, hop = frontier.pop(0)
                    if hop >= self.max_hops:
                        continue
                    for nbr in self.network.graph.successors(curr):
                        if nbr in visited:
                            continue
                        visited.add(nbr)
                        edge = self.network.graph.edges[curr, nbr]
                        dist_f = 1.0 / (1.0 + edge["distance_km"])
                        flow_f = edge["flow_weight"]
                        prop = curr_ci * self.decay * dist_f * flow_f
                        if prop > 0.01:
                            effects[nbr] = effects.get(nbr, 0) + prop
                            frontier.append((nbr, prop, hop + 1))

            # Apply effects with natural decay
            snapshot = {}
            for nid, data in temp_graph.nodes(data=True):
                current_ci = data.get("congestion_index", 0)
                added = effects.get(nid, 0)
                new_ci = min(1.0, current_ci * 0.95 + added)  # 5% natural decay
                temp_graph.nodes[nid]["congestion_index"] = new_ci
                snapshot[nid] = round(new_ci, 4)

            snapshots.append(snapshot)

        return snapshots

    def get_propagation_report(self):
        """Generate a human-readable propagation influence report."""
        effects = self.propagate()
        report = []
        for nid, added_ci in sorted(effects.items(), key=lambda x: -x[1]):
            node_data = self.network.get_node(nid)
            report.append({
                "node_id": nid,
                "node_name": node_data["name"],
                "current_ci": round(node_data.get("congestion_index", 0), 4),
                "propagated_addition": round(added_ci, 4),
                "projected_ci": round(
                    min(1.0, node_data.get("congestion_index", 0) + added_ci), 4
                ),
            })
        return report
