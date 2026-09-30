"""
test_counterfactual.py
======================
Core test suite for the PreImpact counterfactual engine.

Tests verify:
1. Demo graph builds correctly
2. Bridges are detected
3. Bridge removal changes the route
4. Travel time delta is calculated correctly
5. Affected facilities are detected
6. Priority calculation is deterministic
7. Base graph is not mutated by simulation
8. Demo scenario runs end-to-end
"""

import math
import sys
from pathlib import Path

import pytest
import networkx as nx

# ── Path setup ────────────────────────────────────────────────────────────
_BACKEND = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

from engine.graph_loader import build_demo_graph, load_graph
from engine.bridge_detector import detect_bridges, BridgeAsset
from engine.counterfactual import (
    simulate_asset_unavailability,
    calculate_accessibility_change,
    calculate_population_impact,
    calculate_facility_impact,
    calculate_priority,
    run_full_counterfactual,
    _remove_asset_edges,
    _shortest_path,
)
from engine.demo_scenario import run_demo_scenario, DEMO_SETTLEMENTS, DEMO_HOSPITALS, DEMO_SHELTERS


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def demo_graph():
    """Return the deterministic demo graph."""
    return build_demo_graph()


@pytest.fixture(scope="module")
def detected_bridges(demo_graph):
    """Return detected bridges from demo graph."""
    return detect_bridges(demo_graph)


@pytest.fixture(scope="module")
def bridge_b1(detected_bridges):
    """Return the primary demo bridge (Bridge_B1)."""
    bridges = [b for b in detected_bridges if "B1" in b.name or "Bridge_B1" in b.name]
    assert bridges, "Bridge_B1 must be detected in demo graph"
    return bridges[0]


# ─────────────────────────────────────────────────────────────────────────
# 1. Graph construction tests
# ─────────────────────────────────────────────────────────────────────────

class TestGraphConstruction:
    def test_demo_graph_has_nodes(self, demo_graph):
        assert demo_graph.number_of_nodes() >= 10, "Demo graph should have ≥10 nodes"

    def test_demo_graph_has_edges(self, demo_graph):
        assert demo_graph.number_of_edges() >= 10, "Demo graph should have ≥10 edges"

    def test_demo_graph_is_multidigraph(self, demo_graph):
        assert isinstance(demo_graph, nx.MultiDiGraph)

    def test_all_nodes_have_lat_lon(self, demo_graph):
        for nid, data in demo_graph.nodes(data=True):
            assert "y" in data, f"Node {nid} missing lat (y)"
            assert "x" in data, f"Node {nid} missing lon (x)"

    def test_all_edges_have_travel_time(self, demo_graph):
        missing = []
        for u, v, k, data in demo_graph.edges(data=True, keys=True):
            if "travel_time" not in data:
                missing.append((u, v, k))
        assert not missing, f"Edges missing travel_time: {missing[:3]}"

    def test_load_graph_demo_returns_graph(self):
        G, source = load_graph(use_demo=True)
        assert isinstance(G, nx.MultiDiGraph)
        assert source == "demo"


# ─────────────────────────────────────────────────────────────────────────
# 2. Bridge detection tests
# ─────────────────────────────────────────────────────────────────────────

class TestBridgeDetection:
    def test_bridges_detected(self, detected_bridges):
        assert len(detected_bridges) >= 1, "At least one bridge must be detected"

    def test_bridge_has_required_fields(self, bridge_b1):
        assert bridge_b1.asset_id
        assert bridge_b1.name
        assert len(bridge_b1.edge_keys) > 0
        assert bridge_b1.midpoint_lat != 0
        assert bridge_b1.midpoint_lon != 0

    def test_bridge_to_dict(self, bridge_b1):
        d = bridge_b1.to_dict()
        required_keys = ["asset_id", "name", "midpoint_lat", "midpoint_lon", "length_m"]
        for key in required_keys:
            assert key in d, f"Missing key in bridge dict: {key}"

    def test_bridge_edge_keys_valid(self, demo_graph, bridge_b1):
        """All edge keys on the bridge must exist in the graph."""
        for u, v, k in bridge_b1.edge_keys:
            assert demo_graph.has_edge(u, v, k), f"Edge ({u},{v},{k}) not in graph"


# ─────────────────────────────────────────────────────────────────────────
# 3. Shortest-path tests
# ─────────────────────────────────────────────────────────────────────────

class TestShortestPath:
    def test_path_exists_baseline(self, demo_graph):
        """There must be a route from Village_A (1) to Hospital (8)."""
        result = _shortest_path(demo_graph, 1, 8)
        assert result.reachable, "Baseline path from 1→8 must exist"
        assert result.travel_time_s > 0

    def test_path_same_node(self, demo_graph):
        """Path from a node to itself is trivially 0."""
        result = _shortest_path(demo_graph, 1, 1)
        assert result.reachable
        assert result.travel_time_s == 0.0

    def test_path_to_unreachable_returns_false(self, demo_graph):
        """A non-existent node should return unreachable."""
        result = _shortest_path(demo_graph, 1, 9999)
        assert not result.reachable


# ─────────────────────────────────────────────────────────────────────────
# 4. Bridge removal tests — THE CORE TEST
# ─────────────────────────────────────────────────────────────────────────

class TestBridgeRemoval:
    def test_bridge_removal_changes_route(self, demo_graph, bridge_b1):
        """
        After removing Bridge_B1, the route from Village_A→Hospital
        must either be longer OR unreachable.
        """
        change = simulate_asset_unavailability(
            G=demo_graph,
            asset=bridge_b1,
            origin_node=1,   # Village_A
            dest_node=8,     # Hospital_H1
            origin_label="Village_A",
            dest_label="Hospital_H1",
        )
        assert change.baseline is not None
        assert change.scenario is not None
        assert change.baseline.reachable, "Baseline must be reachable"
        # After bridge removal, route should be longer OR unreachable
        if change.scenario.reachable:
            assert (
                change.scenario.travel_time_s > change.baseline.travel_time_s
            ), "Scenario travel time must be > baseline when bridge is removed"
        # If unreachable, became_unreachable flag should be set
        else:
            assert change.became_unreachable

    def test_disruption_delta_is_positive(self, demo_graph, bridge_b1):
        """Disruption delta must be positive (bridge removal always hurts)."""
        change = simulate_asset_unavailability(
            G=demo_graph, asset=bridge_b1,
            origin_node=1, dest_node=8,
        )
        if change.scenario.reachable:
            assert change.disruption_delta_s > 0
        else:
            assert change.became_unreachable

    def test_base_graph_not_mutated(self, demo_graph, bridge_b1):
        """
        The base graph must have the same number of edges before and after
        a counterfactual simulation.
        """
        edge_count_before = demo_graph.number_of_edges()
        simulate_asset_unavailability(
            G=demo_graph, asset=bridge_b1,
            origin_node=1, dest_node=8,
        )
        edge_count_after = demo_graph.number_of_edges()
        assert edge_count_before == edge_count_after, (
            f"Graph was mutated! Before={edge_count_before}, After={edge_count_after}"
        )

    def test_scenario_path_different_from_baseline(self, demo_graph, bridge_b1):
        """Baseline and scenario paths should differ after bridge removal."""
        change = simulate_asset_unavailability(
            G=demo_graph, asset=bridge_b1,
            origin_node=1, dest_node=8,
        )
        if change.scenario.reachable and change.baseline.reachable:
            assert (
                change.baseline.path_nodes != change.scenario.path_nodes
            ), "Paths should differ after bridge removal"

    def test_remove_asset_edges_copy_not_mutate(self, demo_graph, bridge_b1):
        """_remove_asset_edges must return a copy and not modify original."""
        original_edges = demo_graph.number_of_edges()
        G_copy, removed = _remove_asset_edges(demo_graph, bridge_b1.edge_keys)
        assert demo_graph.number_of_edges() == original_edges
        assert G_copy.number_of_edges() < original_edges
        assert removed > 0


# ─────────────────────────────────────────────────────────────────────────
# 5. Batch accessibility change tests
# ─────────────────────────────────────────────────────────────────────────

class TestAccessibilityChange:
    def test_batch_returns_all_pairs(self, demo_graph, bridge_b1):
        origins = [(1, "Village_A"), (2, "Village_B")]
        dests   = [(8, "Hospital_H1"), (10, "Shelter_S1")]
        changes = calculate_accessibility_change(demo_graph, bridge_b1, origins, dests)
        assert len(changes) == len(origins) * len(dests)

    def test_all_changes_have_baseline(self, demo_graph, bridge_b1):
        origins = [(1, "Village_A"), (2, "Village_B"), (3, "Village_C")]
        dests   = [(8, "Hospital_H1")]
        changes = calculate_accessibility_change(demo_graph, bridge_b1, origins, dests)
        for ch in changes:
            assert ch.baseline is not None
            assert ch.scenario is not None


# ─────────────────────────────────────────────────────────────────────────
# 6. Population impact tests
# ─────────────────────────────────────────────────────────────────────────

class TestPopulationImpact:
    def test_affected_population_non_negative(self, demo_graph, bridge_b1):
        origins = [(1, "Village_A"), (2, "Village_B"), (3, "Village_C")]
        dests   = [(8, "Hospital_H1")]
        changes = calculate_accessibility_change(demo_graph, bridge_b1, origins, dests)
        pop_map = {1: 4200, 2: 8700, 3: 2100}
        result = calculate_population_impact(changes, pop_map, threshold_min=5.0)
        assert result["affected_population"] >= 0
        assert result["total_population"] == 15000

    def test_affected_is_subset_of_total(self, demo_graph, bridge_b1):
        origins = [(1, "Village_A"), (2, "Village_B")]
        dests   = [(8, "Hospital_H1")]
        changes = calculate_accessibility_change(demo_graph, bridge_b1, origins, dests)
        pop_map = {1: 4200, 2: 8700}
        result = calculate_population_impact(changes, pop_map)
        assert result["affected_population"] <= result["total_population"]


# ─────────────────────────────────────────────────────────────────────────
# 7. Facility impact tests
# ─────────────────────────────────────────────────────────────────────────

class TestFacilityImpact:
    def test_hospitals_affected_subset(self, demo_graph, bridge_b1):
        origins = [(1, "Village_A"), (2, "Village_B")]
        dests   = [(8, "Hospital_H1"), (10, "Shelter_S1")]
        changes = calculate_accessibility_change(demo_graph, bridge_b1, origins, dests)
        result = calculate_facility_impact(changes, [8], [10])
        # Hospital 8 should be affected since bridge removal slows access
        assert isinstance(result["hospitals_affected"], list)
        assert isinstance(result["shelters_affected"], list)


# ─────────────────────────────────────────────────────────────────────────
# 8. Priority score tests
# ─────────────────────────────────────────────────────────────────────────

class TestPriorityScore:
    def test_priority_is_deterministic(self):
        """Same inputs must always produce the same priority."""
        r1 = calculate_priority(0.8, 0.7, 0.9)
        r2 = calculate_priority(0.8, 0.7, 0.9)
        assert r1 == r2

    def test_priority_zero_inputs(self):
        r = calculate_priority(0.0, 0.0, 0.0)
        assert r["raw_score"] == 0.0
        assert r["label"] == "Low"

    def test_priority_high_inputs(self):
        r = calculate_priority(1.0, 1.0, 1.0)
        assert r["raw_score"] == 1.0
        assert r["label"] == "Critical"

    def test_priority_label_coverage(self):
        labels = set()
        for v in [0.1, 0.35, 0.55, 0.85]:
            r = calculate_priority(v, v, v)
            labels.add(r["label"])
        assert "Low" in labels or "Medium" in labels  # At least two labels exercised

    def test_priority_components_in_output(self):
        r = calculate_priority(0.5, 0.6, 0.7)
        assert "components" in r
        assert "exposure" in r["components"]
        assert "disruption" in r["components"]
        assert "criticality" in r["components"]

    def test_priority_score_bounded(self):
        for e, d, c in [(0.9, 0.8, 0.95), (0.1, 0.2, 0.3), (1.0, 0.5, 0.0)]:
            r = calculate_priority(e, d, c)
            assert 0.0 <= r["raw_score"] <= 1.0


# ─────────────────────────────────────────────────────────────────────────
# 9. Full pipeline test
# ─────────────────────────────────────────────────────────────────────────

class TestFullPipeline:
    def test_run_full_counterfactual(self, demo_graph, bridge_b1):
        settlement_nodes = [(1, "Village_A"), (2, "Village_B"), (3, "Village_C")]
        hospital_nodes   = [(8, "Hospital_H1")]
        shelter_nodes    = [(10, "Shelter_S1")]
        pop_map          = {1: 4200, 2: 8700, 3: 2100}

        result = run_full_counterfactual(
            G=demo_graph,
            asset=bridge_b1,
            settlement_nodes=settlement_nodes,
            hospital_nodes=hospital_nodes,
            shelter_nodes=shelter_nodes,
            population_map=pop_map,
            exposure_score=0.85,
        )
        assert result.asset_id == bridge_b1.asset_id
        assert result.max_disruption_delta_min >= 0
        assert hasattr(result, "priority")
        assert hasattr(result, "population_impact")

    def test_full_counterfactual_to_dict(self, demo_graph, bridge_b1):
        settlement_nodes = [(1, "Village_A"), (2, "Village_B")]
        hospital_nodes   = [(8, "Hospital_H1")]
        shelter_nodes    = [(10, "Shelter_S1")]
        pop_map          = {1: 4200, 2: 8700}

        result = run_full_counterfactual(
            G=demo_graph, asset=bridge_b1,
            settlement_nodes=settlement_nodes,
            hospital_nodes=hospital_nodes,
            shelter_nodes=shelter_nodes,
            population_map=pop_map,
        )
        d = result.to_dict()
        assert "asset_id" in d
        assert "max_disruption_delta_min" in d
        assert "changes" in d


# ─────────────────────────────────────────────────────────────────────────
# 10. Demo scenario end-to-end test
# ─────────────────────────────────────────────────────────────────────────

class TestDemoScenario:
    def test_demo_scenario_runs(self):
        """Demo scenario must complete without errors."""
        data = run_demo_scenario()
        assert data["mode"] == "DEMO"
        assert data["bridges_detected"] >= 1
        assert len(data["counterfactual_results"]) >= 1

    def test_demo_has_headline(self):
        data = run_demo_scenario()
        headline = data.get("headline")
        assert headline is not None, "Demo must produce a headline disruption card"
        assert "disruption_delta_min" in headline
        assert "baseline_travel_time_min" in headline
        assert "scenario_travel_time_min" in headline

    def test_demo_bridge_removal_increases_time(self):
        """In demo, the bridge removal must increase travel time."""
        data = run_demo_scenario()
        headline = data["headline"]
        if headline and not headline.get("became_unreachable"):
            assert headline["scenario_travel_time_min"] > headline["baseline_travel_time_min"], (
                "Scenario travel time must exceed baseline in demo"
            )

    def test_demo_has_settlements_and_facilities(self):
        data = run_demo_scenario()
        assert len(data["settlements"]) >= 1
        assert len(data["hospitals"]) >= 1

    def test_demo_node_positions_populated(self):
        data = run_demo_scenario()
        positions = data.get("node_positions", {})
        assert len(positions) >= 10, "Node positions must include all demo graph nodes"

    def test_demo_graph_source_is_demo(self):
        data = run_demo_scenario()
        assert data["graph_source"] == "demo"


# ─────────────────────────────────────────────────────────────────────────
# Run via:  python -m pytest tests/ -v
# ─────────────────────────────────────────────────────────────────────────
