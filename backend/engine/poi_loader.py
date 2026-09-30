"""
poi_loader.py
=============
Loads Points of Interest (hospitals, shelters, health facilities, etc.)
from OpenStreetMap via Overpass API for the Kendrapara region.

Caches results locally. Falls back to hard-coded demo POIs if unavailable.

Sources:
  - amenity=hospital
  - amenity=clinic / health_facility
  - emergency=shelter / disaster_response
  - amenity=shelter
  - government=evacuation_centre (rare)
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).parent.parent
_CACHE_DIR   = _BACKEND_DIR / "data" / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

HOSPITALS_CACHE = _CACHE_DIR / "hospitals_kendrapara.json"
SHELTERS_CACHE  = _CACHE_DIR / "shelters_kendrapara.json"
POIS_CACHE      = _CACHE_DIR / "pois_kendrapara.json"

# Kendrapara bbox — north, south, east, west (lat/lon)
BBOX = {"north": 20.58, "south": 20.43, "east": 86.68, "west": 86.43}
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# ── Overpass helpers ─────────────────────────────────────────────────────

def _overpass_query(query: str, timeout: int = 30) -> Optional[dict]:
    try:
        resp = requests.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=timeout,
            headers={"User-Agent": "PreImpact-ResilienceEngine/0.1"},
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.warning("Overpass query failed: %s", exc)
        return None


def _bbox_filter() -> str:
    b = BBOX
    return f"{b['south']},{b['west']},{b['north']},{b['east']}"


def _parse_elements(data: dict) -> List[dict]:
    if not data:
        return []
    elements = []
    for el in data.get("elements", []):
        if el.get("type") == "node" and "lat" in el and "lon" in el:
            tags = el.get("tags", {})
            elements.append({
                "osm_id": el["id"],
                "lat": el["lat"],
                "lon": el["lon"],
                "name": tags.get("name", tags.get("name:en", "Unknown")),
                "tags": tags,
                "type": "node",
                "osm_source": "REAL",
            })
        elif el.get("type") in ("way", "relation"):
            # Use centre if available
            centre = el.get("center", {})
            lat = centre.get("lat")
            lon = centre.get("lon")
            if lat and lon:
                tags = el.get("tags", {})
                elements.append({
                    "osm_id": el["id"],
                    "lat": lat,
                    "lon": lon,
                    "name": tags.get("name", tags.get("name:en", "Unknown")),
                    "tags": tags,
                    "type": el["type"],
                    "osm_source": "REAL",
                })
    return elements


# ── Hospital loading ──────────────────────────────────────────────────────

HOSPITAL_QUERY = """
[out:json][timeout:30];
(
  node["amenity"="hospital"]({bbox});
  node["amenity"="clinic"]({bbox});
  node["amenity"="health_post"]({bbox});
  node["healthcare"="hospital"]({bbox});
  node["healthcare"="clinic"]({bbox});
  way["amenity"="hospital"]({bbox});
  way["healthcare"="hospital"]({bbox});
);
out center;
""".strip()


def fetch_hospitals(force: bool = False) -> List[dict]:
    if not force and HOSPITALS_CACHE.exists():
        logger.info("Loading hospitals from cache.")
        return json.loads(HOSPITALS_CACHE.read_text())

    logger.info("Fetching hospitals from Overpass …")
    q = HOSPITAL_QUERY.replace("{bbox}", _bbox_filter())
    data = _overpass_query(q, timeout=40)
    hospitals = _parse_elements(data) if data else []

    # Tag each with facility_type
    for h in hospitals:
        t = h["tags"]
        if t.get("amenity") == "hospital" or t.get("healthcare") == "hospital":
            h["facility_type"] = "hospital"
        else:
            h["facility_type"] = "clinic"

    if hospitals:
        HOSPITALS_CACHE.write_text(json.dumps(hospitals, indent=2))
        logger.info("Cached %d hospitals.", len(hospitals))
    else:
        logger.warning("No hospitals found via Overpass. Will use fallback.")

    return hospitals


# ── Shelter loading ───────────────────────────────────────────────────────

SHELTER_QUERY = """
[out:json][timeout:30];
(
  node["amenity"="shelter"]({bbox});
  node["emergency"="shelter"]({bbox});
  node["social_facility"="shelter"]({bbox});
  node["cyclone_shelter"="yes"]({bbox});
  node["building"="cyclone_shelter"]({bbox});
  node["government"="evacuation_centre"]({bbox});
  way["amenity"="shelter"]({bbox});
  way["emergency"="shelter"]({bbox});
  way["building"="cyclone_shelter"]({bbox});
);
out center;
""".strip()


def fetch_shelters(force: bool = False) -> List[dict]:
    if not force and SHELTERS_CACHE.exists():
        logger.info("Loading shelters from cache.")
        return json.loads(SHELTERS_CACHE.read_text())

    logger.info("Fetching cyclone shelters from Overpass …")
    q = SHELTER_QUERY.replace("{bbox}", _bbox_filter())
    data = _overpass_query(q, timeout=40)
    shelters = _parse_elements(data) if data else []

    for s in shelters:
        s["facility_type"] = "shelter"

    if shelters:
        SHELTERS_CACHE.write_text(json.dumps(shelters, indent=2))
        logger.info("Cached %d shelters.", len(shelters))
    else:
        logger.info("No shelters found via Overpass. Will use fallback.")

    return shelters


# ── Fallback POIs ─────────────────────────────────────────────────────────
# Hard-coded from manual OSM inspection + local knowledge.
# Labelled ESTIMATED/FALLBACK — approximate coordinates for decision support only.

FALLBACK_HOSPITALS = [
    {
        "osm_id": None, "lat": 20.4955, "lon": 86.5225,
        "name": "Kendrapara District Hospital", "facility_type": "hospital",
        "tags": {"amenity": "hospital"}, "osm_source": "ESTIMATED",
        "note": "Approximate location from OSM search — verify before operational use"
    },
    {
        "osm_id": None, "lat": 20.5063, "lon": 86.4194,
        "name": "Rajnagar CHC", "facility_type": "clinic",
        "tags": {"amenity": "clinic"}, "osm_source": "ESTIMATED",
        "note": "Approximate location"
    },
    {
        "osm_id": None, "lat": 20.5440, "lon": 86.6590,
        "name": "Aul CHC", "facility_type": "clinic",
        "tags": {"amenity": "clinic"}, "osm_source": "ESTIMATED",
        "note": "Approximate location"
    },
]

FALLBACK_SHELTERS = [
    {
        "osm_id": None, "lat": 20.5142, "lon": 86.4421,
        "name": "Rajnagar Cyclone Shelter", "facility_type": "shelter",
        "tags": {"building": "cyclone_shelter"}, "osm_source": "ESTIMATED",
        "note": "Approximate location"
    },
    {
        "osm_id": None, "lat": 20.4851, "lon": 86.5003,
        "name": "Kendrapara Shelter CS-01", "facility_type": "shelter",
        "tags": {"building": "cyclone_shelter"}, "osm_source": "ESTIMATED",
        "note": "Approximate location"
    },
    {
        "osm_id": None, "lat": 20.5563, "lon": 86.5831,
        "name": "Mahakalapada Shelter CS-07", "facility_type": "shelter",
        "tags": {"building": "cyclone_shelter"}, "osm_source": "ESTIMATED",
        "note": "Approximate location"
    },
    {
        "osm_id": None, "lat": 20.5720, "lon": 86.4882,
        "name": "Satabhaya Shelter CS-12", "facility_type": "shelter",
        "tags": {"building": "cyclone_shelter"}, "osm_source": "ESTIMATED",
        "note": "Approximate location"
    },
]

FALLBACK_SETTLEMENTS = [
    {"name": "Kendrapara Town",     "lat": 20.4921, "lon": 86.5228, "population_estimate": 32000, "osm_source": "ESTIMATED"},
    {"name": "Rajnagar",            "lat": 20.5063, "lon": 86.4194, "population_estimate": 8500,  "osm_source": "ESTIMATED"},
    {"name": "Mahakalapada",        "lat": 20.5590, "lon": 86.5843, "population_estimate": 7200,  "osm_source": "ESTIMATED"},
    {"name": "Pattamundai",         "lat": 20.5712, "lon": 86.5717, "population_estimate": 15000, "osm_source": "ESTIMATED"},
    {"name": "Aul",                 "lat": 20.5444, "lon": 86.6588, "population_estimate": 9800,  "osm_source": "ESTIMATED"},
    {"name": "Marsaghai",           "lat": 20.5147, "lon": 86.5921, "population_estimate": 5500,  "osm_source": "ESTIMATED"},
    {"name": "Derabish",            "lat": 20.5280, "lon": 86.4420, "population_estimate": 6100,  "osm_source": "ESTIMATED"},
    {"name": "Satabhaya Village",   "lat": 20.5760, "lon": 86.4872, "population_estimate": 2100,  "osm_source": "ESTIMATED"},
    {"name": "Kansarpal",           "lat": 20.4782, "lon": 86.5512, "population_estimate": 3200,  "osm_source": "ESTIMATED"},
]


def load_all_pois(force: bool = False) -> Dict[str, List[dict]]:
    """
    Load hospitals and shelters.
    Returns dict with 'hospitals', 'shelters', 'settlements'.
    Tries live Overpass first, falls back to hard-coded estimates.
    """
    if not force and POIS_CACHE.exists():
        logger.info("Loading POIs from cache: %s", POIS_CACHE)
        return json.loads(POIS_CACHE.read_text())

    hospitals = fetch_hospitals(force=force)
    time.sleep(1)   # be polite to Overpass
    shelters  = fetch_shelters(force=force)

    # Merge with fallbacks where OSM returns nothing
    hosp_source = "osm" if hospitals else "fallback"
    shelt_source = "osm" if shelters else "fallback"

    if not hospitals:
        logger.info("Using fallback hospital data (ESTIMATED).")
        hospitals = FALLBACK_HOSPITALS

    if not shelters:
        logger.info("Using fallback shelter data (ESTIMATED).")
        shelters = FALLBACK_SHELTERS

    result = {
        "hospitals": hospitals,
        "shelters": shelters,
        "settlements": FALLBACK_SETTLEMENTS,   # always estimated
        "hospital_source": hosp_source,
        "shelter_source":  shelt_source,
        "settlement_source": "estimated",
    }

    POIS_CACHE.write_text(json.dumps(result, indent=2))
    logger.info(
        "POIs ready: %d hospitals (%s), %d shelters (%s), %d settlements",
        len(hospitals), hosp_source,
        len(shelters),  shelt_source,
        len(FALLBACK_SETTLEMENTS),
    )
    return result
