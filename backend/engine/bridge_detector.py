"""
bridge_detector.py
==================
Identifies bridge edges (and other critical assets) in a road-network graph.

For OSM graphs  : looks for OSM tags bridge='yes' / tunnel / highway=crossing.
For demo graphs : bridges are marked with bridge='yes' during construction.

Returns a list of BridgeAsset dataclass instances.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)


@dataclass
class BridgeAsset:
    """Represents a detected bridge/critical asset in the road network."""
    asset_id: str                  # Unique identifier, e.g. "B_001"
    name: str                      # Human-readable name
    edge_keys: List[Tuple]         # List of (u, v, k) tuples for all edges of this asset
    midpoint_lat: float
    midpoint_lon: float
    highway_type: str = "primary"
    length_m: float = 0.0
    osm_way_id: Optional[int] = None
    tags: dict = field(default_factory=dict)

    # Computed later by the counterfactual engine
    exposure_level: str = "Unknown"   # Low / Medium / High / Extreme
    baseline_travel_time_s: Optional[float] = None
    scenario_travel_time_s: Optional[float] = None
    disruption_delta_s: Optional[float] = None

    @property
    def disruption_delta_min(self) -> Optional[float]:
        if self.disruption_delta_s is None:
            return None
        return round(self.disruption_delta_s / 60, 1)

    @property
    def baseline_travel_time_min(self) -> Optional[float]:
        if self.baseline_travel_time_s is None:
            return None
        return round(self.baseline_travel_time_s / 60, 1)

    @property
    def scenario_travel_time_min(self) -> Optional[float]:
        if self.scenario_travel_time_s is None:
            return None
        return round(self.scenario_travel_time_s / 60, 1)

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "midpoint_lat": self.midpoint_lat,
            "midpoint_lon": self.midpoint_lon,
            "highway_type": self.highway_type,
            "length_m": round(self.length_m, 1),
            "osm_way_id": self.osm_way_id,
            "exposure_level": self.exposure_level,
            "baseline_travel_time_min": self.baseline_travel_time_min,
            "scenario_travel_time_min": self.scenario_travel_time_min,
            "disruption_delta_min": self.disruption_delta_min,
            "edge_count": len(self.edge_keys),
        }


def _edge_lat_lon_midpoint(G: nx.MultiDiGraph, u: int, v: int) -> Tuple[float, float]:
    """Return approximate lat/lon midpoint of an edge."""
    u_data = G.nodes[u]
    v_data = G.nodes[v]
    lat = (u_data.get("y", 0) + v_data.get("y", 0)) / 2
    lon = (u_data.get("x", 0) + v_data.get("x", 0)) / 2
    return lat, lon


def detect_bridges(G: nx.MultiDiGraph) -> List[BridgeAsset]:
    """
    Scan all edges of G and return a list of BridgeAsset objects.

    Grouping strategy
    -----------------
    Consecutive bridge edges that share the same OSM name (or way ID)
    are merged into a single BridgeAsset.  This avoids listing every
    individual 20-m segment of a 300-m bridge as a separate asset.
    """
    raw_bridge_edges: List[Tuple] = []   # (u, v, k, data)

    for u, v, k, data in G.edges(data=True, keys=True):
        bridge_tag = str(data.get("bridge", "")).lower()
        if bridge_tag in ("yes", "true", "1", "viaduct", "movable"):
            raw_bridge_edges.append((u, v, k, data))

    logger.info("Raw bridge edges found: %d", len(raw_bridge_edges))

    if not raw_bridge_edges:
        return []

    # Group by name / OSM way id
    groups: dict[str, list] = {}
    for u, v, k, data in raw_bridge_edges:
        name = (
            data.get("name")
            or data.get("ref")
            or str(data.get("osmid", ""))
            or f"Bridge_{u}_{v}"
        )
        # Normalise: take first name if it's a list
        if isinstance(name, list):
            name = name[0]
        name = str(name).strip() or f"Bridge_{u}_{v}"
        groups.setdefault(name, []).append((u, v, k, data))

    assets: List[BridgeAsset] = []
    for idx, (name, edges) in enumerate(groups.items(), start=1):
        # Aggregate edge stats
        total_length = sum(d.get("length", 0) for _, _, _, d in edges)
        lats = []
        lons = []
        for u, v, _, _ in edges:
            lat, lon = _edge_lat_lon_midpoint(G, u, v)
            lats.append(lat)
            lons.append(lon)

        mid_lat = sum(lats) / len(lats) if lats else 0
        mid_lon = sum(lons) / len(lons) if lons else 0

        first_data = edges[0][3]
        highway = first_data.get("highway", "road")
        if isinstance(highway, list):
            highway = highway[0]

        osm_way_id = first_data.get("osmid")
        if isinstance(osm_way_id, list):
            osm_way_id = osm_way_id[0]
        try:
            osm_way_id = int(osm_way_id) if osm_way_id else None
        except (ValueError, TypeError):
            osm_way_id = None

        asset = BridgeAsset(
            asset_id=f"B{idx:03d}",
            name=name,
            edge_keys=[(u, v, k) for u, v, k, _ in edges],
            midpoint_lat=round(mid_lat, 6),
            midpoint_lon=round(mid_lon, 6),
            highway_type=str(highway),
            length_m=round(total_length, 1),
            osm_way_id=osm_way_id,
        )
        assets.append(asset)
        logger.debug("Detected bridge: %s  edges=%d  len=%.0fm", name, len(edges), total_length)

    logger.info("Unique bridge assets detected: %d", len(assets))
    return assets
