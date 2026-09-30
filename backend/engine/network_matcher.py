"""
network_matcher.py
==================
Snaps geographic lat/lon points (hospitals, shelters, settlements)
to their nearest node in the road network graph.

This is the bridge between the POI layer and the routing engine.

All matched nodes are labelled with their data provenance
(REAL / ESTIMATED) so the distinction is never lost.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)


@dataclass
class MatchedPOI:
    """A geographic POI snapped to a graph node."""
    poi_name: str
    facility_type: str          # 'hospital' | 'shelter' | 'settlement'
    original_lat: float
    original_lon: float
    nearest_node: int
    nearest_node_lat: float
    nearest_node_lon: float
    snap_distance_m: float      # distance from POI to snapped node
    osm_source: str             # 'REAL' | 'ESTIMATED' | 'fallback'
    osm_id: Optional[int] = None
    population_estimate: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "poi_name": self.poi_name,
            "facility_type": self.facility_type,
            "original_lat": self.original_lat,
            "original_lon": self.original_lon,
            "nearest_node": self.nearest_node,
            "snap_distance_m": round(self.snap_distance_m, 1),
            "osm_source": self.osm_source,
            "osm_id": self.osm_id,
            "population_estimate": self.population_estimate,
        }


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Fast haversine distance in metres."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def snap_to_nearest_node(
    G: nx.MultiDiGraph,
    lat: float,
    lon: float,
) -> Tuple[int, float]:
    """
    Find the nearest graph node to (lat, lon).

    Returns (node_id, distance_m).
    Uses brute-force haversine — fast enough for graphs < 50k nodes.
    For larger graphs, use OSMnx's nearest_nodes().
    """
    best_node = None
    best_dist = float("inf")

    for nid, data in G.nodes(data=True):
        nlat = data.get("y", 0)
        nlon = data.get("x", 0)
        d = _haversine_m(lat, lon, nlat, nlon)
        if d < best_dist:
            best_dist = d
            best_node = nid

    return best_node, best_dist


def snap_to_nearest_node_osmnx(
    G: nx.MultiDiGraph,
    lat: float,
    lon: float,
) -> Tuple[int, float]:
    """
    Use OSMnx nearest_nodes for faster snapping on large graphs.
    Falls back to brute-force if OSMnx unavailable.
    """
    try:
        import osmnx as ox
        node_id = ox.nearest_nodes(G, X=lon, Y=lat)
        data = G.nodes[node_id]
        dist = _haversine_m(lat, lon, data.get("y", 0), data.get("x", 0))
        return node_id, dist
    except Exception:
        return snap_to_nearest_node(G, lat, lon)


def match_pois_to_graph(
    G: nx.MultiDiGraph,
    pois: List[dict],
    facility_type: str,
    max_snap_distance_m: float = 5000.0,
) -> List[MatchedPOI]:
    """
    Snap a list of POI dicts to the nearest graph nodes.

    POI dicts must have: lat, lon, name, osm_source.
    Nodes farther than max_snap_distance_m are dropped with a warning.

    Returns list of MatchedPOI.
    """
    matched = []
    dropped = 0

    for poi in pois:
        lat = poi.get("lat") or poi.get("original_lat")
        lon = poi.get("lon") or poi.get("original_lon")
        name = poi.get("name", "Unknown")

        if lat is None or lon is None:
            logger.warning("POI '%s' has no coordinates — skipped.", name)
            continue

        node_id, dist = snap_to_nearest_node_osmnx(G, lat, lon)

        if node_id is None:
            logger.warning("No node found for '%s' — skipped.", name)
            continue

        if dist > max_snap_distance_m:
            logger.warning(
                "POI '%s' snap distance %.0fm > %.0fm — skipped.",
                name, dist, max_snap_distance_m
            )
            dropped += 1
            continue

        node_data = G.nodes[node_id]
        matched.append(MatchedPOI(
            poi_name=name,
            facility_type=facility_type,
            original_lat=lat,
            original_lon=lon,
            nearest_node=node_id,
            nearest_node_lat=node_data.get("y", lat),
            nearest_node_lon=node_data.get("x", lon),
            snap_distance_m=dist,
            osm_source=poi.get("osm_source", "UNKNOWN"),
            osm_id=poi.get("osm_id"),
            population_estimate=poi.get("population_estimate"),
        ))

    logger.info(
        "Matched %d/%d %s POIs (dropped %d > %.0fm).",
        len(matched), len(pois), facility_type, dropped, max_snap_distance_m
    )
    return matched


def match_all_facilities(
    G: nx.MultiDiGraph,
    pois: dict,
) -> Dict[str, List[MatchedPOI]]:
    """
    Match hospitals, shelters and settlements to the graph.

    Parameters
    ----------
    G    : road network graph
    pois : dict from poi_loader.load_all_pois()

    Returns
    -------
    dict with keys: 'hospitals', 'shelters', 'settlements'
    """
    hospitals   = match_pois_to_graph(G, pois.get("hospitals", []),   "hospital",   max_snap_distance_m=8000)
    shelters    = match_pois_to_graph(G, pois.get("shelters", []),    "shelter",    max_snap_distance_m=8000)
    settlements = match_pois_to_graph(G, pois.get("settlements", []), "settlement", max_snap_distance_m=10000)

    return {
        "hospitals":   hospitals,
        "shelters":    shelters,
        "settlements": settlements,
    }
