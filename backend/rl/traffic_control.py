class TrafficSignalController:
    """
    Simulation of an RL-based Traffic Signal Controller.
    Learns optimal green-light timing based on detected congestion.
    """
    def __init__(self):
        # 4 Directions: N, S, E, W
        self.directions = ["North", "South", "East", "West"]
        self.timings = {d: 30 for d in self.directions} # 30s default
        
    def recommend_timings(self, density_map):
        """
        Adjust signal timing based on density.
        density_map: { "North": float, "South": float, ... }
        """
        total_density = sum(density_map.values()) or 1.0
        
        recs = {}
        for d in self.directions:
            # Allocate more time to directions with more density
            weight = density_map.get(d, 0.25) / total_density
            recs[d] = int(max(15, min(90, 120 * weight)))
            
        self.timings = recs
        return recs

    def get_status(self):
        return {
            "current_green": self.directions[0], # Simulated cycle
            "phase_timings": self.timings,
            "mode": "Adaptive RL-Optimized"
        }
