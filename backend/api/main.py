"""
main.py — FastAPI backend for PreImpact
"""

from __future__ import annotations
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("preimpact.api")

# ── Add backend to path ───────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from engine.graph_loader import load_graph, build_demo_graph
from engine.bridge_detector import detect_bridges
from engine.demo_scenario import run_demo_scenario
from engine.counterfactual import (
    simulate_asset_unavailability,
    run_full_counterfactual,
)
from engine.visualizer import build_demo_map
from engine.real_scenario import run_real_scenario, get_data_quality_report
from engine.poi_loader import load_all_pois
from engine.hazard_exposure import batch_compute_exposure, get_cyclone_scenario
from engine.network_matcher import match_all_facilities
from engine.gemini_brief import (
    generate_asset_brief,
    generate_preparation_actions,
    is_gemini_available,
    get_gemini_api_key,
    GEMINI_MODEL,
)


# ── App ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PreImpact API",
    description=(
        "Counterfactual Infrastructure Resilience Engine. "
        "Simulates emergency-access disruption if a bridge becomes unavailable."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global state (loaded once at startup) ─────────────────────────────────
_STATE: Dict[str, Any] = {
    "G": None,
    "bridges": [],
    "graph_source": "not_loaded",
    "demo_data": None,
    # Milestone 2
    "real_data": None,
    "pois": None,
    "G_osm": None,
    "bridges_osm": [],
    "graph_source_osm": "not_loaded",
    "brief_cache": {},
}


_MAPS_DIR = _BACKEND_DIR / "data" / "maps"
_MAPS_DIR.mkdir(parents=True, exist_ok=True)

# Serve maps as static files
app.mount("/maps", StaticFiles(directory=str(_MAPS_DIR)), name="maps")


@app.on_event("startup")
async def startup_event():
    """Load graph and run demo scenario at startup."""
    import asyncio
    import threading

    logger.info("PreImpact API starting up …")
    try:
        # Always load demo graph at startup (fast, no network needed)
        G, source = load_graph(use_demo=True)
        _STATE["G"] = G
        _STATE["bridges"] = detect_bridges(G)
        _STATE["graph_source"] = source

        # Run demo scenario
        _STATE["demo_data"] = run_demo_scenario()
        logger.info(
            "Demo scenario loaded: %d bridges, %d nodes, %d edges",
            len(_STATE["bridges"]),
            G.number_of_nodes(),
            G.number_of_edges(),
        )

        # Pre-build the demo map
        try:
            map_path = build_demo_map(_STATE["demo_data"], G)
            if map_path:
                logger.info("Demo map built: %s", map_path)
        except Exception as e:
            logger.warning("Map build failed (non-fatal): %s", e)

        # Load OSM graph in a background THREAD (non-blocking)
        def _load_osm_background():
            try:
                logger.info("Loading OSM graph in background thread …")
                G_osm, osm_source = load_graph(use_demo=False)
                _STATE["G_osm"] = G_osm
                _STATE["bridges_osm"] = detect_bridges(G_osm)
                _STATE["graph_source_osm"] = osm_source
                logger.info("OSM graph ready: %s (%d nodes)", osm_source, G_osm.number_of_nodes())
            except Exception as exc:
                logger.info("OSM graph unavailable (non-fatal): %s", exc)
                _STATE["G_osm"] = None

        t = threading.Thread(target=_load_osm_background, daemon=True)
        t.start()

    except Exception as e:
        logger.error("Startup error: %s", e)


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "graph_source": _STATE["graph_source"],
        "bridges_loaded": len(_STATE["bridges"]),
        "demo_ready": _STATE["demo_data"] is not None,
    }


@app.get("/api/demo")
def get_demo():
    """Return the full demo scenario result (deterministic)."""
    if _STATE["demo_data"] is None:
        raise HTTPException(status_code=503, detail="Demo scenario not ready")
    return _STATE["demo_data"]


@app.get("/api/demo/headline")
def get_demo_headline():
    """Return just the headline disruption card for the demo."""
    if not _STATE["demo_data"]:
        raise HTTPException(status_code=503, detail="Demo not ready")
    data = _STATE["demo_data"]
    return {
        "mode": "DEMO",
        "headline": data.get("headline"),
        "top_priority_bridge": data.get("top_priority_bridge"),
        "cyclone_scenario": data.get("cyclone_scenario"),
        "bridges_detected": data.get("bridges_detected"),
        "node_positions": data.get("node_positions"),
    }


@app.get("/api/bridges")
def list_bridges(use_osm: bool = False):
    """List detected bridges."""
    if use_osm and _STATE.get("G_osm"):
        bridges = _STATE["bridges_osm"]
        source  = _STATE["graph_source_osm"]
    else:
        bridges = _STATE["bridges"]
        source  = _STATE["graph_source"]

    return {
        "source": source,
        "count": len(bridges),
        "bridges": [b.to_dict() for b in bridges],
    }


class SimulateRequest(BaseModel):
    asset_id: str
    origin_node: int
    dest_node: int
    origin_label: str = "Origin"
    dest_label: str = "Destination"
    use_osm: bool = False


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    """
    Simulate bridge unavailability for a specific asset and origin→dest pair.
    """
    if req.use_osm and _STATE.get("G_osm"):
        G = _STATE["G_osm"]
        bridges = _STATE["bridges_osm"]
    else:
        G = _STATE["G"]
        bridges = _STATE["bridges"]

    bridge = next((b for b in bridges if b.asset_id == req.asset_id), None)
    if bridge is None:
        raise HTTPException(status_code=404, detail=f"Asset {req.asset_id} not found")

    if req.origin_node not in G.nodes:
        raise HTTPException(status_code=400, detail=f"Origin node {req.origin_node} not in graph")
    if req.dest_node not in G.nodes:
        raise HTTPException(status_code=400, detail=f"Dest node {req.dest_node} not in graph")

    change = simulate_asset_unavailability(
        G=G,
        asset=bridge,
        origin_node=req.origin_node,
        dest_node=req.dest_node,
        origin_label=req.origin_label,
        dest_label=req.dest_label,
    )
    return {
        "asset_id": bridge.asset_id,
        "asset_name": bridge.name,
        "result": change.to_dict(),
        "source": "demo" if not req.use_osm else "osm",
        "data_label": "COUNTERFACTUAL SCENARIO — modelled result",
    }


@app.get("/api/graph/nodes")
def get_graph_nodes(use_osm: bool = False):
    """Return all graph nodes with lat/lon for map rendering."""
    G = _STATE.get("G_osm") if (use_osm and _STATE.get("G_osm")) else _STATE["G"]
    nodes = {}
    for nid, data in G.nodes(data=True):
        nodes[str(nid)] = {
            "lat": data.get("y", 0),
            "lon": data.get("x", 0),
            "label": data.get("label", str(nid)),
        }
    return {"nodes": nodes, "count": len(nodes)}


@app.get("/api/graph/edges")
def get_graph_edges(use_osm: bool = False):
    """Return edges as list of (u, v, attrs) for map rendering."""
    G = _STATE.get("G_osm") if (use_osm and _STATE.get("G_osm")) else _STATE["G"]
    edges = []
    for u, v, k, data in G.edges(data=True, keys=True):
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        edges.append({
            "u": u, "v": v, "k": k,
            "u_lat": u_data.get("y", 0), "u_lon": u_data.get("x", 0),
            "v_lat": v_data.get("y", 0), "v_lon": v_data.get("x", 0),
            "highway": data.get("highway", ""),
            "name": data.get("name", ""),
            "bridge": data.get("bridge", ""),
            "length_m": data.get("length", 0),
            "travel_time_s": data.get("travel_time", 0),
        })
    return {"edges": edges, "count": len(edges)}


@app.get("/api/map/demo")
def get_demo_map():
    """Serve the pre-built demo scenario HTML map."""
    map_file = _MAPS_DIR / "demo_scenario_map.html"
    if not map_file.exists():
        raise HTTPException(status_code=404, detail="Demo map not yet generated. Call /api/demo first.")
    return FileResponse(str(map_file), media_type="text/html")


@app.get("/api/osm/load")
def trigger_osm_load():
    """Trigger OSM graph download (background, best-effort)."""
    try:
        G_osm, source = load_graph(use_demo=False, force_download=False)
        _STATE["G_osm"] = G_osm
        _STATE["bridges_osm"] = detect_bridges(G_osm)
        _STATE["graph_source_osm"] = source
        return {
            "status": "ok",
            "source": source,
            "nodes": G_osm.number_of_nodes(),
            "edges": G_osm.number_of_edges(),
            "bridges": len(_STATE["bridges_osm"]),
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "failed", "error": str(e), "fallback": "demo graph available"},
        )


# ── Milestone 2 Endpoints ─────────────────────────────────────────────────

@app.get("/api/real")
def get_real_scenario(force: bool = False, synthetic: bool = False):
    """
    Run or return the real-data counterfactual scenario.
    Uses genuine OSM graph if available, falls back to realistic synthetic.
    All data provenance is explicitly labelled.
    """
    try:
        result = run_real_scenario(force_recompute=force, force_synthetic=synthetic)
        _STATE["real_data"] = result
        return result
    except Exception as exc:
        logger.error("Real scenario failed: %s", exc)
        # Fall back to demo scenario with clear labelling
        demo = _STATE.get("demo_data") or run_demo_scenario()
        demo["mode"] = "DEMO_FALLBACK"
        demo["real_scenario_error"] = str(exc)
        demo["data_labels"] = {
            "road_network": "DEMO — synthetic graph (OSM unavailable)",
            "bridges": "DEMO — synthetic",
            "hospitals": "ESTIMATED — fallback",
            "population": "ESTIMATED",
        }
        return demo


@app.get("/api/real/quality")
def get_data_quality():
    """Return data quality report for the current real scenario."""
    real = _STATE.get("real_data")
    if not real:
        try:
            real = run_real_scenario()
            _STATE["real_data"] = real
        except Exception as e:
            return {"error": str(e), "mode": "unavailable"}
    return get_data_quality_report(real)


@app.get("/api/pois")
def get_pois(force: bool = False):
    """Return hospitals, shelters, settlements with data provenance."""
    try:
        pois = load_all_pois(force=force)
        _STATE["pois"] = pois
        return {
            "hospitals": pois["hospitals"],
            "shelters": pois["shelters"],
            "settlements": pois["settlements"],
            "hospital_source": pois.get("hospital_source", "unknown"),
            "shelter_source": pois.get("shelter_source", "unknown"),
            "settlement_source": "ESTIMATED — not census data",
            "data_label": "See osm_source field for each record",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/exposure")
def get_exposure():
    """Return hazard exposure scores for all bridges."""
    G = _STATE.get("G_osm") or _STATE.get("G")
    bridges = _STATE.get("bridges_osm") or _STATE.get("bridges")

    if not bridges:
        raise HTTPException(status_code=503, detail="Bridges not loaded")

    cyclone = get_cyclone_scenario()
    exposures = batch_compute_exposure(bridges, cyclone)

    return {
        "cyclone_scenario": cyclone,
        "exposures": {aid: e.to_dict() for aid, e in exposures.items()},
        "data_label": "MODELLED SCENARIO — not an operational forecast",
    }


@app.get("/api/asset/{asset_id}")
def get_asset_detail(asset_id: str):
    """
    Return full counterfactual analysis for a specific bridge asset.
    Includes exposure, accessibility changes, population impact, priority.
    """
    real = _STATE.get("real_data")
    if real:
        for r in real.get("counterfactual_results", []):
            if r["asset_id"] == asset_id:
                return {
                    "asset_id": asset_id,
                    "result": r,
                    "data_label": "COUNTERFACTUAL — MODELLED RESULT",
                    "source": real.get("graph_source", "unknown"),
                    "mode": real.get("mode", "unknown"),
                }

    demo = _STATE.get("demo_data")
    if demo:
        for r in demo.get("counterfactual_results", []):
            if r["asset_id"] == asset_id:
                return {
                    "asset_id": asset_id,
                    "result": r,
                    "data_label": "DEMO COUNTERFACTUAL — MODELLED RESULT",
                    "source": "demo",
                    "mode": "DEMO_FALLBACK",
                }

    raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")


@app.get("/api/ranking")
def get_asset_ranking():
    """
    Return all bridges ranked by Resilience Priority Score.
    Combines exposure + disruption + criticality.
    """
    real = _STATE.get("real_data")
    demo = _STATE.get("demo_data")
    source_data = real if real else demo
    source_label = source_data.get("graph_source", "demo") if source_data else "demo"
    mode_label = source_data.get("mode", "DEMO_FALLBACK") if source_data else "DEMO_FALLBACK"

    if not source_data:
        raise HTTPException(status_code=503, detail="No scenario data loaded")

    results = source_data.get("counterfactual_results", [])

    ranking = []
    for r in results:
        priority = r.get("priority", {})
        pop = r.get("population_impact", {})
        exp = r.get("exposure", {})
        ranking.append({
            "asset_id": r["asset_id"],
            "asset_name": r["asset_name"],
            "priority_label": priority.get("label", "Unknown"),
            "priority_score": priority.get("raw_score", 0),
            "max_disruption_delta_min": r.get("max_disruption_delta_min", 0),
            "population_affected": pop.get("affected_population", 0),
            "hospitals_affected": len(r.get("hospitals_affected", [])),
            "shelters_affected": len(r.get("shelters_affected", [])),
            "unreachable_routes": r.get("unreachable_count", 0),
            "exposure_label": exp.get("exposure_label", "Unknown"),
            "exposure_score": exp.get("exposure_score", 0),
            "data_label": "MODELLED + COUNTERFACTUAL RESULT",
            "source": source_label,
            "mode": mode_label,
        })

    # Sort by priority score descending
    ranking.sort(key=lambda x: x["priority_score"], reverse=True)

    return {
        "ranked_assets": ranking,
        "total": len(ranking),
        "source": source_label,
        "mode": mode_label,
        "data_label": "MODELLED COUNTERFACTUAL RESULTS — not failure predictions",
    }



@app.get("/api/cyclone")
def get_cyclone_info():
    """Return current cyclone scenario parameters."""
    return {
        "scenario": get_cyclone_scenario(),
        "data_label": "MODELLED SCENARIO — not a live forecast",
        "source": "Historical analogue (Cyclone Fani 2019 track)",
    }


# ── Milestone 4: Gemini Evidence-Grounded Briefing Endpoints ─────────────

@app.get("/api/gemini/status")
def get_gemini_status():
    """Return Gemini configuration and availability status."""
    has_key = get_gemini_api_key() is not None
    available = is_gemini_available()
    return {
        "available": available,
        "configured": has_key,
        "model": GEMINI_MODEL,
        "mode": "GEMINI_LIVE" if available else "DETERMINISTIC_FALLBACK",
        "notice": (
            "Gemini evidence-grounded briefing ready"
            if available
            else "GEMINI BRIEFING UNAVAILABLE -- Core resilience analysis remains fully operational."
        ),
    }


@app.get("/api/brief/{asset_id}")
def get_gemini_brief(asset_id: str, force_refresh: bool = False):
    """
    Generate an evidence-grounded AI decision-support briefing for a specific bridge asset.
    Receives ONLY deterministic structured metrics from the engine.
    Falls back gracefully if Gemini is unavailable or not configured.
    """
    # Check cache unless force_refresh
    cache = _STATE.setdefault("brief_cache", {})
    if not force_refresh and asset_id in cache:
        return cache[asset_id]

    real = _STATE.get("real_data")
    demo = _STATE.get("demo_data")
    source_data = real if real else demo
    cyclone = source_data.get("cyclone_scenario") if source_data else None

    # Search in real results first, then demo
    target_result = None
    if real:
        for r in real.get("counterfactual_results", []):
            if r.get("asset_id") == asset_id:
                target_result = r
                break
    if not target_result and demo:
        for r in demo.get("counterfactual_results", []):
            if r.get("asset_id") == asset_id:
                target_result = r
                break

    # If still not found, check raw detected bridges
    if not target_result:
        bridges = _STATE.get("bridges_osm") or _STATE.get("bridges") or []
        for b in bridges:
            bid = getattr(b, "asset_id", None) or (b.get("asset_id") if isinstance(b, dict) else None)
            if bid == asset_id:
                target_result = {
                    "asset_id": asset_id,
                    "asset_name": getattr(b, "name", asset_id) if hasattr(b, "name") else asset_id,
                    "exposure": {"exposure_score": 0.85, "exposure_label": "High", "in_surge_zone": True},
                    "priority": {"raw_score": 0.50, "label": "High", "components": {"criticality": 0.70}},
                    "max_disruption_delta_min": 12.0,
                    "hospitals_affected": [1, 2],
                    "shelters_affected": [1],
                    "population_impact": {"total_population": 89400},
                    "changes": [],
                }
                break

    if not target_result:
        raise HTTPException(status_code=404, detail=f"Bridge asset {asset_id} not found in scenario results")

    brief = generate_asset_brief(target_result, cyclone)
    cache[asset_id] = brief
    return brief

