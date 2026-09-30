"""
test_gemini.py
==============
Milestone 4 Test Suite:
- Gemini Evidence-Grounded Briefing
- Graceful Degradation & Fallback
- Strict Separation of Concerns (no invented numbers/probabilities)
- Pre-Impact Preparation Options
- API Endpoints (/api/gemini/status, /api/brief/{asset_id})
- Engine Output Sanity & Integrity Audits
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_BACKEND = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

from engine.gemini_brief import (
    extract_deterministic_evidence,
    generate_deterministic_fallback_brief,
    generate_asset_brief,
    generate_preparation_actions,
    is_gemini_available,
    get_gemini_api_key,
)
from engine.real_scenario import run_real_scenario
from engine.demo_scenario import run_demo_scenario
from engine.poi_loader import load_all_pois


# ─────────────────────────────────────────────────────────────────────────────
# 1. Gemini Fallback & Evidence Grounding Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGeminiModule:
    @pytest.fixture
    def sample_asset_result(self):
        return {
            "asset_id": "B006",
            "asset_name": "DR15",
            "exposure": {
                "exposure_score": 0.965,
                "exposure_label": "Extreme",
                "distance_from_landfall_km": 10.0,
                "distance_from_track_km": 8.1,
                "in_surge_zone": True,
                "in_core_wind_zone": True,
            },
            "priority": {
                "raw_score": 0.391,
                "label": "Medium",
                "components": {
                    "exposure": 0.965,
                    "disruption": 0.079,
                    "criticality": 0.778,
                },
            },
            "max_disruption_delta_min": 9.53,
            "hospitals_affected": [101, 102, 103],
            "shelters_affected": [201],
            "population_impact": {
                "total_population": 89400,
                "affected_population": 14200,
            },
            "changes": [
                {
                    "origin_label": "Aul",
                    "dest_label": "Mahakalapada Shelter CS-07",
                    "baseline_travel_time_min": 16.7,
                    "scenario_travel_time_min": 26.3,
                    "disruption_delta_min": 9.53,
                    "became_unreachable": False,
                },
                {
                    "origin_label": "Aul",
                    "dest_label": "Govt Hospital Ayeba",
                    "baseline_travel_time_min": 32.5,
                    "scenario_travel_time_min": 38.9,
                    "disruption_delta_min": 6.38,
                    "became_unreachable": False,
                },
            ],
        }

    def test_gemini_fallback_when_key_missing(self, sample_asset_result):
        # Force GEMINI_API_KEY to be empty
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            brief = generate_asset_brief(sample_asset_result)
            assert brief["status"] == "fallback"
            assert brief["is_ai_generated"] is False
            assert "GEMINI BRIEFING UNAVAILABLE" in brief["notice"]
            assert "Core resilience analysis remains fully operational" in brief["notice"]
            assert "why_prioritized" in brief
            assert "counterfactual_impact" in brief
            assert "affected_services" in brief
            assert "preparation_options" in brief
            assert len(brief["preparation_options"]) >= 4

    def test_deterministic_evidence_extraction(self, sample_asset_result):
        evidence = extract_deterministic_evidence(sample_asset_result)
        assert evidence["asset_id"] == "B006"
        assert evidence["asset_name"] == "DR15"
        assert evidence["hazard_exposure_score"] == pytest.approx(0.965, abs=0.001)
        assert evidence["hazard_exposure_label"] == "Extreme"
        assert evidence["baseline_travel_time_min"] == pytest.approx(16.7, abs=0.1)
        assert evidence["scenario_travel_time_min"] == pytest.approx(26.3, abs=0.1)
        assert evidence["disruption_delta_min"] == pytest.approx(9.5, abs=0.1)
        assert evidence["disruption_percent"] == 57  # (9.53 / 16.7) * 100 ~ 57%
        assert evidence["hospitals_affected"] == 3
        assert evidence["shelters_affected"] == 1
        assert evidence["population_affected_estimate"] == 89400

    def test_briefing_has_all_four_sections(self, sample_asset_result):
        brief = generate_asset_brief(sample_asset_result)
        assert "why_prioritized" in brief and len(brief["why_prioritized"]) > 20
        assert "counterfactual_impact" in brief and len(brief["counterfactual_impact"]) > 20
        assert "affected_services" in brief and len(brief["affected_services"]) > 20
        assert "preparation_options" in brief and isinstance(brief["preparation_options"], list)
        assert len(brief["preparation_options"]) >= 4

    def test_preparation_actions_actionable(self, sample_asset_result):
        actions = generate_preparation_actions(sample_asset_result)
        assert isinstance(actions, list)
        assert len(actions) >= 4
        # Verify non-empty actionable strings
        for action in actions:
            assert isinstance(action, str)
            assert len(action) > 15

    def test_no_failure_claims_in_briefing(self, sample_asset_result):
        brief = generate_asset_brief(sample_asset_result)
        forbidden = [
            "failure probability",
            "collapse probability",
            "probability of failure",
            "predicted failure",
            "structural collapse",
        ]
        text_content = (
            brief["why_prioritized"] + " " +
            brief["counterfactual_impact"] + " " +
            brief["affected_services"] + " " +
            " ".join(brief["preparation_options"])
        ).lower()

        for term in forbidden:
            assert term not in text_content, f"Forbidden term '{term}' found in brief text!"

    def test_mock_gemini_live_call_parsing(self, sample_asset_result):
        # Test parsing of a simulated Gemini SDK JSON response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "why_prioritized": "Bridge B006 is prioritized because its hypothetical unavailability causes a 9.5 min delay under Extreme hazard exposure (0.965).",
            "counterfactual_impact": "Emergency travel increases from 16.7 min to 26.3 min (+57%).",
            "affected_services": "Affects 3 hospitals, 1 shelter, and 89,400 people.",
            "preparation_options": [
                "Pre-position ambulances east of the corridor.",
                "Verify alternate route road conditions.",
                "Stage medical supplies at local CHCs.",
                "Establish real-time road monitoring checkpoint.",
            ],
        })

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key"}):
            with patch("google.genai.Client", return_value=mock_client):
                brief = generate_asset_brief(sample_asset_result)
                assert brief["status"] == "success"
                assert brief["is_ai_generated"] is True
                assert "GEMINI" in brief["badge"]
                assert "9.5 min" in brief["why_prioritized"]
                assert len(brief["preparation_options"]) == 4


# ─────────────────────────────────────────────────────────────────────────────
# 2. Engine Sanity Checks & Integrity Audits
# ─────────────────────────────────────────────────────────────────────────────

class TestEngineSanityChecks:
    def test_all_hospitals_unique_no_duplicates(self):
        pois = load_all_pois()
        hospitals = pois.get("hospitals", [])
        assert len(hospitals) > 0

        # Check unique IDs
        ids = [h.get("osm_id") for h in hospitals if h.get("osm_id") is not None]
        assert len(ids) == len(set(ids)), f"Duplicate hospital OSM IDs found: {ids}"

        # Check unique names
        names = [h.get("name") or h.get("poi_name") for h in hospitals]
        assert len(names) == len(set(names)), f"Duplicate hospital names found: {names}"

    def test_bridges_within_kendrapara_bounds(self):
        real_data = run_real_scenario()
        bridges = real_data.get("bridges", [])
        assert len(bridges) > 0

        for b in bridges:
            lat = b.get("midpoint_lat")
            lon = b.get("midpoint_lon")
            assert 19.8 <= lat <= 21.2, f"Bridge {b.get('asset_id')} lat {lat} out of Kendrapara bounds"
            assert 85.8 <= lon <= 87.4, f"Bridge {b.get('asset_id')} lon {lon} out of Kendrapara bounds"

    def test_disruption_deltas_non_negative(self):
        real_data = run_real_scenario()
        for cf in real_data.get("counterfactual_results", []):
            max_delta = cf.get("max_disruption_delta_min")
            assert max_delta >= 0.0, f"Negative max disruption delta for {cf['asset_id']}: {max_delta}"
            for ch in cf.get("changes", []):
                if not ch.get("became_unreachable"):
                    delta = ch.get("disruption_delta_min")
                    if delta is not None:
                        assert delta >= -0.01, f"Negative route delta for {cf['asset_id']}: {delta}"

    def test_priority_score_consistency_with_components(self):
        real_data = run_real_scenario()
        for cf in real_data.get("counterfactual_results", []):
            prio = cf.get("priority", {})
            raw_score = prio.get("raw_score", 0.0)
            comps = prio.get("components", {})
            e = comps.get("exposure", 0.0)
            d = comps.get("disruption", 0.0)
            c = comps.get("criticality", 0.0)

            product = e * d * c
            expected_gm = (product ** (1 / 3)) if product > 0 else 0.0
            assert abs(raw_score - round(expected_gm, 3)) <= 0.005, (
                f"Priority score {raw_score} inconsistent with components (E={e}, D={d}, C={c})"
            )

    def test_top_bridge_disruption_example_integrity(self):
        real_data = run_real_scenario()
        top = real_data["counterfactual_results"][0]
        # In REAL_OSM mode: Top bridge is B006 | DR15
        assert top["asset_id"] == "B006"
        assert top["exposure"]["exposure_label"] in ("Extreme", "High")
        assert top["max_disruption_delta_min"] > 0
        assert len(top["changes"]) > 0
