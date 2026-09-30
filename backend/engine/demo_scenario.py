"""
demo_scenario.py
================
Deterministic demo scenario for PreImpact.

Produces a complete, realistic-looking demo using the synthetic
Kendrapara graph — works with zero external API calls.

All values are clearly labelled as DEMO / MODELLED / ESTIMATED.
"""

from __future__ import annotations
import logging
from typing import Dict, List, Any

from .graph_loader import build_demo_graph, load_graph
from .bridge_detector import detect_bridges, BridgeAsset
from .counterfactual import (
    run_full_counterfactual,
    simulate_asset_unavailability,
    CounterfactualResult,
)

logger = logging.getLogger(__name__)

# ── Demo facility / settlement definitions ────────────────────────────────

DEMO_SETTLEMENTS = [
    (1, "Rajnagar Village",   4200),   # (node_id, name, estimated population)
    (2, "Mahakalapada Town",  8700),
    (3, "Satabhaya Village",  2100),
    (9, "Kansarpal Village",  1800),
]

DEMO_HOSPITALS = [
    (8, "Kendrapara District Hospital"),
]

DEMO_SHELTERS = [
    (10, "Cyclone Shelter CS-07"),
]

DEMO_CYCLONE_SCENARIO = {
    "name": "Scenario: Very Severe Cyclone (VSCS)",
    "description": (
        "Modelled wind field for a VSCS-class cyclone making landfall near "
        "Kendrapara coast. Based on historical track analogues (e.g. Fani 2019). "
        "NOT a real-time forecast."
    ),
    "landfall_lat": 20.52,
    "landfall_lon": 86.70,
    "max_wind_kmh": 175,
    "storm_surge_m": 3.5,
    "source": "MODELLED SCENARIO — not a live forecast",
    "data_label": "DEMO",
}

DEMO_EXPOSURE_SCORES = {
    "B001": 0.85,   # Bridge_B1 — in direct coastal storm-surge zone
}


def _build_population_map(settlements: list) -> Dict[int, int]:
    return {node_id: pop for node_id, _, pop in settlements}


def run_demo_scenario() -> Dict[str, Any]:
    """
    Execute the full demo counterfactual scenario.

    Returns a structured dict suitable for the API to serve and the
    frontend to render.
    """
    logger.info("Running PreImpact demo scenario …")

    # Load the synthetic graph
    G, source = load_graph(use_demo=True)
    bridges = detect_bridges(G)

    if not bridges:
        raise RuntimeError("Demo graph produced no bridge assets — check build_demo_graph().")

    settlement_nodes = [(n, lbl) for n, lbl, _ in DEMO_SETTLEMENTS]
    hospital_nodes   = DEMO_HOSPITALS
    shelter_nodes    = DEMO_SHELTERS
    pop_map          = _build_population_map(DEMO_SETTLEMENTS)

    results = []
    for bridge in bridges:
        exposure = DEMO_EXPOSURE_SCORES.get(bridge.asset_id, 0.6)

        cf_result = run_full_counterfactual(
            G=G,
            asset=bridge,
            settlement_nodes=settlement_nodes,
            hospital_nodes=hospital_nodes,
            shelter_nodes=shelter_nodes,
            population_map=pop_map,
            exposure_score=exposure,
            disruption_threshold_min=15.0,
        )
        results.append(cf_result)

    # Sort by max disruption delta (most critical first)
    results.sort(key=lambda r: r.max_disruption_delta_min, reverse=True)

    # Get the top bridge for the "headline" result
    top = results[0]

    # Also extract the single most-disrupted pair for the summary card
    most_disrupted_change = None
    best_delta = -1
    for ch in top.changes:
        if ch.disruption_delta_min != float("inf") and ch.disruption_delta_min > best_delta:
            best_delta = ch.disruption_delta_min
            most_disrupted_change = ch

    headline = None
    if most_disrupted_change:
        headline = {
            "origin_label": most_disrupted_change.origin_label,
            "dest_label": most_disrupted_change.dest_label,
            "baseline_travel_time_min": most_disrupted_change.baseline.travel_time_min
            if most_disrupted_change.baseline else None,
            "scenario_travel_time_min": most_disrupted_change.scenario.travel_time_min
            if most_disrupted_change.scenario else None,
            "disruption_delta_min": most_disrupted_change.disruption_delta_min,
            "became_unreachable": most_disrupted_change.became_unreachable,
            "baseline_path": most_disrupted_change.baseline.path_nodes
            if most_disrupted_change.baseline else [],
            "scenario_path": most_disrupted_change.scenario.path_nodes
            if most_disrupted_change.scenario else [],
        }

    return {
        "mode": "DEMO",
        "data_label": "DEMO SCENARIO — All values are modelled estimates",
        "cyclone_scenario": DEMO_CYCLONE_SCENARIO,
        "graph_source": source,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "bridges_detected": len(bridges),
        "bridges": [b.to_dict() for b in bridges],
        "settlements": [
            {"node_id": n, "name": lbl, "population_estimate": pop, "data_label": "ESTIMATED"}
            for n, lbl, pop in DEMO_SETTLEMENTS
        ],
        "hospitals": [
            {"node_id": n, "name": lbl} for n, lbl in DEMO_HOSPITALS
        ],
        "shelters": [
            {"node_id": n, "name": lbl} for n, lbl in DEMO_SHELTERS
        ],
        "counterfactual_results": [_cf_to_dict(r) for r in results],
        "top_priority_bridge": top.asset_id,
        "headline": headline,
        "node_positions": _extract_node_positions(G),
    }


def _cf_to_dict(result: CounterfactualResult) -> dict:
    d = result.to_dict()
    d["priority"] = getattr(result, "priority", {})
    d["population_impact"] = getattr(result, "population_impact", {})
    return d


def _extract_node_positions(G) -> Dict[int, Dict[str, float]]:
    """Return {node_id: {lat, lon, label}} for all nodes in the graph."""
    positions = {}
    for nid, data in G.nodes(data=True):
        positions[nid] = {
            "lat": data.get("y", 0),
            "lon": data.get("x", 0),
            "label": data.get("label", str(nid)),
        }
    return positions


def get_node_lat_lon(G, node_id: int):
    """Helper: return (lat, lon) for a node."""
    data = G.nodes[node_id]
    return data.get("y", 0), data.get("x", 0)
