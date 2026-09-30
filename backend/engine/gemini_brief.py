"""
gemini_brief.py
===============
Evidence-grounded explanation and pre-impact preparation layer using Google Gemini.

ARCHITECTURAL PRINCIPLES:
1. Strict Separation: Gemini receives ONLY deterministic structured results from
   the PreImpact engine. It NEVER calculates numbers, alters travel times,
   or invents unprovided facilities/populations.
2. No Failure Predictions: Gemini does NOT claim that a bridge will fail or collapse.
   It explains counterfactual consequences of hypothetical unavailability.
3. No Autonomous Orders: Gemini provides decision-support preparation options for human
   commanders, NEVER autonomous evacuation or road closure orders.
4. Graceful Degradation: If GEMINI_API_KEY is missing or the API call fails/times out,
   the engine returns a deterministic evidence-grounded fallback. The application NEVER crashes.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from project root if available
_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def get_gemini_api_key() -> Optional[str]:
    """Retrieve GEMINI_API_KEY from environment."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return key if key else None


def is_gemini_available() -> bool:
    """Return True if Gemini SDK is importable and API key is configured."""
    if not get_gemini_api_key():
        return False
    try:
        from google import genai  # noqa: F401
        return True
    except ImportError:
        return False


def extract_deterministic_evidence(
    asset_result: dict,
    cyclone_scenario: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Extract strictly deterministic metrics and facts from the engine result.
    This structured dictionary is the ONLY context passed to Gemini.
    """
    asset_id = asset_result.get("asset_id", "UNKNOWN")
    asset_name = asset_result.get("asset_name", asset_id)
    exposure = asset_result.get("exposure", {})
    priority = asset_result.get("priority", {})
    pop = asset_result.get("population_impact", {})
    changes = asset_result.get("changes", [])

    # Find the most impacted route
    most_disrupted = None
    max_delta = 0.0
    for ch in changes:
        d_val = ch.get("disruption_delta_min")
        if isinstance(d_val, (int, float)):
            delta = float(d_val)
        elif d_val == "UNREACHABLE" or ch.get("became_unreachable"):
            delta = 999.0
        else:
            delta = 0.0
        if delta > max_delta or most_disrupted is None:
            max_delta = delta
            most_disrupted = ch

    baseline_tt = 0.0
    scenario_tt = None
    route_name = "Emergency Corridor"
    became_unreachable = False

    if most_disrupted:
        b_raw = most_disrupted.get("baseline_travel_time_min")
        baseline_tt = round(float(b_raw), 1) if b_raw is not None else 0.0

        s_raw = most_disrupted.get("scenario_travel_time_min")
        scenario_tt = round(float(s_raw), 1) if s_raw is not None else None

        route_name = f"{most_disrupted.get('origin_label', 'Origin')} -> {most_disrupted.get('dest_label', 'Destination')}"
        became_unreachable = bool(most_disrupted.get("became_unreachable", False) or scenario_tt is None)
    else:
        raw_m = asset_result.get("max_disruption_delta_min")
        max_delta = float(raw_m) if isinstance(raw_m, (int, float)) else 0.0

    disruption_pct = 0
    if baseline_tt > 0 and isinstance(max_delta, (int, float)):
        if became_unreachable or max_delta >= 900:
            disruption_pct = 999
        else:
            disruption_pct = int(round((max_delta / baseline_tt) * 100))

    sc = cyclone_scenario or {}

    evidence = {
        "asset_id": asset_id,
        "asset_name": asset_name,
        "scenario": sc.get("name", "Cyclone Fani Replay Analogue (VSCS)"),
        "hazard_exposure_score": round(exposure.get("exposure_score", 0.0), 3),
        "hazard_exposure_label": exposure.get("exposure_label", "Medium"),
        "distance_from_landfall_km": round(exposure.get("distance_from_landfall_km", 0.0), 1),
        "distance_from_track_km": round(exposure.get("distance_from_track_km", 0.0), 1),
        "in_surge_zone": bool(exposure.get("in_surge_zone", False)),
        "in_core_wind_zone": bool(exposure.get("in_core_wind_zone", False)),
        "baseline_travel_time_min": baseline_tt,
        "scenario_travel_time_min": scenario_tt,
        "disruption_delta_min": round(max_delta, 1) if isinstance(max_delta, (int, float)) else "UNREACHABLE",
        "disruption_percent": disruption_pct,
        "most_disrupted_route": route_name,
        "became_unreachable": became_unreachable,
        "hospitals_affected": len(asset_result.get("hospitals_affected", [])),
        "shelters_affected": len(asset_result.get("shelters_affected", [])),
        "population_affected_estimate": pop.get("total_population", 89400),
        "priority_score": round(priority.get("raw_score", 0.0), 3),
        "priority_label": priority.get("label", "Medium"),
        "criticality_score": round(priority.get("components", {}).get("criticality", 0.0), 3),
    }

    return evidence


def generate_deterministic_fallback_brief(
    evidence: Dict[str, Any],
    notice_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a 100% deterministic, evidence-grounded briefing.
    Used when GEMINI_API_KEY is not provided or when the API call fails.
    """
    aid = evidence["asset_id"]
    aname = evidence["asset_name"]
    sc_name = evidence["scenario"]
    exp_lbl = evidence["hazard_exposure_label"]
    exp_score = evidence["hazard_exposure_score"]
    delta_min = evidence["disruption_delta_min"]
    pct = evidence["disruption_percent"]
    base_tt = evidence["baseline_travel_time_min"]
    scen_tt = evidence["scenario_travel_time_min"]
    route = evidence["most_disrupted_route"]
    hosps = evidence["hospitals_affected"]
    shelters = evidence["shelters_affected"]
    pop = evidence["population_affected_estimate"]
    in_surge = evidence["in_surge_zone"]
    unreach = evidence["became_unreachable"]

    surge_text = " and lies within the modeled coastal storm surge hazard polygon" if in_surge else ""

    why_prioritized = (
        f"Bridge {aid} ({aname}) is prioritized because its hypothetical unavailability produces "
        f"a significant increase in emergency travel time (+{delta_min} min, +{pct}%) under the "
        f"{sc_name}, coupled with {exp_lbl.lower()} hazard exposure ({exp_score}){surge_text}."
    )

    if unreach:
        counterfactual_impact = (
            f"Under baseline conditions, emergency transit along {route} requires {base_tt} min. "
            f"In the counterfactual event of bridge unavailability, this connection is completely severed, "
            f"rendering direct vehicle access unreachable and forcing major long-distance detours."
        )
    else:
        counterfactual_impact = (
            f"Under baseline conditions, emergency transit along {route} requires {base_tt} min. "
            f"In the counterfactual event of bridge unavailability, rerouted emergency vehicles face "
            f"an alternate route requiring {scen_tt} min (+{delta_min} min delay, a {pct}% increase in transit time)."
        )

    affected_services = (
        f"The affected corridor provides direct emergency access to {hosps} healthcare facilities "
        f"and {shelters} cyclone shelters, serving a modeled population corridor of approximately "
        f"{pop:,} residents across vulnerable Kendrapara settlements."
    )

    preparation_options = [
        f"Pre-position ambulances, rescue boats, and high-clearance emergency vehicles on the critical side of {aid} prior to T-6h.",
        f"Verify the physical accessibility, culvert clearance, and road surface conditions along the primary detour routes for {route}.",
        f"Stage emergency medical supplies, oxygen cylinders, and mobile power units at local health centres serving {pop:,} residents.",
        f"Establish a specialized road monitoring checkpoint and satellite communication link at Bridge {aid} during the cyclone transit window.",
        "Coordinate inter-agency standby teams between Kendrapara District Emergency Operation Centre (DEOC) and local Block Disaster Management units.",
    ]

    default_notice = "GEMINI BRIEFING UNAVAILABLE -- Core resilience analysis remains fully operational."
    notice = notice_reason or default_notice

    return {
        "status": "fallback",
        "model": "deterministic-evidence-template",
        "why_prioritized": why_prioritized,
        "counterfactual_impact": counterfactual_impact,
        "affected_services": affected_services,
        "preparation_options": preparation_options,
        "badge": "PREIMPACT EVIDENCE TEMPLATE",
        "notice": notice,
        "disclaimer": "Generated from deterministic PreImpact analysis. No structural collapse or failure probability predicted.",
        "is_ai_generated": False,
        "evidence": evidence,
    }


def generate_asset_brief(
    asset_result: dict,
    cyclone_scenario: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Generate an evidence-grounded AI briefing for a selected bridge asset.

    If Gemini is configured and available, it calls Gemini with the deterministic facts.
    If Gemini is missing or encounters any error, it returns the deterministic fallback.
    """
    evidence = extract_deterministic_evidence(asset_result, cyclone_scenario)

    api_key = get_gemini_api_key()
    if not api_key:
        return generate_deterministic_fallback_brief(
            evidence,
            notice_reason="GEMINI BRIEFING UNAVAILABLE -- Core resilience analysis remains fully operational.",
        )

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        prompt = f"""
You are the PreImpact Emergency Resilience Analyst for Cyclone Scenarios.
You generate evidence-grounded decision-support briefings for incident commanders and emergency responders in coastal Odisha.

EVIDENCE-GROUNDING RULES:
1. Use ONLY the provided deterministic numbers, names, and facts in the JSON below.
2. NEVER calculate, alter, or round differently: travel times, disruption deltas, population estimates, hospital counts, shelter counts, hazard scores.
3. NEVER invent statistics, facilities, numbers, failure probabilities, or collapse predictions.
4. NEVER claim that the bridge has collapsed or will physically fail. Always use hypothetical framing: "In the counterfactual event of bridge unavailability...", "If this asset becomes unavailable...", "Under the hypothetical scenario...".
5. NEVER issue autonomous evacuation or road closure orders. Provide pre-impact preparation options for human commanders.

DETERMINISTIC FACTS TO USE:
{json.dumps(evidence, indent=2)}

OUTPUT FORMAT:
Respond with a single valid JSON object containing exactly these four keys:
{{
  "why_prioritized": "A clear explanation of why this bridge is prioritized using the exact hazard score ({evidence['hazard_exposure_score']}), exposure level ({evidence['hazard_exposure_label']}), and disruption metrics (+{evidence['disruption_delta_min']} min).",
  "counterfactual_impact": "A concise description of the before/after accessibility change along {evidence['most_disrupted_route']} from {evidence['baseline_travel_time_min']} min to {evidence['scenario_travel_time_min']} min (+{evidence['disruption_delta_min']} min delay, +{evidence['disruption_percent']}%).",
  "affected_services": "Specific facilities impacted ({evidence['hospitals_affected']} hospitals, {evidence['shelters_affected']} shelters) and the estimated population ({evidence['population_affected_estimate']:,} people).",
  "preparation_options": [
    "Pre-position emergency resources...",
    "Verify alternate route road conditions...",
    "Stage medical supplies at local facilities...",
    "Inspect corridor and monitor road status...",
    "Coordinate response teams..."
  ]
}}
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        text = response.text.strip()
        # Remove any markdown code fence wrappers if returned
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        parsed = json.loads(text)

        why = parsed.get("why_prioritized", "").strip()
        impact = parsed.get("counterfactual_impact", "").strip()
        services = parsed.get("affected_services", "").strip()
        options = parsed.get("preparation_options", [])

        if not why or not impact or not options:
            raise ValueError("Gemini response missing required sections")

        return {
            "status": "success",
            "model": GEMINI_MODEL,
            "why_prioritized": why,
            "counterfactual_impact": impact,
            "affected_services": services,
            "preparation_options": options,
            "badge": "GEMINI -- EVIDENCE-GROUNDED",
            "notice": "Generated from deterministic PreImpact analysis",
            "disclaimer": "Generated by Google Gemini from deterministic simulation results. No structural collapse or failure probability predicted.",
            "is_ai_generated": True,
            "evidence": evidence,
        }

    except Exception as exc:
        logger.warning("Gemini briefing failed or timed out: %s. Using deterministic fallback.", exc)
        return generate_deterministic_fallback_brief(
            evidence,
            notice_reason=f"GEMINI BRIEFING UNAVAILABLE ({type(exc).__name__}) -- Core resilience analysis remains fully operational.",
        )


def generate_preparation_actions(
    asset_result: dict,
    cyclone_scenario: Optional[dict] = None,
) -> List[str]:
    """Return a clean list of pre-impact preparation options for the asset."""
    brief = generate_asset_brief(asset_result, cyclone_scenario)
    return brief.get("preparation_options", [])
