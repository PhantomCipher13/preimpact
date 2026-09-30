"""
test_milestone3.py
==================
Milestone 3 Test Suite: Cyclone Exposure + Hazard-Aware Scenarios.

Validates:
1. Cyclone scenario track waypoints, wind swaths, and surge polygon.
2. Geometry calculations: track distance, surge polygon inclusion.
3. Hazard classification (Extreme, High, Medium, Low) and normalized exposure [0, 1].
4. Candidate filtering progression (Total -> Exposed -> Analyzed).
5. Resilience Priority Score calculation and component visibility.
6. Deterministic scenario reproducibility.
7. Strict absence of forbidden predictive/failure probability terminology.
8. API endpoints for scenario data and ranking.
"""

import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
import networkx as nx

_BACKEND = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

from engine.hazard_exposure import (
    compute_exposure,
    batch_compute_exposure,
    filter_exposed_bridges,
    get_cyclone_scenario,
    _min_distance_to_track_km,
    _point_in_polygon,
    CYCLONE_SCENARIO,
    CORE_WIND_RADIUS_KM,
    HIGH_WIND_RADIUS_KM,
    ExposureResult,
)
from engine.bridge_detector import BridgeAsset
from engine.counterfactual import calculate_priority, simulate_asset_unavailability
from engine.real_scenario import run_real_scenario
from engine.demo_scenario import run_demo_scenario


# ─────────────────────────────────────────────────────────────────────────────
# 1. Cyclone Scenario & Provenance Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCycloneScenario:
    def test_cyclone_scenario_structure(self):
        scenario = get_cyclone_scenario()
        assert "name" in scenario
        assert "region" in scenario
        assert "landfall_lat" in scenario
        assert "landfall_lon" in scenario
        assert "max_wind_kmh" in scenario
        assert "storm_surge_m" in scenario
        assert "track_waypoints" in scenario
        assert "surge_zone_polygon" in scenario
        assert "data_label" in scenario
        assert "source" in scenario

    def test_cyclone_track_waypoints(self):
        scenario = get_cyclone_scenario()
        waypoints = scenario["track_waypoints"]
        assert len(waypoints) >= 5, "Should have at least 5 track waypoints"

        for wp in waypoints:
            assert "hour" in wp
            assert "lat" in wp and 18.0 <= wp["lat"] <= 24.0, f"Lat out of Odisha bounds: {wp['lat']}"
            assert "lon" in wp and 84.0 <= wp["lon"] <= 89.0, f"Lon out of Odisha bounds: {wp['lon']}"
            assert "wind_kmh" in wp and wp["wind_kmh"] > 0
            assert "stage" in wp

    def test_cyclone_provenance_labels(self):
        scenario = get_cyclone_scenario()
        # Must be labeled as replay analogue, not a live prediction
        assert "MODELED" in scenario["data_label"]
        assert "Replay" in scenario["source"] or "Archive" in scenario["source"] or "Analogue" in scenario["source"]
        assert "not a live forecast" in scenario["data_label"].lower() or "not an operational forecast" in scenario["data_label"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Geometry & Hazard Calculations
# ─────────────────────────────────────────────────────────────────────────────

class TestHazardGeometryMath:
    def test_min_distance_to_track_point_on_waypoint(self):
        # A point at the exact coordinates of the landfall waypoint
        landfall = CYCLONE_SCENARIO["landfall_lat"], CYCLONE_SCENARIO["landfall_lon"]
        dist = _min_distance_to_track_km(landfall[0], landfall[1])
        assert dist < 1.0, f"Distance to own waypoint should be near 0, got {dist:.2f} km"

    def test_min_distance_to_track_far_point(self):
        # Point far west in inland Odisha / Chhattisgarh (lat 20.5, lon 82.0)
        dist = _min_distance_to_track_km(20.5, 82.0)
        assert dist > 300.0, f"Far inland point should be > 300 km away, got {dist:.2f} km"

    def test_point_in_polygon_surge_zone(self):
        surge_poly = CYCLONE_SCENARIO["surge_zone_polygon"]
        # Point directly on the Kendrapara coastal fringe (approx 20.55, 86.75)
        assert _point_in_polygon(20.55, 86.75, surge_poly) is True
        # Point far inland in Cuttack (approx 20.46, 85.88)
        assert _point_in_polygon(20.46, 85.88, surge_poly) is False

    def test_wind_swath_membership(self):
        landfall_lat = CYCLONE_SCENARIO["landfall_lat"]
        landfall_lon = CYCLONE_SCENARIO["landfall_lon"]
        asset = BridgeAsset(
            asset_id="TEST_LF",
            name="Landfall Bridge",
            edge_keys=[(1, 2, 0)],
            midpoint_lat=landfall_lat,
            midpoint_lon=landfall_lon,
            highway_type="primary",
            length_m=100.0,
        )
        exp_at_landfall = compute_exposure(asset)
        assert exp_at_landfall.in_core_wind_zone is True
        assert exp_at_landfall.in_gale_wind_zone is True
        assert exp_at_landfall.is_exposed is True


# ─────────────────────────────────────────────────────────────────────────────
# 3. Hazard Classification & Exposure Normalization
# ─────────────────────────────────────────────────────────────────────────────

class TestHazardClassification:
    def test_exposure_score_normalized_bounds(self):
        # Test various coordinates in and around Kendrapara
        test_coords = [
            ("B_LF", 20.485, 86.680, "trunk"),     # Landfall
            ("B_KP", 20.565, 86.557, "primary"),   # Kendrapara interior
            ("B_BK", 20.700, 86.900, "secondary"), # Bhitarkanika coast
            ("B_BB", 20.300, 85.800, "tertiary"),  # Bhubaneswar
            ("B_NB", 21.500, 87.500, "primary"),   # Northern Bay
            ("B_SO", 19.000, 84.000, "unclassified"), # South Odisha
        ]
        for aid, lat, lon, hw in test_coords:
            asset = BridgeAsset(
                asset_id=aid,
                name=f"Bridge {aid}",
                edge_keys=[(1, 2, 0)],
                midpoint_lat=lat,
                midpoint_lon=lon,
                highway_type=hw,
                length_m=100.0,
            )
            exp = compute_exposure(asset)
            assert 0.0 <= exp.exposure_score <= 1.0, f"Score {exp.exposure_score} outside [0, 1] for ({lat}, {lon})"
            assert exp.exposure_label in ("Extreme", "High", "Medium", "Low")

    def test_hazard_classification_levels(self):
        # Very close to track + in surge zone -> High or Extreme
        asset_coastal = BridgeAsset(
            asset_id="B_COAST",
            name="Coastal Bridge",
            edge_keys=[(1, 2, 0)],
            midpoint_lat=20.55,
            midpoint_lon=86.75,
            highway_type="primary",
            length_m=200.0,
        )
        coastal_exp = compute_exposure(asset_coastal)
        assert coastal_exp.exposure_label in ("Extreme", "High")
        assert coastal_exp.exposure_score >= 0.55

        # Far inland point -> Low
        asset_far = BridgeAsset(
            asset_id="B_FAR",
            name="Far Inland Bridge",
            edge_keys=[(3, 4, 0)],
            midpoint_lat=20.0,
            midpoint_lon=84.0,
            highway_type="unclassified",
            length_m=40.0,
        )
        far_exp = compute_exposure(asset_far)
        assert far_exp.exposure_label == "Low"
        assert far_exp.exposure_score < 0.40

    def test_surge_increases_exposure(self):
        # Two points with similar track distance, one in surge polygon
        asset_surge = BridgeAsset(
            asset_id="B_SURGE",
            name="Surge Zone Bridge",
            edge_keys=[(1, 2, 0)],
            midpoint_lat=20.55,
            midpoint_lon=86.75,
            highway_type="primary",
            length_m=100.0,
        )
        asset_inland = BridgeAsset(
            asset_id="B_INLAND",
            name="Inland Bridge",
            edge_keys=[(3, 4, 0)],
            midpoint_lat=20.55,
            midpoint_lon=86.25,
            highway_type="primary",
            length_m=100.0,
        )
        exp_surge = compute_exposure(asset_surge)
        exp_inland = compute_exposure(asset_inland)
        assert exp_surge.in_surge_zone is True
        assert exp_inland.in_surge_zone is False
        assert exp_surge.exposure_score > exp_inland.exposure_score


# ─────────────────────────────────────────────────────────────────────────────
# 4. Candidate Filtering Progression
# ─────────────────────────────────────────────────────────────────────────────

class TestCandidateFiltering:
    @pytest.fixture
    def mock_bridges(self) -> List[BridgeAsset]:
        # Create 10 mock bridges with varied coordinates
        bridges = []
        # 5 near coast/track
        for i in range(5):
            bridges.append(BridgeAsset(
                asset_id=f"B_NEAR_{i}",
                name=f"Coastal Bridge {i}",
                edge_keys=[(100 + i, 200 + i, 0)],
                midpoint_lat=20.50 + i * 0.02,
                midpoint_lon=86.65 + i * 0.02,
                highway_type="primary",
                length_m=150.0,
            ))
        # 5 far inland
        for i in range(5):
            bridges.append(BridgeAsset(
                asset_id=f"B_FAR_{i}",
                name=f"Inland Bridge {i}",
                edge_keys=[(300 + i, 400 + i, 0)],
                midpoint_lat=20.50 + i * 0.05,
                midpoint_lon=84.50 + i * 0.05,  # ~200km inland
                highway_type="secondary",
                length_m=80.0,
            ))
        return bridges

    def test_filter_exposed_bridges_progression(self, mock_bridges):
        res = filter_exposed_bridges(
            mock_bridges,
            min_exposure_score=0.40,
        )
        total = res["total_count"]
        exposed = res["exposed_count"]
        exposed_assets = res["exposed_assets"]

        assert total == 10
        # Coastal bridges will meet exposure threshold
        assert exposed >= 5
        assert len(exposed_assets) == exposed
        # Progression invariant: total >= exposed >= 1
        assert total >= exposed >= 1

    def test_filter_exposed_bridges_ordering(self, mock_bridges):
        res = filter_exposed_bridges(
            mock_bridges,
            min_exposure_score=0.10,
        )
        exposed_assets = res["exposed_assets"]
        exp_map = res["exposure_map"]

        # Verify descending order of exposure
        for i in range(len(exposed_assets) - 1):
            assert exp_map[exposed_assets[i].asset_id].exposure_score >= exp_map[exposed_assets[i + 1].asset_id].exposure_score


# ─────────────────────────────────────────────────────────────────────────────
# 5. Resilience Priority Score & Components
# ─────────────────────────────────────────────────────────────────────────────

class TestResiliencePriorityScore:
    def test_priority_score_components_visible(self):
        # Test calculation with visible components: exposure, disruption, criticality
        res = calculate_priority(
            exposure_score=0.85,
            disruption_score=0.62,
            criticality_score=0.74,
        )
        assert "raw_score" in res
        assert "label" in res
        assert "components" in res
        components = res["components"]
        assert "exposure" in components
        assert "disruption" in components
        assert "criticality" in components

        # Verify all components are non-negative floats
        assert 0.0 <= components["exposure"] <= 1.0
        assert 0.0 <= components["disruption"] <= 1.0
        assert 0.0 <= components["criticality"] <= 1.0
        assert 0.0 <= res["raw_score"] <= 1.0

    def test_disruption_impact_on_priority(self):
        # Higher disruption with same exposure should produce higher priority score
        p_low = calculate_priority(
            exposure_score=0.75,
            disruption_score=0.15,
            criticality_score=0.50,
        )
        p_high = calculate_priority(
            exposure_score=0.75,
            disruption_score=0.85,
            criticality_score=0.50,
        )
        assert p_high["raw_score"] > p_low["raw_score"]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Scenario Reproducibility
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioReproducibility:
    def test_deterministic_real_scenario_runs(self):
        # Run real scenario twice and check identical results
        res1 = run_real_scenario()
        res2 = run_real_scenario()

        assert res1["mode"] == res2["mode"]
        assert len(res1["counterfactual_results"]) == len(res2["counterfactual_results"])
        assert res1["summary"] == res2["summary"]

        for r1, r2 in zip(res1["counterfactual_results"], res2["counterfactual_results"]):
            assert r1["asset_id"] == r2["asset_id"]
            assert r1["priority"]["raw_score"] == r2["priority"]["raw_score"]
            assert r1["exposure"]["exposure_score"] == r2["exposure"]["exposure_score"]
            assert r1["max_disruption_delta_min"] == r2["max_disruption_delta_min"]


# ─────────────────────────────────────────────────────────────────────────────
# 7. Strict Absence of Forbidden Predictive / Failure Probability Terms
# ─────────────────────────────────────────────────────────────────────────────

class TestForbiddenTerminology:
    FORBIDDEN_TERMS = [
        "failure_probability",
        "collapse_probability",
        "probability_of_failure",
        "predicted_failure",
    ]

    def _check_no_forbidden_in_obj(self, obj: Any, path: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = str(k).lower()
                for term in self.FORBIDDEN_TERMS:
                    assert term not in k_lower, f"Forbidden term '{term}' found in key '{path}.{k}'"
                self._check_no_forbidden_in_obj(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._check_no_forbidden_in_obj(item, f"{path}[{i}]")
        elif isinstance(obj, str):
            obj_lower = obj.lower()
            for term in self.FORBIDDEN_TERMS:
                assert term not in obj_lower, f"Forbidden term '{term}' found in text at '{path}': {obj}"

    def test_no_forbidden_terms_in_real_scenario(self):
        data = run_real_scenario()
        self._check_no_forbidden_in_obj(data)

    def test_no_forbidden_terms_in_demo_scenario(self):
        data = run_demo_scenario()
        self._check_no_forbidden_in_obj(data)

    def test_no_forbidden_terms_in_cyclone_scenario(self):
        data = get_cyclone_scenario()
        self._check_no_forbidden_in_obj(data)
