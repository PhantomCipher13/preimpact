# PREIMPACT — 2-Minute Demonstration Script

> **"We don't predict that a bridge will fail. We show responders what happens if it does — before the cyclone arrives."**

---

### [0:00 - 0:15] — The Threat: Cyclone Approaching Coastal Odisha
- **Presenter:**
  > *"Disaster response in coastal Odisha faces a critical operational blind spot: when an Extremely Severe Cyclone makes landfall, which roads and bridges will cause the most catastrophic emergency-access paralysis if they become impassable?"*
- **Screen Action:**
  - Open PreImpact dashboard (`http://localhost:5173`).
  - Point to the **Top Situational Awareness Banner**:
    - **Scenario:** *Cyclone Fani Replay Analogue (VSCS)*
    - **Region:** *Kendrapara District, Coastal Odisha*
    - **Exposure Window:** *T-6h to T+12h Landfall*
    - **Peak Winds:** *175 km/h* | **Storm Surge:** *3.5m*

---

### [0:15 - 0:30] — Hazard Exposure & Footprint
- **Presenter:**
  > *"PreImpact models the deterministic multi-hazard footprint directly onto the genuine OpenStreetMap road network: an 85 km gale-force wind swath, a 45 km destructive core wind zone, and an 8-point coastal storm surge polygon along the vulnerable Kendrapara fringe."*
- **Screen Action:**
  - Hover over the cyan coastal storm surge polygon and orange dashed wind buffers on the Leaflet map.
  - Point to the candidate progression chips:
    $$\text{126 Total Bridges} \longrightarrow \text{126 Bridges in Hazard Footprint} \longrightarrow \text{12 Analyzed Critical Assets}$$

---

### [0:30 - 0:45] — Identify the Top Critical Asset
- **Presenter:**
  > *"Every bridge in the corridor is scored for hazard exposure. But high exposure alone doesn't tell responders what will happen to emergency access. To answer that, PreImpact executes a counterfactual simulation."*
- **Screen Action:**
  - Point to the top prioritized asset on the left ranking list:
    **Bridge B006 | DR15** (Hazard Exposure: `Extreme`, score `0.965`, 10.0 km from landfall).

---

### [0:45 - 1:00] — Simulate Counterfactual Unavailability
- **Presenter:**
  > *"Watch what happens when we simulate the hypothetical unavailability of Bridge B006."*
- **Screen Action:**
  - Click the **`▶ RUN COUNTERFACTUAL SIMULATION`** button in the top toolbar.
  - Watch the automated 3-phase simulation sequence:
    1. **Phase 1 (Baseline):** Blue solid line illustrates unobstructed baseline access from Aul settlement to Mahakalapada Shelter CS-07 (**16.7 min**).
    2. **Phase 2 (Severance):** Bridge B006 flashes with a pulsing red ✖ marker — direct corridor severed.
    3. **Phase 3 (Rerouting):** NetworkX Dijkstra recalculates alternate detour routes in real time.

---

### [1:00 - 1:20] — Emergency Route Disruption Measured
- **Presenter:**
  > *"Look at the right panel: the primary emergency story is instantly understandable within 10 seconds:*
  > *Baseline travel time was 16.7 minutes. With Bridge B006 unavailable, rerouted emergency vehicles face 26.3 minutes — a +9.5 minute delay (+57% increase in transit time)."*
- **Screen Action:**
  - Highlight the **Instant Story Card**:
    $$\text{16.7 min} \longrightarrow \text{26.3 min} \quad (\mathbf{+9.5\text{ min emergency travel}})$$
  - Point to the orange dashed detour line on the map.

---

### [1:20 - 1:35] — Downstream Consequence & Resilience Priority
- **Presenter:**
  > *"This isn't an isolated delay. This bridge unavailability cascades across the healthcare and shelter network:*
  > *- 3 hospitals experience delayed ambulance transit (up to +6.4 min to Govt Hospital Ayeba).*
  > *- 1 key cyclone shelter is delayed by +9.5 minutes.*
  > *- ~89,400 vulnerable coastal residents are affected.*
  > *Our engine computes a composite Resilience Priority Score of 0.391, transparently breaking down Exposure (97%), Disruption (8%), and Criticality (78%)."*
- **Screen Action:**
  - Point to the Consequential Impact Grid (Hospitals, Shelters, Population) and the Resilience Priority breakdown bar.

---

### [1:35 - 1:55] — Google Gemini Evidence-Grounded Briefing
- **Presenter:**
  > *"Finally, Google Gemini synthesizes these deterministic facts into an operational briefing for emergency incident commanders.*
  > *Notice that Gemini receives ONLY our pre-calculated numbers — it cannot hallucinate population numbers or invent failure probabilities.*
  > *It provides 4 structured operational sections:*
  > *A: Why Prioritized, B: Counterfactual Impact, C: Affected Services, and D: Actionable Pre-Impact Preparation Options — such as pre-positioning ambulances on the critical side of the bridge before landfall and verifying alternate culvert clearance."*
- **Screen Action:**
  - Scroll down the **AI Response Brief** card:
    - Badge: `GEMINI — EVIDENCE-GROUNDED`
    - Check the 5 preparation action bullets.

---

### [1:55 - 2:00] — The Core Takeaway
- **Presenter (Closing Statement):**
  > **"We don't predict that a bridge will fail.**
  > **We show responders what happens if it does — before the cyclone arrives."**

---

### Demonstration Checklist
- [x] Backend running on `http://127.0.0.1:8000` (`REAL_OSM` mode active)
- [x] Frontend running on `http://localhost:5173`
- [x] `▶ RUN COUNTERFACTUAL SIMULATION` tested and animating
- [x] Gemini briefing active with fallback safeguard
- [x] 10-second comprehension story verified
