"""
counterfactual.py
=================
Core counterfactual simulation engine for PreImpact.

Public API
----------
simulate_asset_unavailability(G, asset, origin_node, dest_node, ...)
    → CounterfactualResult

calculate_accessibility_change(G, asset, origins, dest_node, ...)
    → list[AccessibilityChange]

Key design constraint:
    The base graph G is NEVER mutated.
    We always work on a view / subgraph copy.
"""

from __future__ import annotations

import copy
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)

# Speed assumption (km/h) when edge data is missing
_DEFAULT_SPEED_KMH = 40.0
_UNREACHABLE_SENTINEL = float("inf")


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class RouteResult:
    """Single-pair shortest-path result."""
    origin_node: int
    dest_node: int
    path_nodes: List[int]
    travel_time_s: float
    distance_m: float
    reachable: bool

    @property
    def travel_time_min(self) -> float:
        return round(self.travel_time_s / 60, 2) if self.reachable else _UNREACHABLE_SENTINEL

    @property
    def distance_km(self) -> float:
        return round(self.distance_m / 1000, 2) if self.reachable else _UNREACHABLE_SENTINEL


@dataclass
class AccessibilityChange:
    """Before/after accessibility for one origin→destination pair."""
    origin_node: int
    dest_node: int
    origin_label: str = "Origin"
    dest_label: str = "Destination"

    baseline: Optional[RouteResult] = None
    scenario: Optional[RouteResult] = None

    @property
    def disruption_delta_s(self) -> float:
        if self.baseline is None or self.scenario is None:
            return 0.0
        if not self.baseline.reachable:
            return 0.0
        if not self.scenario.reachable:
            return _UNREACHABLE_SENTINEL
        return self.scenario.travel_time_s - self.baseline.travel_time_s

    @property
    def disruption_delta_min(self) -> float:
        d = self.disruption_delta_s
        if d == _UNREACHABLE_SENTINEL:
            return _UNREACHABLE_SENTINEL
        return round(d / 60, 2)

    @property
    def became_unreachable(self) -> bool:
        if self.baseline is None or self.scenario is None:
            return False
        return self.baseline.reachable and not self.scenario.reachable

    @property
    def pct_increase(self) -> Optional[float]:
        if not self.baseline or not self.baseline.reachable:
            return None
        if not self.scenario or not self.scenario.reachable:
            return None
        if self.baseline.travel_time_s == 0:
            return None
        return round(
            (self.scenario.travel_time_s - self.baseline.travel_time_s)
            / self.baseline.travel_time_s * 100,
            1,
        )

    def to_dict(self) -> dict:
        return {
            "origin_node": self.origin_node,
            "dest_node": self.dest_node,
            "origin_label": self.origin_label,
            "dest_label": self.dest_label,
            "baseline_travel_time_min": (
                round(self.baseline.travel_time_min, 1) if self.baseline and self.baseline.reachable else None
            ),
            "baseline_distance_km": (
                round(self.baseline.distance_km, 2) if self.baseline and self.baseline.reachable else None
            ),
            "scenario_travel_time_min": (
                round(self.scenario.travel_time_min, 1)
                if self.scenario and self.scenario.reachable
                else None
            ),
            "scenario_distance_km": (
                round(self.scenario.distance_km, 2)
                if self.scenario and self.scenario.reachable
                else None
            ),
            "disruption_delta_min": (
                self.disruption_delta_min
                if self.disruption_delta_min != _UNREACHABLE_SENTINEL
                else "UNREACHABLE"
            ),
            "became_unreachable": self.became_unreachable,
            "pct_increase": self.pct_increase,
            "baseline_path": self.baseline.path_nodes if self.baseline else [],
            "scenario_path": self.scenario.path_nodes if self.scenario else [],
        }


@dataclass
class CounterfactualResult:
    """Full result of a counterfactual bridge-removal simulation."""
    asset_id: str
    asset_name: str

    # Core accessibility changes (one per origin→dest pair)
    changes: List[AccessibilityChange] = field(default_factory=list)

    # Aggregate stats
    max_disruption_delta_min: float = 0.0
    mean_disruption_delta_min: float = 0.0
    unreachable_count: int = 0
    affected_pairs_count: int = 0

    # Facility impact
    hospitals_affected: List[int] = field(default_factory=list)
    shelters_affected: List[int] = field(default_factory=list)

    # Graph metadata
    edges_removed: int = 0
    source: str = "computed"     # 'computed' | 'demo' | 'cached'

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "max_disruption_delta_min": round(self.max_disruption_delta_min, 1),
            "mean_disruption_delta_min": round(self.mean_disruption_delta_min, 1),
            "unreachable_count": self.unreachable_count,
            "affected_pairs_count": self.affected_pairs_count,
            "hospitals_affected": self.hospitals_affected,
            "shelters_affected": self.shelters_affected,
            "edges_removed": self.edges_removed,
            "source": self.source,
            "changes": [c.to_dict() for c in self.changes],
        }


# ── Internal helpers ───────────────────────────────────────────────────────

def _travel_time_weight(u: int, v: int, data: dict) -> float:
    """Weight function for shortest-path: travel_time (seconds)."""
    # Supports MultiDiGraph edge data dict
    if isinstance(data, dict):
        # data may be a single-edge dict or a multi-edge dict keyed by int
        if 0 in data or len(data) == 0:
            # multi-edge dict – pick minimum travel_time
            times = [
                e.get("travel_time", _fallback_tt(e))
                for e in data.values()
                if isinstance(e, dict)
            ]
            return min(times) if times else 999999
        return data.get("travel_time", _fallback_tt(data))
    return 999999


def _fallback_tt(data: dict) -> float:
    length = data.get("length", 200)
    speed  = data.get("speed_kph", _DEFAULT_SPEED_KMH)
    try:
        speed = float(speed)
    except (TypeError, ValueError):
        speed = _DEFAULT_SPEED_KMH
    return length / (max(speed, 1) * 1000 / 3600)


def _shortest_path(
    G: nx.MultiDiGraph,
    origin: int,
    dest: int,
) -> RouteResult:
    """
    Compute the shortest-travel-time path from origin to dest.
    Returns an unreachable RouteResult if no path exists.
    """
    if origin == dest:
        return RouteResult(
            origin_node=origin,
            dest_node=dest,
            path_nodes=[origin],
            travel_time_s=0.0,
            distance_m=0.0,
            reachable=True,
        )

    try:
        path = nx.shortest_path(G, origin, dest, weight="travel_time")
        # Accumulate travel time and distance along the path
        total_tt = 0.0
        total_dist = 0.0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edges = G[u][v]   # dict of parallel edges keyed by int
            # Pick the edge with minimum travel time
            best_tt = min(
                e.get("travel_time", _fallback_tt(e))
                for e in edges.values()
            )
            best_dist = min(
                e.get("length", 100)
                for e in edges.values()
            )
            total_tt   += best_tt
            total_dist += best_dist

        return RouteResult(
            origin_node=origin,
            dest_node=dest,
            path_nodes=path,
            travel_time_s=total_tt,
            distance_m=total_dist,
            reachable=True,
        )
    except nx.NetworkXNoPath:
        return RouteResult(
            origin_node=origin,
            dest_node=dest,
            path_nodes=[],
            travel_time_s=_UNREACHABLE_SENTINEL,
            distance_m=_UNREACHABLE_SENTINEL,
            reachable=False,
        )
    except nx.NodeNotFound as exc:
        logger.warning("Node not found in graph: %s", exc)
        return RouteResult(
            origin_node=origin,
            dest_node=dest,
            path_nodes=[],
            travel_time_s=_UNREACHABLE_SENTINEL,
            distance_m=_UNREACHABLE_SENTINEL,
            reachable=False,
        )


def _remove_asset_edges(G: nx.MultiDiGraph, edge_keys: List[Tuple]) -> nx.MultiDiGraph:
    """
    Return a copy of G with the specified edges removed.
    G is NOT mutated.
    """
    G_scenario = G.copy()
    removed = 0
    for u, v, k in edge_keys:
        if G_scenario.has_edge(u, v, k):
            G_scenario.remove_edge(u, v, k)
            removed += 1
        # Also remove reverse direction
        if G_scenario.has_edge(v, u, k):
            G_scenario.remove_edge(v, u, k)
            removed += 1
    logger.debug("Removed %d edge directions for counterfactual.", removed)
    return G_scenario, removed


# ── Public API ─────────────────────────────────────────────────────────────

def simulate_asset_unavailability(
    G: nx.MultiDiGraph,
    asset,                        # BridgeAsset
    origin_node: int,
    dest_node: int,
    origin_label: str = "Origin",
    dest_label: str = "Destination",
) -> AccessibilityChange:
    """
    Simulate removing `asset` from graph G and measure the change in
    travel time from origin_node to dest_node.

    Parameters
    ----------
    G           : base road-network graph (NOT mutated)
    asset       : BridgeAsset with .edge_keys
    origin_node : source node id
    dest_node   : target node id

    Returns
    -------
    AccessibilityChange with baseline and scenario RouteResults.
    """
    # Baseline (bridge present)
    baseline = _shortest_path(G, origin_node, dest_node)

    # Scenario (bridge absent)
    G_scenario, edges_removed = _remove_asset_edges(G, asset.edge_keys)
    scenario = _shortest_path(G_scenario, origin_node, dest_node)

    change = AccessibilityChange(
        origin_node=origin_node,
        dest_node=dest_node,
        origin_label=origin_label,
        dest_label=dest_label,
        baseline=baseline,
        scenario=scenario,
    )

    logger.info(
        "Counterfactual [%s] %s→%s  baseline=%.1fmin  scenario=%s  Δ=%s",
        asset.asset_id,
        origin_label,
        dest_label,
        baseline.travel_time_min,
        f"{scenario.travel_time_min:.1f}min" if scenario.reachable else "UNREACHABLE",
        (
            f"+{change.disruption_delta_min:.1f}min"
            if scenario.reachable
            else "UNREACHABLE"
        ),
    )
    return change


def calculate_accessibility_change(
    G: nx.MultiDiGraph,
    asset,                           # BridgeAsset
    origins: List[Tuple[int, str]],  # list of (node_id, label)
    destinations: List[Tuple[int, str]],  # list of (node_id, label)
) -> List[AccessibilityChange]:
    """
    Batch counterfactual: compute AccessibilityChange for every
    (origin, destination) pair.

    The scenario graph is built once and reused for all pairs.
    """
    G_scenario, _removed = _remove_asset_edges(G, asset.edge_keys)
    changes = []

    for o_node, o_label in origins:
        for d_node, d_label in destinations:
            baseline = _shortest_path(G, o_node, d_node)
            scenario = _shortest_path(G_scenario, o_node, d_node)
            changes.append(AccessibilityChange(
                origin_node=o_node,
                dest_node=d_node,
                origin_label=o_label,
                dest_label=d_label,
                baseline=baseline,
                scenario=scenario,
            ))

    return changes


def calculate_population_impact(
    changes: List[AccessibilityChange],
    population_map: Dict[int, int],     # node_id → estimated population
    threshold_min: float = 15.0,        # disruption threshold in minutes
) -> Dict[str, object]:
    """
    Estimate how many people are affected by the counterfactual disruption.

    A settlement node is counted as 'affected' if:
    - its route becomes unreachable, OR
    - the disruption delta exceeds threshold_min

    Parameters
    ----------
    changes        : output of calculate_accessibility_change
    population_map : dict mapping origin node → settlement population
    threshold_min  : minimum disruption (minutes) to count as affected

    Returns
    -------
    dict with keys: affected_population, affected_settlements, total_population
    """
    affected_nodes = set()
    total_pop = sum(population_map.values())

    for ch in changes:
        origin = ch.origin_node
        if origin not in population_map:
            continue
        if ch.became_unreachable:
            affected_nodes.add(origin)
        elif (
            ch.disruption_delta_min != _UNREACHABLE_SENTINEL
            and ch.disruption_delta_min >= threshold_min
        ):
            affected_nodes.add(origin)

    affected_pop = sum(population_map.get(n, 0) for n in affected_nodes)
    return {
        "affected_population": affected_pop,
        "affected_settlements": len(affected_nodes),
        "total_population": total_pop,
        "threshold_min": threshold_min,
    }


def calculate_facility_impact(
    changes: List[AccessibilityChange],
    hospital_nodes: List[int],
    shelter_nodes: List[int],
) -> Dict[str, List[int]]:
    """
    Return which hospitals/shelters are affected (their route became
    worse or unreachable in the counterfactual scenario).
    """
    affected_hospitals = []
    affected_shelters  = []

    for ch in changes:
        dest = ch.dest_node
        if ch.disruption_delta_min > 0 or ch.became_unreachable:
            if dest in hospital_nodes:
                if dest not in affected_hospitals:
                    affected_hospitals.append(dest)
            if dest in shelter_nodes:
                if dest not in affected_shelters:
                    affected_shelters.append(dest)

    return {
        "hospitals_affected": affected_hospitals,
        "shelters_affected": affected_shelters,
    }


def calculate_priority(
    exposure_score: float,        # 0-1 (how exposed the asset is to the cyclone)
    disruption_score: float,      # 0-1 (normalised network disruption)
    criticality_score: float,     # 0-1 (importance of affected facilities)
) -> Dict[str, object]:
    """
    Compute a Resilience Priority Score.

    Priority = Exposure × Disruption × Criticality
    (geometric mean to keep the score balanced)

    Returns
    -------
    dict with raw_score (0-1), label ('Low'|'Medium'|'High'|'Critical'),
    and component breakdown.
    """
    # Geometric mean of the three components
    product = exposure_score * disruption_score * criticality_score
    raw_score = math.pow(product, 1 / 3) if product > 0 else 0.0
    raw_score = min(max(raw_score, 0.0), 1.0)

    if raw_score >= 0.70:
        label = "Critical"
    elif raw_score >= 0.45:
        label = "High"
    elif raw_score >= 0.25:
        label = "Medium"
    else:
        label = "Low"

    return {
        "raw_score": round(raw_score, 3),
        "label": label,
        "components": {
            "exposure": round(exposure_score, 3),
            "disruption": round(disruption_score, 3),
            "criticality": round(criticality_score, 3),
        },
    }


def run_full_counterfactual(
    G: nx.MultiDiGraph,
    asset,                              # BridgeAsset
    settlement_nodes: List[Tuple[int, str]],
    hospital_nodes:   List[Tuple[int, str]],
    shelter_nodes:    List[Tuple[int, str]],
    population_map:   Dict[int, int],
    exposure_score:   float = 0.7,
    disruption_threshold_min: float = 15.0,
) -> CounterfactualResult:
    """
    Run the complete counterfactual pipeline for a single asset.

    Pipeline:
    1. calculate_accessibility_change (all settlement→hospital/shelter pairs)
    2. calculate_population_impact
    3. calculate_facility_impact
    4. calculate_priority
    5. Assemble CounterfactualResult
    """
    all_destinations = hospital_nodes + shelter_nodes
    changes = calculate_accessibility_change(G, asset, settlement_nodes, all_destinations)

    pop_impact = calculate_population_impact(changes, population_map, disruption_threshold_min)
    fac_impact = calculate_facility_impact(
        changes,
        [n for n, _ in hospital_nodes],
        [n for n, _ in shelter_nodes],
    )

    # Disruption score: normalise by maximum delta (cap at 120 min)
    # Unreachable routes count as 120-min equivalent (maximum disruption)
    UNREACHABLE_EQUIV_MIN = 120.0   # treat unreachable = 2-hour penalty
    deltas = []
    for ch in changes:
        if ch.became_unreachable:
            deltas.append(UNREACHABLE_EQUIV_MIN)
        elif ch.disruption_delta_min not in (None, _UNREACHABLE_SENTINEL) and ch.disruption_delta_min > 0:
            deltas.append(float(ch.disruption_delta_min))

    max_delta     = max(deltas) if deltas else 0.0
    mean_delta    = sum(deltas) / len(deltas) if deltas else 0.0
    # Use actual finite delta for reporting (not the unreachable equivalent)
    finite_deltas = [
        ch.disruption_delta_min for ch in changes
        if not ch.became_unreachable
        and ch.disruption_delta_min not in (None, _UNREACHABLE_SENTINEL)
        and ch.disruption_delta_min > 0
    ]
    reported_max_delta  = max(finite_deltas) if finite_deltas else 0.0
    reported_mean_delta = sum(finite_deltas) / len(finite_deltas) if finite_deltas else 0.0
    disruption_score = min(max_delta / UNREACHABLE_EQUIV_MIN, 1.0)

    # Criticality score: proportion of destinations that are hospitals
    n_hosp_affected = len(fac_impact["hospitals_affected"])
    n_shelt_affected = len(fac_impact["shelters_affected"])
    total_facilities = len(hospital_nodes) + len(shelter_nodes)
    criticality_score = (
        (n_hosp_affected * 2 + n_shelt_affected)
        / max(total_facilities * 2, 1)
    )
    criticality_score = min(criticality_score, 1.0)

    priority = calculate_priority(exposure_score, disruption_score, criticality_score)

    unreachable = sum(1 for ch in changes if ch.became_unreachable)
    affected_pairs = sum(1 for ch in changes if ch.disruption_delta_min > 0 or ch.became_unreachable)

    result = CounterfactualResult(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        changes=changes,
        max_disruption_delta_min=round(reported_max_delta, 1),
        mean_disruption_delta_min=round(reported_mean_delta, 1),
        unreachable_count=unreachable,
        affected_pairs_count=affected_pairs,
        hospitals_affected=fac_impact["hospitals_affected"],
        shelters_affected=fac_impact["shelters_affected"],
        source="computed",
    )

    # Attach priority to result (extra attributes)
    result.priority = priority
    result.population_impact = pop_impact

    return result
