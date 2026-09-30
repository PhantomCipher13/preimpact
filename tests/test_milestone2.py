"""
test_milestone2.py
==================
Milestone 2 test suite: real-data pipeline, POI loading, exposure scoring,
network matching, accessibility analysis, priority ranking.

All tests work offline (using demo/fallback data) so CI doesn't require
a live Overpass connection.
"""

import math
import sys
from pathlib import Path
from typing import List

import pytest
import networkx as nx

_BACKEND = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

from engine.graph_loader import build_demo_graph, load_graph
from engine.bridge_detector import detect_bridges
from engine.poi_loader import (
    FALLBACK_HOSPITALS,
    FALLBACK_SHELTERS,
    FALLBACK_SETTLEMENTS,
    load_all_pois,
)
from engine.network_matcher import (
    MatchedPOI,
    match_pois_to_graph,
    match_all_facilities,
    snap_to_nearest_node,
    _haversine_m,
)
from engine.hazard_exposure import (
    compute_exposure,
    batch_compute_exposure,
    get_cyclone_scenario,
    CYCLONE_SCENARIO,
    ExposureResult,
)
from engine.counterfactual import (
    simulate_asset_unavailability,
    run_full_counterfactual,
    calculate_priority,
)
from engine.real_scenario import run_real_scenario, get_data_quality_report
from engine.demo_scenario import run_demo_scenario


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def demo_graph():
    return build_demo_graph()

@pytest.fixture(scope="module")
def demo_bridges(demo_graph):
    return detect_bridges(demo_graph)

@pytest.fixture(scope="module")
def bridge_b1(demo_bridges):
    bridges = [b for b in demo_bridges if "B1" in b.name]
    assert bridges, "Bridge_B1 required"
    return bridges[0]


# ─────────────────────────────────────────────────────────────────────────
# 1. POI Loader tests
# ─────────────────────────────────────────────────────────────────────────

class TestPOILoader:
    def test_fallback_hospitals_non_empty(self):
        assert len(FALLBACK_HOSPITALS) >= 1

    def test_fallback_hospitals_have_coords(self):
        for h in FALLBACK_HOSPITALS:
            assert "lat" in h and "lon" in h
            assert -90 <= h["lat"] <= 90
            assert -180 <= h["lon"] <= 180

    def test_fallback_hospitals_labelled_estimated(self):
        for h in FALLBACK_HOSPITALS:
            assert h.get("osm_source") in ("ESTIMATED", "REAL"), \
                f"Hospital '{h['name']}' missing osm_source"

    def test_fallback_shelters_non_empty(self):
        assert len(FALLBACK_SHELTERS) >= 1

    def test_fallback_settlements_non_empty(self):
        assert len(FALLBACK_SETTLEMENTS) >= 1

    def test_fallback_settlements_have_population(self):
        for s in FALLBACK_SETTLEMENTS:
            assert "population_estimate" in s
            assert s["population_estimate"] > 0

    def test_load_all_pois_returns_dict(self):
        """load_all_pois should always return a dict with required keys."""
        pois = load_all_pois()   # uses cache or fallback — offline safe
        assert "hospitals" in pois
        assert "shelters" in pois
        assert "settlements" in pois

    def test_pois_all_have_names(self):
        pois = load_all_pois()
        for h in pois["hospitals"]:
            assert h.get("name"), f"Hospital missing name: {h}"

    def test_pois_all_have_coords(self):
        pois = load_all_pois()
        for item in pois["hospitals"] + pois["shelters"]:
            assert "lat" in item and "lon" in item

    def test_pois_source_field_present(self):
        pois = load_all_pois()
        assert pois.get("hospital_source") in ("osm", "fallback", None)


# ─────────────────────────────────────────────────────────────────────────
# 2. Haversine / geometry tests
# ─────────────────────────────────────────────────────────────────────────

class TestGeometry:
    def test_haversine_same_point(self):
        d = _haversine_m(20.5, 86.5, 20.5, 86.5)
        assert d == pytest.approx(0.0, abs=1.0)

    def test_haversine_known_distance(self):
        # Kendrapara to Cuttack is roughly 70–80 km
        d = _haversine_m(20.495, 86.523, 20.460, 85.880)
        assert 60_000 < d < 100_000, f"Expected ~70km, got {d/1000:.1f}km"

    def test_haversine_symmetry(self):
        d1 = _haversine_m(20.5, 86.5, 20.6, 86.6)
        d2 = _haversine_m(20.6, 86.6, 20.5, 86.5)
        assert abs(d1 - d2) < 1.0


# ─────────────────────────────────────────────────────────────────────────
# 3. Network matching tests
# ─────────────────────────────────────────────────────────────────────────

class TestNetworkMatcher:
    def test_snap_returns_node_in_graph(self, demo_graph):
        lat, lon = 20.570, 86.510   # Village_A area
        node_id, dist = snap_to_nearest_node(demo_graph, lat, lon)
        assert node_id in demo_graph.nodes
        assert dist >= 0

    def test_snap_distance_is_reasonable(self, demo_graph):
        """Snap to a point that should be within 5 km of a node."""
        lat, lon = 20.565, 86.530   # Junction_1 area
        node_id, dist = snap_to_nearest_node(demo_graph, lat, lon)
        assert dist < 5000, f"Snap distance too large: {dist:.0f}m"

    def test_match_pois_to_graph_returns_matched(self, demo_graph):
        pois = [
            {"lat": 20.555, "lon": 86.580, "name": "Hospital", "osm_source": "ESTIMATED"},
        ]
        matched = match_pois_to_graph(demo_graph, pois, "hospital")
        assert len(matched) == 1
        assert matched[0].nearest_node in demo_graph.nodes

    def test_match_pois_drops_far_points(self, demo_graph):
        """POIs far outside the graph extent should be dropped."""
        pois = [
            {"lat": 25.0, "lon": 90.0, "name": "Far POI", "osm_source": "ESTIMATED"},
        ]
        matched = match_pois_to_graph(demo_graph, pois, "hospital", max_snap_distance_m=100)
        assert len(matched) == 0

    def test_match_all_facilities_returns_all_types(self, demo_graph):
        pois = {
            "hospitals": [{"lat": 20.555, "lon": 86.580, "name": "H1", "osm_source": "ESTIMATED"}],
            "shelters":  [{"lat": 20.545, "lon": 86.545, "name": "S1", "osm_source": "ESTIMATED"}],
            "settlements": [{"lat": 20.570, "lon": 86.510, "name": "V1", "osm_source": "ESTIMATED", "population_estimate": 5000}],
        }
        result = match_all_facilities(demo_graph, pois)
        assert "hospitals" in result
        assert "shelters" in result
        assert "settlements" in result

    def test_matched_poi_to_dict(self, demo_graph):
        pois = [{"lat": 20.555, "lon": 86.580, "name": "H1", "osm_source": "ESTIMATED"}]
        matched = match_pois_to_graph(demo_graph, pois, "hospital")
        assert len(matched) == 1
        d = matched[0].to_dict()
        assert "poi_name" in d
        assert "nearest_node" in d
        assert "snap_distance_m" in d
        assert "osm_source" in d


# ─────────────────────────────────────────────────────────────────────────
# 4. Hazard exposure tests
# ─────────────────────────────────────────────────────────────────────────

class TestHazardExposure:
    def test_cyclone_scenario_has_landfall(self):
        sc = get_cyclone_scenario()
        assert "landfall_lat" in sc
        assert "landfall_lon" in sc
        assert "data_label" in sc

    def test_exposure_result_is_dataclass(self, demo_bridges, bridge_b1):
        result = compute_exposure(bridge_b1)
        assert isinstance(result, ExposureResult)
        assert 0.0 <= result.exposure_score <= 1.0

    def test_exposure_label_is_valid(self, bridge_b1):
        result = compute_exposure(bridge_b1)
        assert result.exposure_label in ("Low", "Medium", "High", "Extreme")

    def test_exposure_score_bounded(self, demo_bridges):
        for bridge in demo_bridges:
            result = compute_exposure(bridge)
            assert 0.0 <= result.exposure_score <= 1.0

    def test_exposure_closer_is_higher(self, demo_graph):
        """A bridge closer to landfall should have higher exposure."""
        from engine.bridge_detector import BridgeAsset

        # Close to Kendrapara coast (near landfall)
        near_bridge = BridgeAsset(
            asset_id="TEST_NEAR", name="Near Bridge",
            edge_keys=[], midpoint_lat=20.510, midpoint_lon=86.660,
            highway_type="primary", length_m=200,
        )
        # Far inland
        far_bridge = BridgeAsset(
            asset_id="TEST_FAR", name="Far Bridge",
            edge_keys=[], midpoint_lat=21.200, midpoint_lon=85.500,
            highway_type="primary", length_m=200,
        )
        near_exp = compute_exposure(near_bridge)
        far_exp  = compute_exposure(far_bridge)
        assert near_exp.exposure_score > far_exp.exposure_score, \
            f"Near {near_exp.exposure_score:.3f} should > Far {far_exp.exposure_score:.3f}"

    def test_batch_compute_exposure(self, demo_bridges):
        result = batch_compute_exposure(demo_bridges)
        assert len(result) == len(demo_bridges)
        for aid, exp in result.items():
            assert isinstance(exp, ExposureResult)

    def test_exposure_to_dict(self, bridge_b1):
        result = compute_exposure(bridge_b1)
        d = result.to_dict()
        required = ["asset_id", "exposure_score", "exposure_label", "data_label",
                    "distance_from_landfall_km", "in_surge_zone"]
        for k in required:
            assert k in d, f"Missing key: {k}"

    def test_exposure_data_label_present(self, bridge_b1):
        result = compute_exposure(bridge_b1)
        assert "MODELLED" in result.data_label.upper() or "SCENARIO" in result.data_label.upper()


# ─────────────────────────────────────────────────────────────────────────
# 5. Hospital routing tests
# ─────────────────────────────────────────────────────────────────────────

class TestHospitalRouting:
    def test_baseline_route_to_hospital(self, demo_graph, bridge_b1):
        """Settlement → hospital route exists in baseline."""
        change = simulate_asset_unavailability(
            G=demo_graph, asset=bridge_b1,
            origin_node=1, dest_node=8,   # Village_A → Hospital_H1
            origin_label="Village_A", dest_label="Hospital_H1",
        )
        assert change.baseline is not None
        assert change.baseline.reachable
        assert change.baseline.travel_time_s > 0

    def test_scenario_route_changes_after_bridge_removal(self, demo_graph, bridge_b1):
        """After bridge removal, travel time to hospital must increase."""
        change = simulate_asset_unavailability(
            G=demo_graph, asset=bridge_b1,
            origin_node=1, dest_node=8,
        )
        if change.scenario.reachable:
            assert change.scenario.travel_time_s > change.baseline.travel_time_s
        else:
            assert change.became_unreachable

    def test_multi_settlement_hospital_accessibility(self, demo_graph, bridge_b1):
        """Test batch accessibility for multiple settlements → hospital."""
        from engine.counterfactual import calculate_accessibility_change
        settlements = [(1, "Village_A"), (2, "Village_B"), (3, "Village_C")]
        hospitals   = [(8, "Hospital_H1")]
        changes = calculate_accessibility_change(demo_graph, bridge_b1, settlements, hospitals)
        assert len(changes) == 3
        # All baselines should be reachable
        for ch in changes:
            assert ch.baseline.reachable, f"{ch.origin_label} → hospital not reachable"

    def test_shelter_accessibility(self, demo_graph, bridge_b1):
        """Settlements can reach shelter in baseline; bridge removal disrupts."""
        change = simulate_asset_unavailability(
            G=demo_graph, asset=bridge_b1,
            origin_node=1, dest_node=10,  # Village_A → Shelter_S1
        )
        assert change.baseline.reachable
        if change.scenario.reachable:
            assert change.disruption_delta_s > 0


# ─────────────────────────────────────────────────────────────────────────
# 6. Priority engine tests
# ─────────────────────────────────────────────────────────────────────────

class TestPriorityEngine:
    def test_priority_uses_all_three_components(self):
        r = calculate_priority(0.8, 0.6, 0.7)
        comps = r["components"]
        assert comps["exposure"]    == pytest.approx(0.8, abs=0.001)
        assert comps["disruption"]  == pytest.approx(0.6, abs=0.001)
        assert comps["criticality"] == pytest.approx(0.7, abs=0.001)

    def test_priority_geometric_mean(self):
        """Priority = geometric mean of (exp, disrupt, crit)."""
        e, d, c = 0.8, 0.6, 0.7
        expected = (e * d * c) ** (1/3)
        r = calculate_priority(e, d, c)
        assert r["raw_score"] == pytest.approx(expected, abs=0.001)

    def test_priority_deterministic_repeated(self):
        for _ in range(10):
            r = calculate_priority(0.75, 0.50, 0.85)
            assert r["raw_score"] == pytest.approx(calculate_priority(0.75, 0.50, 0.85)["raw_score"])

    def test_priority_ranking_order(self):
        """Higher exposure/disruption/criticality → higher priority."""
        low  = calculate_priority(0.2, 0.2, 0.2)
        high = calculate_priority(0.9, 0.8, 0.85)
        assert high["raw_score"] > low["raw_score"]

    def test_full_pipeline_priority_with_exposure(self, demo_graph, bridge_b1):
        """Full pipeline includes exposure in priority calculation."""
        result = run_full_counterfactual(
            G=demo_graph,
            asset=bridge_b1,
            settlement_nodes=[(1, "V_A"), (2, "V_B")],
            hospital_nodes=[(8, "Hospital_H1")],
            shelter_nodes=[(10, "Shelter_S1")],
            population_map={1: 4200, 2: 8700},
            exposure_score=0.85,
        )
        assert hasattr(result, "priority")
        p = result.priority
        assert p["components"]["exposure"] == pytest.approx(0.85, abs=0.01)
        assert p["raw_score"] >= 0


# ─────────────────────────────────────────────────────────────────────────
# 7. Real scenario pipeline tests (offline-safe)
# ─────────────────────────────────────────────────────────────────────────

class TestRealScenario:
    def test_real_scenario_runs(self):
        """Real scenario should complete with a valid honest mode."""
        result = run_real_scenario()
        assert "mode" in result
        assert result["mode"] in ("REAL_OSM", "PARTIAL_REAL_DATA", "DEMO_FALLBACK")

    def test_real_scenario_has_bridges(self):
        result = run_real_scenario()
        assert result["bridges_detected"] >= 1

    def test_real_scenario_has_counterfactual_results(self):
        result = run_real_scenario()
        assert len(result["counterfactual_results"]) >= 1

    def test_real_scenario_data_labels_present(self):
        result = run_real_scenario()
        assert "data_labels" in result
        labels = result["data_labels"]
        assert "road_network" in labels
        assert "hospitals" in labels
        assert "bridges" in labels
        assert "shelters" in labels
        assert "population" in labels
        assert "counterfactual_results" in labels
        assert "priority_score" in labels

    def test_real_scenario_headline(self):
        result = run_real_scenario()
        headline = result.get("headline")
        assert headline is not None
        assert "baseline_travel_time_min" in headline
        assert "disruption_delta_min" in headline
        assert "provenance_note" in headline

    def test_data_quality_report(self):
        result = run_real_scenario()
        report = get_data_quality_report(result)
        assert "counts" in report
        assert report["counts"]["bridges_found"] >= 1
        assert "data_labels" in report
        assert "mode" in report

    def test_real_scenario_bridges_have_exposure(self):
        result = run_real_scenario()
        for cf in result["counterfactual_results"]:
            assert "exposure" in cf, f"{cf['asset_id']} missing exposure"

    def test_real_scenario_no_fake_probabilities(self):
        """Verify no 'failure_probability' or 'collapse_risk' keys anywhere."""
        result = run_real_scenario()
        result_str = str(result).lower()
        forbidden = ["failure_probability", "collapse_risk", "predicted_failure"]
        for f in forbidden:
            assert f not in result_str, f"Forbidden term found: {f}"


# ─────────────────────────────────────────────────────────────────────────
# 8. Data provenance integrity tests (Milestone 2 Correction)
# ─────────────────────────────────────────────────────────────────────────

class TestDataProvenance:
    def test_all_pois_have_osm_source_field(self):
        pois = load_all_pois()
        for h in pois["hospitals"]:
            assert "osm_source" in h, f"Hospital {h.get('name')} missing osm_source"
        for s in pois["shelters"]:
            assert "osm_source" in s, f"Shelter {s.get('name')} missing osm_source"

    def test_osm_source_values_are_valid(self):
        pois = load_all_pois()
        valid = {"REAL", "ESTIMATED", "fallback"}
        for item in pois["hospitals"] + pois["shelters"]:
            assert item.get("osm_source") in valid, \
                f"Invalid osm_source '{item.get('osm_source')}' for {item.get('name')}"

    def test_hospitals_have_real_osm_ids_and_coords(self):
        """Hospital layer must provide verified OSM IDs and geographic coordinates."""
        pois = load_all_pois()
        real_hospitals = [h for h in pois["hospitals"] if h.get("osm_source") == "REAL"]
        assert len(real_hospitals) >= 1, "Must have at least one real OSM hospital"
        for h in real_hospitals:
            assert "osm_id" in h and h["osm_id"] is not None, f"Hospital {h['name']} missing osm_id"
            assert h["osm_id"] > 0, f"Invalid osm_id {h['osm_id']}"
            assert "lat" in h and 20.0 <= h["lat"] <= 21.5, f"Invalid lat for {h['name']}"
            assert "lon" in h and 86.0 <= h["lon"] <= 87.5, f"Invalid lon for {h['name']}"

    def test_synthetic_fallback_labeled_partial_real_data(self):
        """
        When live OSM road download is unavailable and synthetic graph is used,
        mode MUST be PARTIAL_REAL_DATA (never REAL_OSM).
        """
        result = run_real_scenario(force_synthetic=True)
        assert result["mode"] == "PARTIAL_REAL_DATA"
        assert result["graph_source"] == "realistic_synthetic"

        labels = result["data_labels"]
        # Road network must state it is modeled fallback
        assert "MODELED" in labels["road_network"].upper() or "SYNTHETIC" in labels["road_network"].upper()
        assert "unavailable" in labels["road_network"].lower()

        # Hospitals must state they are Real OSM
        assert "REAL" in labels["hospitals"].upper()
        assert "OPENSTREETMAP" in labels["hospitals"].upper()

        # Bridges must be labeled synthetic / modeled
        assert "SYNTHETIC" in labels["bridges"].upper() or "MODELED" in labels["bridges"].upper()

        # Warning must be present explaining the hybrid nature
        assert result["warning"] is not None
        assert "Modeled fallback" in result["warning"]
        assert "Real OpenStreetMap" in result["warning"]

    def test_real_osm_mode_only_when_genuine_graph_exists(self):
        """
        REAL_OSM mode is ONLY allowed when graph_source is osm_cache or osm_live.
        """
        result = run_real_scenario()
        if result["mode"] == "REAL_OSM":
            assert result["graph_source"] in ("osm_cache", "osm_live")
            assert "OpenStreetMap" in result["data_labels"]["road_network"]
        elif result["mode"] == "PARTIAL_REAL_DATA":
            assert result["graph_source"] == "realistic_synthetic"
            assert "MODELED" in result["data_labels"]["road_network"].upper() or "SYNTHETIC" in result["data_labels"]["road_network"].upper()

    def test_exposure_always_labelled_modelled(self, demo_bridges):
        for bridge in demo_bridges:
            exp = compute_exposure(bridge)
            assert "MODELLED" in exp.data_label.upper() or "SCENARIO" in exp.data_label.upper()

    def test_cyclone_scenario_labelled_not_forecast(self):
        sc = get_cyclone_scenario()
        label = sc.get("data_label", "").upper()
        assert "FORECAST" not in label or "NOT" in label

    def test_matched_pois_preserve_osm_source_and_id(self, demo_graph):
        pois = [{"lat": 20.555, "lon": 86.580, "name": "H1", "osm_source": "REAL", "osm_id": 123456}]
        matched = match_pois_to_graph(demo_graph, pois, "hospital")
        assert len(matched) == 1
        assert matched[0].osm_source == "REAL"
        assert matched[0].osm_id == 123456
        assert matched[0].to_dict()["osm_id"] == 123456

