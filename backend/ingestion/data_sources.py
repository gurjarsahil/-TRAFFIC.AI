"""
Data Sources Manager — Coordinates ingestion from multiple data sources.
"""

class DataSourceManager:
    """Manages and aggregates data from all ingestion sources."""

    def __init__(self, gps_simulator):
        self.gps = gps_simulator
        self._density_overrides = {}  # DL-derived density per node

    def set_density(self, node_id, density):
        """Set DL-derived vehicle density for a node."""
        self._density_overrides[node_id] = density

    def set_densities(self, density_map):
        """Batch update densities from detection layer."""
        self._density_overrides.update(density_map)

    def get_all_data(self):
        """
        Returns combined data:
        {node_id: {"speed_kph": float, "density": int}}
        """
        speeds = self.gps.get_speeds()
        result = {}
        for nid in speeds:
            result[nid] = {
                "speed_kph": speeds[nid],
                "density": self._density_overrides.get(nid, 0),
            }
        return result

    def tick(self):
        """Advance the simulation clock in all sources."""
        self.gps.tick()
