"""
graph_loader.py
===============
Loads the road network graph for the Kendrapara / coastal-Odisha region
using OSMnx. Caches the result locally so subsequent runs are instant.
Falls back to a deterministic synthetic demo graph if OSM is unavailable.
"""

import os
import pickle
import logging
from pathlib import Path
from typing import Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).parent.parent
_CACHE_DIR = _BACKEND_DIR / "data" / "cache"
_DEMO_DIR  = _BACKEND_DIR / "data" / "demo"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_DEMO_DIR.mkdir(parents=True, exist_ok=True)

OSM_CACHE_FILE       = _CACHE_DIR / "kendrapara_OSM_graph.pkl"
SYNTHETIC_CACHE_FILE = _CACHE_DIR / "kendrapara_synthetic_graph.pkl"
GRAPH_CACHE_FILE     = SYNTHETIC_CACHE_FILE   # legacy alias
GRAPH_CACHE_GPKG     = _CACHE_DIR / "kendrapara_graph.gpkg"

# ── Region settings ────────────────────────────────────────────────────────
# Kendrapara district + coastal fringe, Odisha
REGION_BBOX = {
    "north": 20.70,
    "south": 20.40,
    "east":  86.70,
    "west":  86.40,
}
REGION_NAME = "Kendrapara, Odisha, India"

# Average road speed assumptions (km/h) used when OSM `maxspeed` is absent
DEFAULT_SPEEDS = {
    "motorway":     80,
    "trunk":        60,
    "primary":      50,
    "secondary":    40,
    "tertiary":     30,
    "unclassified": 25,
    "residential":  20,
    "service":      15,
    "track":        10,
    "path":          5,
}


def _add_travel_time(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Add a 'travel_time' edge attribute (seconds) based on length + speed."""
    try:
        import osmnx as ox
        G = ox.add_edge_speeds(G, fallback=40)
        G = ox.add_edge_travel_times(G)
    except Exception:
        # Fallback: compute manually
        for u, v, k, data in G.edges(data=True, keys=True):
            length = data.get("length", 100)   # metres
            speed  = data.get("maxspeed", 40)
            if isinstance(speed, list):
                speed = speed[0]
            try:
                speed = float(str(speed).split()[0])
            except (ValueError, TypeError):
                speed = 40.0
            speed_ms = max(speed, 5) * 1000 / 3600
            G[u][v][k]["travel_time"] = length / speed_ms
    return G


def load_graph_from_osm(force_download: bool = False) -> Tuple[nx.MultiDiGraph, bool]:
    """
    Load the Kendrapara road network from OpenStreetMap via Overpass.
    Uses a dedicated cache file (kendrapara_OSM_graph.pkl) that is ONLY
    written here — never by the synthetic graph builder.

    Returns
    -------
    (G, from_cache): graph and whether it was loaded from cache.

    Raises
    ------
    RuntimeError  if OSM download fails (caller falls back to synthetic graph).
    """
    import osmnx as ox
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="osmnx")

    if not force_download and OSM_CACHE_FILE.exists():
        logger.info("Loading genuine OSM graph from cache: %s", OSM_CACHE_FILE)
        with open(OSM_CACHE_FILE, "rb") as f:
            G = pickle.load(f)
        return G, True

    # Configure OSMnx for large-area queries
    ox.settings.max_query_area_size = 50_000_000_000  # 50 sq km chunks
    ox.settings.timeout = 10
    ox.settings.log_console = False

    logger.info("Downloading genuine OSM graph for %s …", REGION_NAME)
    G = None


    # Strategy 1: place name (fastest)
    try:
        logger.info("Trying place-name query: %s", REGION_NAME)
        G = ox.graph_from_place(REGION_NAME, network_type="drive", simplify=True)
        logger.info("Place-name query succeeded: %d nodes", G.number_of_nodes())
    except Exception as exc:
        logger.warning("Place-name query failed (%s), trying bbox …", exc)

    # Strategy 2: bbox fallback
    if G is None:
        try:
            G = ox.graph_from_bbox(
                bbox=(
                    REGION_BBOX["north"],
                    REGION_BBOX["south"],
                    REGION_BBOX["east"],
                    REGION_BBOX["west"],
                ),
                network_type="drive",
                simplify=True,
                retain_all=False,
            )
            logger.info("Bbox query succeeded: %d nodes", G.number_of_nodes())
        except Exception as exc:
            logger.error("Bbox query also failed: %s", exc)
            raise RuntimeError(f"OSM download failed: {exc}") from exc

    G = _add_travel_time(G)
    with open(OSM_CACHE_FILE, "wb") as f:
        pickle.dump(G, f)
    logger.info("Genuine OSM graph cached to %s (%.1f MB)", OSM_CACHE_FILE,
                OSM_CACHE_FILE.stat().st_size / 1024 / 1024)
    return G, False






def build_demo_graph() -> nx.MultiDiGraph:
    """
    Build a deterministic synthetic road graph that mirrors a coastal
    Odisha topology for demo / testing purposes.

    Node IDs are integers; nodes carry 'x' (lon) and 'y' (lat).
    Edges carry 'length' (m), 'travel_time' (s), 'highway', 'name'.
    Bridge edges additionally carry 'bridge': 'yes'.

    Topology (approximate):
        VILLAGE_A ──road──► JUNCTION_1 ──bridge_B1──► JUNCTION_2 ──road──► HOSPITAL_H1
        VILLAGE_B ──road──► JUNCTION_1
        VILLAGE_C ──road──►                           JUNCTION_3 ──road──► HOSPITAL_H1
        VILLAGE_A ──long detour──────────────────────► JUNCTION_3
        SHELTER_S1 is near JUNCTION_2
    """
    G = nx.MultiDiGraph()

    nodes = {
        # id: (lat, lon, label)
        1: (20.570, 86.510, "Village_A"),
        2: (20.565, 86.520, "Village_B"),
        3: (20.580, 86.500, "Village_C"),
        4: (20.568, 86.530, "Junction_1"),
        5: (20.565, 86.555, "Junction_2"),         # bridge west side
        6: (20.563, 86.560, "Bridge_B1_node"),     # bridge mid-point
        7: (20.560, 86.565, "Junction_3"),         # bridge east side
        8: (20.555, 86.580, "Hospital_H1"),
        9: (20.590, 86.575, "Village_D"),
        10: (20.545, 86.545, "Shelter_S1"),
        11: (20.600, 86.540, "Junction_North"),
        12: (20.595, 86.565, "Junction_NE"),
    }

    for nid, (lat, lon, label) in nodes.items():
        G.add_node(nid, y=lat, x=lon, label=label)

    def _add_edge(u, v, length_m, highway="primary", bridge=False, name=None, speed_kmh=40):
        tt = length_m / (speed_kmh * 1000 / 3600)
        attrs = {
            "length": length_m,
            "travel_time": tt,
            "highway": highway,
            "name": name or f"Road_{u}_{v}",
            "oneway": False,
        }
        if bridge:
            attrs["bridge"] = "yes"
        G.add_edge(u, v, **attrs)
        G.add_edge(v, u, **attrs)   # bidirectional

    # Roads feeding into Junction_1
    _add_edge(1, 4, 1800, "secondary",   name="Main_Rd_A")        # Village_A → J1
    _add_edge(2, 4, 900,  "residential", name="Village_B_Rd")     # Village_B → J1
    _add_edge(3, 4, 1500, "secondary",   name="North_Rd")         # Village_C → J1

    # Junction_1 → bridge approach
    _add_edge(4, 5, 2000, "primary", name="Pre_Bridge_Rd")

    # THE KEY BRIDGE  (Bridge_B1)
    _add_edge(5, 6, 300, "primary", bridge=True, name="Bridge_B1", speed_kmh=30)
    _add_edge(6, 7, 300, "primary", bridge=True, name="Bridge_B1", speed_kmh=30)

    # Junction_3 → Hospital
    _add_edge(7, 8, 1500, "primary", name="Hospital_Access_Rd")

    # DETOUR ROUTE (long way around — used when bridge unavailable)
    _add_edge(4, 11, 4500, "tertiary", name="North_Loop_Rd",  speed_kmh=30)
    _add_edge(11, 12, 3000, "tertiary", name="NE_Connector",  speed_kmh=30)
    _add_edge(12, 8, 2500, "secondary", name="East_Hospital_Rd", speed_kmh=35)

    # Shelter connection
    _add_edge(7, 10, 1200, "residential", name="Shelter_Access", speed_kmh=20)

    # Village_D (remote)
    _add_edge(9, 11, 2000, "tertiary", name="Village_D_Rd", speed_kmh=25)

    # Assign graph CRS metadata
    G.graph["crs"] = "EPSG:4326"
    G.graph["name"] = "Demo Kendrapara Graph"

    return G


def load_graph(use_demo: bool = False, force_download: bool = False) -> Tuple[nx.MultiDiGraph, str]:
    """
    Main entry-point for loading a road network graph.

    Priority:
      1. OSM full download (live or cached) — most accurate
      2. Realistic Kendrapara graph (pre-built, real coordinates) — good fallback
      3. Tiny demo graph — last resort for testing only

    Returns
    -------
    (G, source): graph and source label:
        'osm_cache'         — loaded from local OSM pickle cache
        'osm_live'          — freshly downloaded from Overpass
        'realistic_synthetic' — geographically realistic synthetic graph
        'demo'              — tiny 12-node test graph
    """
    if use_demo:
        logger.info("Using deterministic demo graph.")
        return build_demo_graph(), "demo"

    # Strategy 1: Try OSM (cache or live)
    try:
        G, from_cache = load_graph_from_osm(force_download=force_download)
        source = "osm_cache" if from_cache else "osm_live"
        return G, source
    except Exception as exc:
        logger.warning("OSM unavailable (%s). Trying realistic Kendrapara graph.", exc)

    # Strategy 2: Realistic geographically-correct synthetic graph
    try:
        from .kendrapara_graph_builder import save_kendrapara_graph
        G, source = save_kendrapara_graph()
        logger.info("Loaded realistic Kendrapara graph (%d nodes, %d edges).", G.number_of_nodes(), G.number_of_edges())
        return G, source
    except Exception as exc2:
        logger.warning("Realistic graph builder failed (%s). Falling back to demo graph.", exc2)

    # Strategy 3: Demo graph (last resort)
    return build_demo_graph(), "demo"

