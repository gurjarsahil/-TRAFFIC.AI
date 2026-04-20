"""
GPS Speed Data Simulator — Generates realistic simulated speed data
for each road segment/intersection in the network.
"""
import random, math, time

class GPSSimulator:
    """Generates plausible GPS-derived speed data per node."""

    def __init__(self, road_network, max_speed_kph=60):
        self.network = road_network
        self.max_speed = max_speed_kph
        self._base_speeds = {}
        self._tick = 0
        self._init_base_speeds()

    def _init_base_speeds(self):
        """Set baseline speeds with slight per-node variation."""
        for nid, data in self.network.get_all_nodes():
            # Base speed 30–55 kph
            self._base_speeds[nid] = random.uniform(30, 55)

    def tick(self):
        """Advance the simulation clock."""
        self._tick += 1

    def get_speeds(self):
        """
        Return dict {node_id: speed_kph} with time-varying noise.
        Simulates morning/evening rush hours and random slowdowns.
        """
        hour_of_day = (self._tick % 288) / 12  # 288 ticks = 24 hours at 5-min intervals
        rush_factor = self._rush_multiplier(hour_of_day)

        speeds = {}
        for nid in self._base_speeds:
            base = self._base_speeds[nid]
            # Apply rush hour effect
            speed = base * rush_factor
            # Random perturbation ±15%
            speed *= random.uniform(0.85, 1.15)
            # Occasional sharp slowdown (5% chance)
            if random.random() < 0.05:
                speed *= random.uniform(0.2, 0.5)
            speeds[nid] = max(2.0, min(speed, self.max_speed))
        return speeds

    @staticmethod
    def _rush_multiplier(hour):
        """
        Returns a multiplier < 1 during rush hours, ~1 otherwise.
        Morning rush: 8-10, Evening rush: 17-20.
        """
        morning = math.exp(-0.5 * ((hour - 9) / 1.2) ** 2) * 0.45
        evening = math.exp(-0.5 * ((hour - 18.5) / 1.5) ** 2) * 0.5
        return 1.0 - morning - evening
