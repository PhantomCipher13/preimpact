"""
real_scenario.py
================
Real-data counterfactual scenario runner for PreImpact Milestone 2.

Uses:
  - OSM road network (downloaded + cached)
  - OSM / fallback hospitals & shelters
  - Estimated settlement populations (clearly labelled)
  - Modelled hazard exposure (cyclone analogue scenario)

Produces ranked bridge impact analysis with explicit data provenance.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)

_BACKEND_DIR  = Path(__file__).parent.parent
_RESULTS_CACHE = _BACKEND_DIR / "data" / "cache" / "real_scenario_results.json"


def run_real_scenario(
    force_recompute: bool = False,
    max_snap_distance_m: float = 5000,
    force_synthetic: bool = False,
) -> Dict[str, Any]:
    """
    Full Milestone 2 real-data pipeline:

    1. Load OSM road graph (or demo/synthetic fallback)
    2. Detect bridges
    3. Load / snap hospitals, shelters, settlements
    4. Compute hazard exposure per bridge
    5. Run counterfactual accessibility analysis
    6. Rank by priority
    7. Return structured result with provenance labels

    Parameters
    ----------
    force_recompute : ignore cached results
    max_snap_distance_m : max distance to snap a POI to the graph
    force_synthetic : bypass live/cached OSM and force the realistic synthetic graph

    Returns
    -------
    Structured dict ready for API serialization / UI rendering.
    """
    from .graph_loader   import load_graph
    from .bridge_detector import detect_bridges
    from .poi_loader     import load_all_pois
    from .network_matcher import match_all_facilities
    from .hazard_exposure import batch_compute_exposure, get_cyclone_scenario, filter_exposed_bridges
    from .counterfactual  import (
        run_full_counterfactual,
        calculate_priority,
    )

    if not force_synthetic and not force_recompute and _RESULTS_CACHE.exists():
        try:
            cached_data = json.loads(_RESULTS_CACHE.read_text())
            osm_cache_file = _BACKEND_DIR / "data" / "cache" / "kendrapara_OSM_graph.pkl"
            # Provenance guard: NEVER report REAL_OSM unless genuine OSM cache file exists
            if cached_data.get("mode") == "REAL_OSM" and not osm_cache_file.exists():
                logger.warning("Cache claimed REAL_OSM but no genuine OSM cache file exists. Invalidating cache.")
            elif cached_data.get("mode") in ("PARTIAL_REAL_DATA", "DEMO_FALLBACK", "REAL_OSM"):
                logger.info("Loading cached scenario results [%s].", cached_data.get("mode"))
                return cached_data
        except Exception as err:
            logger.warning("Failed to read cached results (%s). Recomputing...", err)

    # ── Step 1: Load graph ─────────────────────────────────────────────
    if force_synthetic:
        from .kendrapara_graph_builder import save_kendrapara_graph
        G, graph_source = save_kendrapara_graph()
    else:
        G, graph_source = load_graph(use_demo=False)

    logger.info(
        "Graph loaded [%s]: %d nodes, %d edges",
        graph_source, G.number_of_nodes(), G.number_of_edges()
    )


    # ── Step 2: Detect bridges ─────────────────────────────────────────
    bridges = detect_bridges(G)
    logger.info("Bridges detected: %d", len(bridges))

    if not bridges:
        logger.warning("No OSM bridges found — this may indicate the graph lacks bridge tags.")

    # ── Step 3: Load POIs ──────────────────────────────────────────────
    pois = load_all_pois()
    logger.info(
        "POIs: %d hospitals, %d shelters, %d settlements",
        len(pois["hospitals"]), len(pois["shelters"]), len(pois["settlements"])
    )

    # ── Step 4: Snap POIs to graph nodes ───────────────────────────────
    facilities = match_all_facilities(G, pois)

    hosp_matched  = facilities["hospitals"]
    shelt_matched = facilities["shelters"]
    sett_matched  = facilities["settlements"]

    logger.info(
        "Snapped: %d hospitals, %d shelters, %d settlements",
        len(hosp_matched), len(shelt_matched), len(sett_matched)
    )

    # If no facilities matched (graph doesn't cover POI area), use best-effort nodes
    if not hosp_matched and not shelt_matched:
        logger.warning(
            "No facilities snapped to graph — network may not overlap POI locations. "
            "Results will use nearest available graph nodes."
        )

    # ── Step 5: Hazard exposure & candidate filtering ──────────────────
    cyclone = get_cyclone_scenario()
    filter_res = filter_exposed_bridges(bridges, cyclone, min_exposure_score=0.35)
    exposed_bridges = filter_res["exposed_assets"]
    exposure_map = filter_res["exposure_map"]

    total_bridges_count = filter_res["total_count"]
    exposed_bridges_count = filter_res["exposed_count"]

    # Candidate bridges for full counterfactual simulation:
    # Top exposed bridges (up to 12)
    analyzed_candidate_bridges = exposed_bridges[:12]

    # ── Step 6: Counterfactual analysis per exposed bridge ─────────────
    settlement_nodes = [(s.nearest_node, s.poi_name) for s in sett_matched]
    hospital_nodes   = [(h.nearest_node, h.poi_name) for h in hosp_matched]
    shelter_nodes    = [(s.nearest_node, s.poi_name) for s in shelt_matched]

    pop_map = {s.nearest_node: (s.population_estimate or 5000) for s in sett_matched}

    # Fall back to dummy routing pairs if nothing matched
    if not settlement_nodes:
        nodes_list = list(G.nodes())[:5]
        settlement_nodes = [(n, f"Node_{n}") for n in nodes_list]
        pop_map = {n: 5000 for n in nodes_list}

    if not hospital_nodes:
        nodes_list = list(G.nodes())
        hospital_nodes = [(nodes_list[-1], "Nearest_Node_Hospital")]

    if not shelter_nodes:
        nodes_list = list(G.nodes())
        shelter_nodes = [(nodes_list[len(nodes_list)//2], "Nearest_Node_Shelter")]

    counterfactual_results = []

    for bridge in analyzed_candidate_bridges:
        exp = exposure_map.get(bridge.asset_id)
        exposure_score = exp.exposure_score if exp else 0.5

        try:
            cf = run_full_counterfactual(
                G=G,
                asset=bridge,
                settlement_nodes=settlement_nodes,
                hospital_nodes=hospital_nodes,
                shelter_nodes=shelter_nodes,
                population_map=pop_map,
                exposure_score=exposure_score,
                disruption_threshold_min=10.0,
            )
            cf_dict = cf.to_dict()
            cf_dict["priority"] = cf.priority
            cf_dict["population_impact"] = cf.population_impact
            cf_dict["exposure"] = exp.to_dict() if exp else {}
            counterfactual_results.append(cf_dict)
        except Exception as exc:
            logger.warning("Counterfactual failed for %s: %s", bridge.asset_id, exc)

    # Sort strictly by Resilience Priority Score descending
    counterfactual_results.sort(
        key=lambda r: (
            r.get("priority", {}).get("raw_score", 0),
            r.get("unreachable_count", 0),
            r.get("max_disruption_delta_min", 0),
        ),
        reverse=True,
    )

    # Calculate top-level impact summary
    unique_hospitals_affected = set()
    unique_shelters_affected = set()
    unique_settlements_affected = set()
    max_pop_affected = 0

    for cf in counterfactual_results:
        for hid in cf.get("hospitals_affected", []):
            unique_hospitals_affected.add(hid)
        for sid in cf.get("shelters_affected", []):
            unique_shelters_affected.add(sid)
        pop_imp = cf.get("population_impact", {})
        if pop_imp.get("affected_population", 0) > max_pop_affected:
            max_pop_affected = pop_imp.get("affected_population", 0)
        for ch in cf.get("changes", []):
            if (ch.get("disruption_delta_min") not in (0, None) and ch.get("disruption_delta_min") != 0.0) or ch.get("became_unreachable"):
                unique_settlements_affected.add(ch.get("origin_label"))

    summary = {
        "scenario_name": cyclone.get("name"),
        "scenario_type": cyclone.get("scenario_type", "Historical/replay scenario"),
        "analogue_event": cyclone.get("analogue_event", "Cyclone Fani (May 2019)"),
        "region": cyclone.get("region", "Kendrapara District, Coastal Odisha"),
        "exposure_window": cyclone.get("exposure_window", "Replay Window: T-6h to T+12h"),
        "total_bridges": total_bridges_count,
        "exposed_bridges": exposed_bridges_count,
        "analyzed_bridges": len(counterfactual_results),
        "hospitals_potentially_affected": len(unique_hospitals_affected) or len(hosp_matched),
        "shelters_potentially_affected": len(unique_shelters_affected) or len(shelt_matched),
        "communities_potentially_affected": len(unique_settlements_affected) or len(sett_matched),
        "population_estimate_affected": max_pop_affected or sum(s.population_estimate or 0 for s in sett_matched),
        "data_provenance": {
            "hazard_source": cyclone.get("source"),
            "resolution": cyclone.get("resolution"),
            "classification": "MODELED SCENARIO — Historical Replay",
        },
    }


    # ── Step 7: Mode and Provenance Determination ──────────────────────
    #
    # MODE LOGIC — strictly honest about what is real vs modelled:
    #
    #   REAL_OSM        → road network is a genuine OSM download (osm_cache / osm_live)
    #   PARTIAL_REAL_DATA → road topology is synthetic/modelled but hospital POIs
    #                       are from real OSM records (realistic_synthetic source)
    #   DEMO_FALLBACK   → tiny 12-node synthetic demo graph, no real POIs
    #
    OSM_REAL_SOURCES = {"osm_cache", "osm_live"}

    if graph_source in OSM_REAL_SOURCES:
        mode = "REAL_OSM"
    elif graph_source == "realistic_synthetic":
        mode = "PARTIAL_REAL_DATA"
    else:
        mode = "DEMO_FALLBACK"

    # Per-layer data provenance — computed from actual sources, not hardcoded
    road_network_label = {
        "osm_cache":           "REAL — OpenStreetMap (cached download)",
        "osm_live":            "REAL — OpenStreetMap (live download)",
        "realistic_synthetic": "SYNTHETIC / MODELED — Road network: Modeled fallback — live OSM road retrieval unavailable (built from real geographic coordinates)",
        "demo":                "DEMO — tiny 12-node synthetic test graph",
    }.get(graph_source, f"UNKNOWN ({graph_source})")

    bridge_label = {
        "osm_cache":           "REAL — OSM bridge=yes tag",
        "osm_live":            "REAL — OSM bridge=yes tag",
        "realistic_synthetic": "SYNTHETIC / MODELED — placed on estimated river-crossing locations on road corridors",
        "demo":                "DEMO — synthetic bridge",
    }.get(graph_source, "UNKNOWN")

    hospital_label = (
        "REAL — OpenStreetMap (Hospital locations: Real OpenStreetMap data with verified OSM IDs)"
        if pois.get("hospital_source") == "osm"
        else "ESTIMATED / FALLBACK — fallback coordinates"
    )

    shelter_label = (
        "REAL — OpenStreetMap"
        if pois.get("shelter_source") == "osm"
        else "ESTIMATED / FALLBACK — fallback coordinates (Overpass returned no assembly points)"
    )

    warnings_map = {
        "REAL_OSM": None,
        "PARTIAL_REAL_DATA": (
            "Road network: Modeled fallback — live OSM road retrieval unavailable. "
            "Hospital locations: Real OpenStreetMap data. "
            "Bridge positions are estimated on river crossings. "
            "Results are MODELED + COUNTERFACTUAL."
        ),
        "DEMO_FALLBACK": (
            "Running on a 12-node synthetic demo graph. "
            "No real OSM road data, hospitals, or bridges are used. "
            "For demonstration purposes only."
        ),
    }

    mode_descriptions = {
        "REAL_OSM":          "Full OpenStreetMap road network — genuine download",
        "PARTIAL_REAL_DATA": "Road network: Modeled fallback — live OSM road retrieval unavailable | Hospital locations: Real OpenStreetMap data",
        "DEMO_FALLBACK":     "Synthetic demo graph — no real data",
    }

    # ── Step 8: Build headline ─────────────────────────────────────────
    headline = None
    if counterfactual_results:
        top = counterfactual_results[0]
        best_change = None
        best_score  = -1

        for ch in top.get("changes", []):
            if ch.get("became_unreachable"):
                score = 10000 + (ch.get("baseline_travel_time_min") or 0)
            else:
                delta = ch.get("disruption_delta_min")
                score = float(delta) if delta is not None and delta != "UNREACHABLE" else 0

            if score > best_score:
                best_score = score
                best_change = ch

        if best_change:
            unreachable = best_change.get("became_unreachable", False)
            data_label_hl = (
                "MODELED + COUNTERFACTUAL (Real OSM Hospitals + Modeled Road Network)"
                if mode == "PARTIAL_REAL_DATA"
                else "COUNTERFACTUAL — MODELLED RESULT (Real OSM Road Network)"
                if mode == "REAL_OSM"
                else "COUNTERFACTUAL — DEMO RESULT"
            )
            provenance_note = (
                "Hospital: Real OSM | Road network: Modeled fallback — live OSM road retrieval unavailable"
                if mode == "PARTIAL_REAL_DATA"
                else "Hospital: Real OSM | Road network: Real OpenStreetMap (genuine download)"
                if mode == "REAL_OSM"
                else "Hospital: Demo estimate | Road network: Demo synthetic"
            )
            headline = {
                "asset_id": top["asset_id"],
                "asset_name": top["asset_name"],
                "origin_label": best_change["origin_label"],
                "dest_label":   best_change["dest_label"],
                "baseline_travel_time_min": best_change.get("baseline_travel_time_min"),
                "scenario_travel_time_min": None if unreachable else best_change.get("scenario_travel_time_min"),
                "disruption_delta_min": "UNREACHABLE" if unreachable else best_change.get("disruption_delta_min"),
                "became_unreachable": unreachable,
                "baseline_path": best_change.get("baseline_path", []),
                "scenario_path": best_change.get("scenario_path", []),
                "data_label": data_label_hl,
                "provenance_note": provenance_note,
            }

    # ── Step 9: Assemble full result ───────────────────────────────────
    result = {
        "mode": mode,
        "mode_description": mode_descriptions.get(mode, mode),
        "warning": warnings_map.get(mode),
        "dq_warning": warnings_map.get(mode),
        "graph_source": graph_source,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "total_bridges": total_bridges_count,
        "exposed_bridges": exposed_bridges_count,
        "analyzed_bridges": len(counterfactual_results),
        "bridges_detected": total_bridges_count,
        "bridges_analysed": len(counterfactual_results),
        "summary": summary,
        "cyclone_scenario": cyclone,
        "hospitals": [h.to_dict() for h in hosp_matched],
        "shelters":  [s.to_dict() for s in shelt_matched],
        "settlements": [s.to_dict() for s in sett_matched],
        "hospital_source": pois.get("hospital_source", "unknown"),
        "shelter_source":  pois.get("shelter_source",  "unknown"),
        "settlement_source": "ESTIMATED — not census data",
        "bridges": [
            {
                **b.to_dict(),
                "exposure": exposure_map.get(b.asset_id, {}).to_dict()
                            if b.asset_id in exposure_map else {},
            }
            for b in bridges
        ],
        "counterfactual_results": counterfactual_results,
        "top_priority_bridge": counterfactual_results[0]["asset_id"] if counterfactual_results else None,

        "headline": headline,
        "node_positions": _extract_node_positions(G),
        "data_labels": {
            "road_network": road_network_label,
            "bridges": bridge_label,
            "hospitals": hospital_label,
            "shelters": shelter_label,
            "population": "ESTIMATED / MODELED — not census microdata",
            "travel_time": "MODELED — road length / speed class assumption",
            "hazard_exposure": "MODELED — VSCS cyclone scenario analogue (not a forecast)",
            "counterfactual_results": "MODELED + COUNTERFACTUAL — scenario accessibility disruption",
            "priority_score": "MODELED + COUNTERFACTUAL — Exposure × Disruption × Criticality (geometric mean)",
        },
    }

    # Cache genuine scenario results (do not overwrite with a forced-synthetic run)
    if not force_synthetic:
        _RESULTS_CACHE.write_text(json.dumps(result, indent=2, default=str))
        logger.info("Scenario cached [%s]: %d bridges, %d counterfactual results",
                    mode, len(bridges), len(counterfactual_results))


    return result




def _extract_node_positions(G: nx.MultiDiGraph) -> Dict[int, Dict]:
    """Extract {node_id: {lat, lon, label}} — subsample for large graphs."""
    positions = {}
    for nid, data in G.nodes(data=True):
        positions[nid] = {
            "lat": data.get("y", 0),
            "lon": data.get("x", 0),
            "label": data.get("label", data.get("name", str(nid))),
        }
    return positions


def get_data_quality_report(result: dict) -> dict:
    """
    Build a data-quality summary for display in the UI.
    Explicitly distinguishes REAL from ESTIMATED from MODELLED.
    """
    mode = result["mode"]

    # Mode-specific warnings shown prominently in UI
    warnings_map = {
        "REAL_OSM": None,   # No warning — everything is genuine
        "PARTIAL_REAL_DATA": (
            "Road network is a modelled/synthetic graph using real geographic coordinates. "
            "Live OSM road-network download was unavailable. "
            "Hospital locations are REAL OpenStreetMap data. "
            "Bridge positions are ESTIMATED on known river-crossing corridors. "
            "Results are COUNTERFACTUAL — for decision-support only."
        ),
        "DEMO_FALLBACK": (
            "Running on a 12-node synthetic demo graph. "
            "No real OSM road data, hospitals, or bridges are used. "
            "For demonstration purposes only."
        ),
    }

    return {
        "graph_source": result["graph_source"],
        "mode": mode,
        "mode_description": {
            "REAL_OSM":          "Full OpenStreetMap road network — genuine download",
            "PARTIAL_REAL_DATA": "Hybrid: real hospital POIs + synthetic road topology",
            "DEMO_FALLBACK":     "Synthetic demo — no real data",
        }.get(mode, mode),
        "counts": {
            "road_nodes": result["node_count"],
            "road_edges": result["edge_count"],
            "total_bridges": result.get("total_bridges", result.get("bridges_detected", 0)),
            "exposed_bridges": result.get("exposed_bridges", result.get("bridges_detected", 0)),
            "bridges_found": result["bridges_detected"],
            "bridges_analysed": result["bridges_analysed"],
            "hospitals": len(result["hospitals"]),
            "shelters": len(result["shelters"]),
            "settlements": len(result["settlements"]),
        },
        "hazard_scenario": {
            "name": result.get("cyclone_scenario", {}).get("name"),
            "scenario_type": result.get("cyclone_scenario", {}).get("scenario_type"),
            "analogue_event": result.get("cyclone_scenario", {}).get("analogue_event"),
            "data_label": result.get("cyclone_scenario", {}).get("data_label"),
            "source": result.get("cyclone_scenario", {}).get("source"),
            "exposure_window": result.get("cyclone_scenario", {}).get("exposure_window"),
        },
        "data_labels": result["data_labels"],
        "warning": warnings_map.get(mode),
    }


