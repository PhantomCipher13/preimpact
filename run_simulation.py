"""
run_simulation.py
=================
CLI entry-point: Run the PreImpact demo simulation and print results.

Usage:
    python run_simulation.py
    python run_simulation.py --demo
    python run_simulation.py --osm
    python run_simulation.py --map
"""
from __future__ import annotations
import io, sys
# Force UTF-8 output on Windows so Unicode symbols display correctly
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
import logging
from pathlib import Path


_BACKEND = Path(__file__).parent / "backend"
sys.path.insert(0, str(_BACKEND))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("preimpact")


def print_separator(char="─", width=60):
    print(char * width)


def print_result_card(demo_data: dict):
    print()
    print("=" * 60)
    print("  PREIMPACT — Counterfactual Infrastructure Resilience Engine")
    print("=" * 60)
    print()

    cyclone = demo_data.get("cyclone_scenario", {})
    print(f"  Cyclone Scenario : {cyclone.get('name', 'N/A')}")
    print(f"  Region           : Kendrapara, Odisha (coastal)")
    print(f"  Graph source     : {demo_data['graph_source'].upper()}")
    print(f"  Nodes            : {demo_data['node_count']}")
    print(f"  Edges            : {demo_data['edge_count']}")
    print(f"  Bridges detected : {demo_data['bridges_detected']}")
    print(f"  Data label       : {demo_data['data_label']}")
    print()

    headline = demo_data.get("headline")
    if headline:
        print_separator()
        print("  TOP DISRUPTION SCENARIO")
        print_separator()
        print(f"  Asset            : {demo_data['top_priority_bridge']}")
        print(f"  Origin → Dest    : {headline['origin_label']} → {headline['dest_label']}")
        print()
        if headline.get("baseline_travel_time_min") is not None:
            print(f"  Normal travel    : {headline['baseline_travel_time_min']:.1f} min")
        if headline.get("became_unreachable"):
            print(f"  If unavailable   : ⛔ DESTINATION UNREACHABLE")
            print(f"  Disruption       : COMPLETE ISOLATION")
        elif headline.get("scenario_travel_time_min") is not None:
            print(f"  If unavailable   : {headline['scenario_travel_time_min']:.1f} min")
            delta = headline.get("disruption_delta_min", 0)
            print(f"  Disruption Δ     : ▲ +{delta:.1f} minutes")
        print()

    results = demo_data.get("counterfactual_results", [])
    if results:
        print_separator()
        print("  BRIDGE PRIORITY RANKING")
        print_separator()
        for i, r in enumerate(results, 1):
            priority = r.get("priority", {})
            pop = r.get("population_impact", {})
            label = priority.get("label", "?")
            score = priority.get("raw_score", 0)
            affected_pop = pop.get("affected_population", 0)
            print(
                f"  [{i}] {r['asset_id']:6s} {r['asset_name'][:30]:30s}"
                f"  Δ={r['max_disruption_delta_min']:5.1f}min"
                f"  Priority={label:8s} ({score:.2f})"
                f"  Pop≈{affected_pop:,}"
            )
        print()

    print_separator()
    print()
    print("  NOTE: This is a COUNTERFACTUAL SCENARIO, not a failure prediction.")
    print("  All values are MODELLED ESTIMATES.")
    print("  This tool helps responders PREPARE for potential disruptions.")
    print()
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="PreImpact — Counterfactual Infrastructure Resilience Engine"
    )
    parser.add_argument("--demo", action="store_true", help="Use deterministic demo graph (default)")
    parser.add_argument("--osm",  action="store_true", help="Try to download/load OSM graph")
    parser.add_argument("--map",  action="store_true", help="Generate an HTML map")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    from engine.graph_loader import load_graph
    from engine.bridge_detector import detect_bridges
    from engine.demo_scenario import run_demo_scenario
    from engine.visualizer import build_demo_map

    print("\n  Loading graph …")
    use_demo = not args.osm
    G, source = load_graph(use_demo=use_demo)
    bridges = detect_bridges(G)
    print(f"  Graph loaded from: {source}  ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")
    print(f"  Bridges detected: {len(bridges)}")

    print("  Running demo scenario …")
    demo_data = run_demo_scenario()

    print_result_card(demo_data)

    if args.map:
        print("  Building map …")
        map_path = build_demo_map(demo_data, G)
        if map_path:
            print(f"  Map saved to: {map_path}")
            print("  Open in your browser to view the interactive map.")
        else:
            print("  Map generation failed (check folium installation).")


if __name__ == "__main__":
    main()
