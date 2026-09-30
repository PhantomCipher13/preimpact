"""
visualizer.py
=============
Generate Folium HTML map visualizations for PreImpact.

Outputs:
- An interactive Leaflet map showing:
  * road network
  * bridge location (highlighted)
  * baseline route (blue)
  * counterfactual/alternate route (orange dashed)
  * hospitals (red cross marker)
  * shelters (green triangle)
  * settlements (grey circle)

The map is saved as an HTML file for embedding in the dashboard or
serving standalone.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path(__file__).parent.parent / "data" / "maps"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _check_folium():
    try:
        import folium
        return folium
    except ImportError:
        logger.error("folium not installed. Run: pip install folium")
        return None


def _node_coords(G: nx.MultiDiGraph, node_id: int) -> Tuple[float, float]:
    """Return (lat, lon) for a node."""
    data = G.nodes[node_id]
    return data.get("y", 0), data.get("x", 0)


def _path_coords(G: nx.MultiDiGraph, path_nodes: List[int]) -> List[Tuple[float, float]]:
    """Convert a list of node IDs to [(lat, lon), …]."""
    return [_node_coords(G, n) for n in path_nodes if n in G.nodes]


def build_scenario_map(
    G: nx.MultiDiGraph,
    bridge_asset,                    # BridgeAsset
    baseline_path: List[int],
    scenario_path: List[int],
    hospital_nodes: List[Tuple[int, str]],
    shelter_nodes:  List[Tuple[int, str]],
    settlement_nodes: List[Tuple[int, str, int]],  # (node, label, pop)
    cf_result=None,
    output_filename: str = "scenario_map.html",
) -> str:
    """
    Build and save an interactive Folium map.

    Returns the absolute path to the saved HTML file.
    """
    folium = _check_folium()
    if folium is None:
        return ""

    # Centre on bridge midpoint
    centre = [bridge_asset.midpoint_lat, bridge_asset.midpoint_lon]

    m = folium.Map(location=centre, zoom_start=12, tiles="OpenStreetMap")

    # ── Road network (thin grey lines for all edges) ──────────────────
    edge_group = folium.FeatureGroup(name="Road Network", show=True)
    for u, v, data in G.edges(data=True):
        u_lat, u_lon = _node_coords(G, u)
        v_lat, v_lon = _node_coords(G, v)
        folium.PolyLine(
            [(u_lat, u_lon), (v_lat, v_lon)],
            color="#aaaaaa",
            weight=1.5,
            opacity=0.5,
            tooltip=data.get("name", ""),
        ).add_to(edge_group)
    edge_group.add_to(m)

    # ── Baseline route (blue) ─────────────────────────────────────────
    if baseline_path:
        baseline_coords = _path_coords(G, baseline_path)
        if len(baseline_coords) >= 2:
            folium.PolyLine(
                baseline_coords,
                color="#1565C0",
                weight=5,
                opacity=0.85,
                tooltip="Baseline route (bridge available)",
            ).add_to(m)

    # ── Scenario route (orange dashed) ────────────────────────────────
    if scenario_path:
        scenario_coords = _path_coords(G, scenario_path)
        if len(scenario_coords) >= 2:
            folium.PolyLine(
                scenario_coords,
                color="#E65100",
                weight=5,
                opacity=0.85,
                dash_array="10 5",
                tooltip=f"Alternate route — bridge {bridge_asset.name} unavailable",
            ).add_to(m)

    # ── Bridge marker (red X) ─────────────────────────────────────────
    bridge_icon = folium.Icon(color="red", icon="ban", prefix="fa")
    popup_html = f"""
    <b>{bridge_asset.asset_id}: {bridge_asset.name}</b><br>
    Highway: {bridge_asset.highway_type}<br>
    Length: {bridge_asset.length_m:.0f} m<br>
    Exposure: {bridge_asset.exposure_level}<br>
    <i>COUNTERFACTUAL: removed in scenario</i>
    """
    folium.Marker(
        location=[bridge_asset.midpoint_lat, bridge_asset.midpoint_lon],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=f"⚠ {bridge_asset.asset_id}: {bridge_asset.name}",
        icon=bridge_icon,
    ).add_to(m)

    # ── Hospitals ─────────────────────────────────────────────────────
    for node_id, hosp_name in hospital_nodes:
        lat, lon = _node_coords(G, node_id)
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(f"<b>🏥 {hosp_name}</b>", max_width=200),
            tooltip=f"🏥 {hosp_name}",
            icon=folium.Icon(color="red", icon="plus-sign", prefix="glyphicon"),
        ).add_to(m)

    # ── Shelters ──────────────────────────────────────────────────────
    for node_id, shelter_name in shelter_nodes:
        lat, lon = _node_coords(G, node_id)
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(f"<b>🏠 {shelter_name}</b>", max_width=200),
            tooltip=f"🏠 {shelter_name}",
            icon=folium.Icon(color="green", icon="home", prefix="glyphicon"),
        ).add_to(m)

    # ── Settlements ───────────────────────────────────────────────────
    for entry in settlement_nodes:
        node_id, s_name = entry[0], entry[1]
        pop = entry[2] if len(entry) > 2 else None
        lat, lon = _node_coords(G, node_id)
        pop_text = f"<br>Est. population: {pop:,}" if pop else ""
        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            color="#555555",
            fill=True,
            fill_color="#ffcc00",
            fill_opacity=0.8,
            popup=folium.Popup(
                f"<b>{s_name}</b>{pop_text}<br><i>ESTIMATED population</i>",
                max_width=250,
            ),
            tooltip=s_name,
        ).add_to(m)

    # ── Disruption summary box ─────────────────────────────────────────
    if cf_result:
        delta = cf_result.max_disruption_delta_min
        delta_str = f"+{delta:.1f} min" if delta < float("inf") else "UNREACHABLE"
        legend_html = f"""
        <div style="
            position: fixed;
            bottom: 50px; left: 50px;
            background-color: white;
            padding: 12px 16px;
            border-radius: 8px;
            border: 2px solid #333;
            font-family: Arial, sans-serif;
            font-size: 13px;
            z-index: 9999;
            max-width: 260px;
        ">
        <b>🔴 PREIMPACT — Counterfactual Scenario</b><br>
        <b>Asset:</b> {cf_result.asset_name}<br>
        <b>Max disruption:</b> {delta_str}<br>
        <b>Hospitals affected:</b> {len(cf_result.hospitals_affected)}<br>
        <b>Shelters affected:</b> {len(cf_result.shelters_affected)}<br>
        <hr style="margin:4px 0">
        <span style="color:#1565C0">━━━</span> Baseline route<br>
        <span style="color:#E65100">- - -</span> Alternate route<br>
        <span style="color:red">✖</span> Counterfactual bridge<br>
        <i style="font-size:11px; color:#666">
            MODELLED COUNTERFACTUAL — not structural failure prediction
        </i>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

    # Layer control
    folium.LayerControl().add_to(m)

    output_path = _OUTPUT_DIR / output_filename
    m.save(str(output_path))
    logger.info("Map saved to %s", output_path)
    return str(output_path)


def build_demo_map(demo_data: dict, G: nx.MultiDiGraph) -> str:
    """
    Build a map from the output of run_demo_scenario().
    """
    from .bridge_detector import BridgeAsset

    if not demo_data.get("counterfactual_results"):
        logger.warning("No counterfactual results in demo_data.")
        return ""

    top_result_dict = demo_data["counterfactual_results"][0]
    headline = demo_data.get("headline", {})

    # Reconstruct a minimal BridgeAsset for visualisation
    bridge_info = next(
        (b for b in demo_data["bridges"] if b["asset_id"] == top_result_dict["asset_id"]),
        demo_data["bridges"][0],
    )
    asset = BridgeAsset(
        asset_id=bridge_info["asset_id"],
        name=bridge_info["name"],
        edge_keys=[],   # Not needed for visualisation
        midpoint_lat=bridge_info["midpoint_lat"],
        midpoint_lon=bridge_info["midpoint_lon"],
        highway_type=bridge_info["highway_type"],
        length_m=bridge_info["length_m"],
    )

    class _FakeResult:
        asset_name = top_result_dict["asset_name"]
        max_disruption_delta_min = top_result_dict["max_disruption_delta_min"]
        hospitals_affected = top_result_dict["hospitals_affected"]
        shelters_affected  = top_result_dict["shelters_affected"]

    settlements = demo_data["settlements"]
    settlement_nodes = [(s["node_id"], s["name"], s["population_estimate"]) for s in settlements]
    hospital_nodes   = [(h["node_id"], h["name"]) for h in demo_data["hospitals"]]
    shelter_nodes    = [(s["node_id"], s["name"]) for s in demo_data["shelters"]]

    return build_scenario_map(
        G=G,
        bridge_asset=asset,
        baseline_path=headline.get("baseline_path", []),
        scenario_path=headline.get("scenario_path", []),
        hospital_nodes=hospital_nodes,
        shelter_nodes=shelter_nodes,
        settlement_nodes=settlement_nodes,
        cf_result=_FakeResult(),
        output_filename="demo_scenario_map.html",
    )
