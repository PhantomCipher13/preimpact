# PREIMPACT — Milestone 4 Walkthrough: Gemini Integration & Final Hackathon Polish

## Purpose & Summary

PreImpact is a disaster-response decision-support prototype for cyclone scenarios in the Kendrapara district of coastal Odisha.

**Core Research Question:**
> *"If this exposed road/bridge becomes unavailable during the cyclone, what emergency-access disruption would occur, and what should responders prepare for first?"*

This walkthrough documents the completion and verification of **Milestone 4 — Google Gemini + Final Hackathon Polish**.

---

## 1. Google Gemini Evidence-Grounded Briefing

PreImpact integrates **Google Gemini 2.5 Flash** (via the `google-genai` Python SDK) as an explanation and recommendation layer:

### Architectural Separation
1. **Strict Evidence Grounding:** Gemini receives ONLY structured, pre-computed deterministic facts from the engine:
   ```json
   {
     "asset_id": "B006",
     "asset_name": "DR15",
     "scenario": "Cyclone Fani Replay Analogue (VSCS)",
     "hazard_exposure_score": 0.965,
     "hazard_exposure_label": "Extreme",
     "baseline_travel_time_min": 16.7,
     "scenario_travel_time_min": 26.3,
     "disruption_delta_min": 9.53,
     "disruption_percent": 57,
     "hospitals_affected": 3,
     "shelters_affected": 1,
     "population_affected_estimate": 89400
   }
   ```
2. **Zero Hallucination Guardrails:**
   - Gemini does NOT calculate or alter travel times, deltas, or population figures.
   - Gemini does NOT invent facilities, numbers, or failure probabilities.
   - Gemini does NOT claim infrastructure will physically fail or collapse.
3. **Four Structured Sections:**
   - **A. Why Prioritized:** Contextualizes why Bridge B006 is flagged under extreme exposure and coastal surge proximity.
   - **B. Counterfactual Impact:** Explains the before/after accessibility change from 16.7 min to 26.3 min (+57%).
   - **C. Affected Services:** Identifies the 3 hospitals, 1 shelter, and ~89,400 residents in the corridor.
   - **D. Pre-Impact Preparation Options:** Suggests 5 actionable operational steps (pre-positioning ambulances on the critical side of the bridge, verifying alternate culvert clearance, staging supplies, corridor monitoring, inter-agency coordination).
4. **Policy Constraint:** Never issues autonomous evacuation or road closure orders.

---

## 2. Failure Handling & Graceful Degradation

The application operates seamlessly with or without a Gemini API key:
- If `GEMINI_API_KEY` is omitted, empty, or fails:
  - Automatically generates a 100% deterministic, evidence-grounded fallback briefing.
  - Displays: `GEMINI BRIEFING UNAVAILABLE -- Core resilience analysis remains fully operational.`
  - The application and API **never** crash.
- Added `.env.example` with `GEMINI_API_KEY=` template.

---

## 3. The 10-Second Primary Disruption Story (UX Hierarchy)

Selecting any bridge on the map or ranking table immediately communicates:
1. **Bridge Asset ID & Name:** `BRIDGE B006 | DR15`
2. **Hazard Exposure:** `EXTREME (0.965)` with surge and wind meta
3. **IF UNAVAILABLE Banner:**
   $$\mathbf{16.7\text{ min} \longrightarrow 26.3\text{ min} \quad (+9.5\text{ min emergency travel delay})}$$
4. **Consequential Impact Grid:**
   - `3 Hospitals Affected`
   - `1 Shelter Affected`
   - `~89,400 Estimated Population`
5. **Resilience Priority Score:** `0.391` (`Medium`, with $E, D, C$ component bars).
6. **AI Response Brief:** Structured decision-support text with operational recommendations.

---

## 4. Interactive Counterfactual Demo Simulation

A prominent **`▶ RUN COUNTERFACTUAL SIMULATION`** button triggers a guided walkthrough:
- **Phase 1 (Baseline Access):** Solid blue line highlights unobstructed access from Aul to Mahakalapada Shelter (16.7 min).
- **Phase 2 (Bridge Severed):** Bridge B006 flashes with a pulsing red ✖ marker and route severance notice.
- **Phase 3 (Rerouting Complete):** Alternate orange dashed detour line appears (+9.5 min delay), updating all downstream hospital delays and synthesizing the AI brief.
- Floating simulation HUD on the map guides evaluators through each phase.

---

## 5. Trust, Governance & Methodology Panel

Redesigned `MethodologyNote.jsx` emphasizes responsible AI:
- **Core Statement:**
  > *"PreImpact does not predict infrastructure failure. It evaluates hypothetical infrastructure unavailability and measures the resulting emergency-access disruption under a modeled cyclone scenario."*
- **Pipeline Progression:**
  `Hazard Exposure → Counterfactual Unavailability → Network Rerouting → Accessibility Change → Consequence → Resilience Priority → Human Decision Support`
- **Transparent Provenance:**
  - `REAL DATA:` OSM road network (1,672 nodes, 4,115 edges), 126 detected bridges, 5 verified OSM hospitals.
  - `MODELED:` Cyclone hazard footprint, NetworkX Dijkstra route consequences, Resilience priority.
  - `ESTIMATED:` Population estimates (~89,400), fallback cyclone shelter coordinates.

---

## 6. Automated Testing (118 Tests Passing)

All **118 unit and integration tests** pass in **3.79 seconds**:

```powershell
C:\Python311\python.exe -m pytest tests/ -v
```

```
tests/test_counterfactual.py ..................................... [ 31%]
tests/test_gemini.py         ...........                           [ 40%]
tests/test_milestone2.py     ..................................... [ 84%]
tests/test_milestone3.py     ..................                    [100%]

============================= 118 passed in 3.79s =============================
```

### Verified Milestone 4 Tests (`test_gemini.py`)
- `test_gemini_fallback_when_key_missing`: Verifies fallback status and notice when API key is missing.
- `test_deterministic_evidence_extraction`: Confirms exact mathematical fidelity of facts passed to Gemini.
- `test_briefing_has_all_four_sections`: Validates presence of sections A, B, C, D.
- `test_preparation_actions_actionable`: Validates $\ge 4$ actionable recommendation bullets.
- `test_no_failure_claims_in_briefing`: Verifies complete absence of failure/collapse terminology.
- `test_mock_gemini_live_call_parsing`: Tests JSON response parsing and markdown strip handling.
- `test_all_hospitals_unique_no_duplicates`: Confirms zero duplicate hospitals.
- `test_bridges_within_kendrapara_bounds`: Asserts all 126 bridges fall within Kendrapara bounding box.
- `test_disruption_deltas_non_negative`: Asserts all travel-time deltas $\ge 0$.
- `test_priority_score_consistency_with_components`: Mathematical verification of $(E \times D \times C)^{1/3}$.
- `test_top_bridge_disruption_example_integrity`: End-to-end verification of `B006 | DR15`.

---

## 7. Build & Service Verification

- **Production Frontend Build:** `npm run build` succeeds in **211ms** with 0 errors.
- **Backend API:** `http://127.0.0.1:8000` (FastAPI / Uvicorn running in background).
- **Frontend Dashboard:** `http://localhost:5173` (Vite dev server running in background).
- **Interactive API Docs:** `http://127.0.0.1:8000/docs`.
- **2-Minute Demo Script:** Documented in [`DEMO_SCRIPT.md`](file:///c:/Users/Admin/Downloads/Internal%20hackathon/preimpact/DEMO_SCRIPT.md).
