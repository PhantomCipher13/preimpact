# PreImpact

## Counterfactual Infrastructure Resilience Engine

> **"PreImpact evaluates hypothetical infrastructure unavailability under a modeled cyclone scenario and quantifies the resulting emergency-access disruption."**
>
> **"PreImpact does not predict infrastructure failure."**

[![Tests](https://img.shields.io/badge/tests-118%20passed-brightgreen)](#automated-testing)
[![Modes](https://img.shields.io/badge/modes-REAL__OSM%20%7C%20PARTIAL__REAL__DATA%20%7C%20DEMO-blue)](#data-provenance--transparency)
[![Region](https://img.shields.io/badge/region-Kendrapara%2C%20Odisha-orange)](#problem-context)
[![Google AI](https://img.shields.io/badge/Google%20AI-Gemini%202.5%20Flash-8E24AA)](#technologies-used)

---

## 1. Problem Statement & Research Question

During major cyclonic events in coastal Odisha, emergency responders face severe infrastructure uncertainty:
- Responders cannot know in advance which compromised roads or bridges will cause the most catastrophic emergency-access paralysis.
- Traditional risk models either attempt structural collapse predictions (which are unreliable without high-density physical sensor telemetry) or merely display hazard overlays without calculating network connectivity.
- Incident commanders lack actionable pre-impact decision support: where to pre-position ambulances, which detour routes to inspect, and which vulnerable communities face isolation before the cyclone makes landfall.

PreImpact addresses a single, actionable question:

> **"If this exposed bridge becomes unavailable during the cyclone, what emergency-access disruption will occur, and what should responders prepare for first?"**

Instead of predicting whether a bridge will physically fail, PreImpact evaluates the **consequence of hypothetical bridge unavailability** on critical access routes to hospitals and cyclone shelters.

---

## 2. Core Workflow & Pipeline

```
Cyclone Scenario (Historical Replay Analogue — Cyclone Fani 2019)
      ↓
Hazard Exposure (Wind swath & storm surge inundation proximity)
      ↓
Exposed Infrastructure (Candidate filtering: 126 Total → 126 Exposed → 12 Critical)
      ↓
Counterfactual Unavailability (Hypothetical edge removal in in-memory graph)
      ↓
Network Rerouting (NetworkX Dijkstra shortest-path recalculation)
      ↓
Accessibility / Travel-Time Change (Disruption delta Δt and route severance detection)
      ↓
Hospitals / Shelters / Population Impact (Downstream facilities & population isolated)
      ↓
Resilience Priority (Geometric mean of Exposure × Disruption × Criticality)
      ↓
Evidence-Grounded AI Brief (Actionable preparation options via Google Gemini)
```

---

## 3. Technologies Used

PreImpact is implemented with a lightweight, reproducible open-source stack:

- **Python (3.11+):** Core graph routing, hazard exposure mathematics, and backend services.
- **NetworkX:** In-memory road graph representation, subgraph isolation, edge removal, and Dijkstra shortest-path recalculation.
- **FastAPI & Uvicorn:** High-performance RESTful backend API serving simulation results and POI datasets.
- **React (18) & Vite:** Component-based frontend interface with light soft glassmorphism architecture.
- **Leaflet:** Interactive geospatial visualization of cyclone tracks, wind swaths, surge zones, bridges, and counterfactual routes.
- **Google Gemini Integration (`google-genai` SDK):** Gemini 2.5 Flash used exclusively as an evidence-grounded operational briefing layer.
- **OpenStreetMap Data (OSMnx / Overpass):** Genuine road network geometry, bridge tags, and healthcare facility locations for Kendrapara, Odisha.

*(Note: PreImpact uses only the technologies listed above. It does not use or claim external services like Earth Engine, BigQuery, or Vertex AI.)*

---

## 4. Data Provenance & Transparency

PreImpact enforces strictly honest provenance labeling across all endpoints, tests, and UI views:

| Category | Layer | Source & Verification | Modeled vs Real Status |
|---|---|---|---|
| **REAL** | **Road Network** | OpenStreetMap genuine download | Genuine network: 1,672 nodes, 4,115 edges in `REAL_OSM` mode |
| **REAL** | **Bridges** | OpenStreetMap `bridge=yes` tags | 126 independently verified OSM bridges detected |
| **REAL** | **Healthcare Facilities** | OpenStreetMap `amenity=hospital` | 5 verified hospital facilities with OSM IDs and coordinates |
| **MODELED** | **Cyclone Scenario** | IMD Archive Analogue (Cyclone Fani) | Modeled historical replay analogue (**not an operational forecast**) |
| **MODELED** | **Hazard Footprint** | Geometric track buffer & surge polygon | Core wind swath (45 km), gale swath (85 km), surge zone polygon |
| **MODELED** | **Bridge Unavailability** | Counterfactual edge removal | Hypothetical scenario simulation (**not structural failure prediction**) |
| **MODELED** | **Route Recalculation** | NetworkX Dijkstra algorithm | Shortest travel-time detour under speed-limit assumptions |
| **MODELED** | **Resilience Priority** | Formula: $(E \times D \times C)^{1/3}$ | Balanced score combining exposure, disruption, and criticality |
| **ESTIMATED** | **Shelters** | Fallback geographic coordinates | 4 cyclone shelters in coastal service corridor |
| **ESTIMATED** | **Population** | District census aggregate estimates | ~89,400 residents across Kendrapara coastal settlements |
| **EVIDENCE-GROUNDED** | **Operational Briefing** | Google Gemini 2.5 Flash | Grounded strictly on deterministic engine facts (deterministic fallback if offline) |

---

## 5. Methodology & Mathematical Formulation

1. **Hazard Exposure Score $E \in [0.0, 1.0]$:**
   $$E = \min\left(1.0,\; (\text{Distance Score} \times 0.50) + \text{Zone Bonus} + (\text{Highway Weight} \times 0.15)\right)$$
   - Distance score measures proximity to the cyclone track centerline and coastal landfall.
   - Zone bonuses: $+0.25$ inside storm surge inundation polygon, $+0.15$ inside 45 km core wind swath, $+0.08$ inside 85 km gale swath.

2. **Disruption Delta $\Delta t$:**
   $$\Delta t = t_{\text{scenario}} - t_{\text{baseline}}$$
   If no alternate path exists within the connected network, the route is flagged as `UNREACHABLE` (severed access).

3. **Resilience Priority Score $P \in [0.0, 1.0]$:**
   $$P = \left(\text{Exposure} \times \text{Disruption} \times \text{Criticality}\right)^{1/3}$$
   The geometric mean guarantees that an asset must have high hazard exposure, substantial travel-time delay, and downstream facility criticality to receive top priority.

---

## 6. Google Gemini Evidence-Grounded Briefing

Gemini 2.5 Flash synthesizes operational decision-support briefings from deterministic facts:
- **Strict Evidence Grounding:** Gemini receives ONLY structured, pre-computed facts from the engine (asset ID, baseline time, scenario time, delay delta, affected hospital/shelter counts, population).
- **Zero Hallucination Guardrails:** Gemini is forbidden from inventing facilities, altering travel times, or predicting structural collapse.
- **Operational Action Options:** Generates 5 pre-impact preparation options:
  1. Pre-position emergency ambulances and rescue personnel on the critical side of the bridge before landfall.
  2. Verify road surface and culvert drainage conditions along alternate detour corridors.
  3. Pre-stage emergency rations and medical supplies at community health centers.
  4. Establish real-time corridor monitoring and communication links at vulnerable crossings.
  5. Coordinate standby response teams between district headquarters and block officers.
- **Graceful Offline Degradation:** If `GEMINI_API_KEY` is omitted or API calls fail, PreImpact automatically provides a deterministic evidence template. The core resilience engine remains 100% operational.

---

## 7. Setup & Local Execution

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Clone Repository & Install Backend

```bash
git clone https://github.com/PhantomCipher13/preimpact.git
cd preimpact

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

```bash
# Copy example configuration
cp .env.example .env

# Edit .env and set your Gemini API key (optional):
# GEMINI_API_KEY=your_api_key_here
```
*(PreImpact works 100% offline with deterministic fallback templates if no API key is provided.)*

### 3. Start Backend API

```bash
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```
API documentation is available at `http://127.0.0.1:8000/docs`.

### 4. Start Frontend Dashboard

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` or `http://127.0.0.1:5173` in your browser.

---

## 8. Automated Testing

Run the full pytest suite (118 unit and integration tests):

```bash
python -m pytest tests/ -v
```

All 118 tests run fully offline and pass in ~3.8 seconds.

To test the frontend production build:

```bash
cd frontend
npm run build
```

---

## 9. Responsible AI & Ethical Boundaries

PreImpact was built adhering to strict institutional disaster-response ethics:
- **No Structural Collapse Predictions:** PreImpact models hypothetical unavailability, not physical bridge failure probability.
- **No Operational Forecasting Claims:** Cyclone scenarios are historical/modeled replay analogues for contingency planning, not live meteorological forecasts.
- **No Autonomous Emergency Orders:** The AI layer provides preparation options for human incident commanders; it cannot issue autonomous evacuation or road closure orders.
- **Transparent Provenance:** All data layers explicitly disclose whether they are Real OSM, Modeled, or Estimated.

---

## 10. Repository Structure

```text
preimpact/
├── backend/
│   ├── api/                  # FastAPI router endpoints & schemas
│   ├── data/                 # Cached OSM graph & POI datasets
│   └── engine/               # NetworkX routing, exposure, and Gemini modules
├── frontend/
│   ├── src/                  # React dashboard, Leaflet map, glassmorphism UI
│   ├── index.html            # Entry HTML
│   ├── package.json          # Node dependencies & build scripts
│   └── vite.config.js        # Vite build & proxy configuration
├── scripts/
│   ├── scan_secrets.py       # Standalone secret & credential scanner
│   └── verify_browser_e2e.py # Automated Selenium browser E2E test
├── tests/                    # 118 automated pytest unit & integration tests
├── .env.example              # Placeholder environment configuration
├── .gitignore                # Comprehensive Git exclusion rules
├── conftest.py               # Pytest fixtures and test setup
├── DEMO_SCRIPT.md            # Interactive walkthrough demo script
├── FINAL_TEST_REPORT.md      # Adversarial audit & test report
├── README.md                 # Complete project documentation
├── requirements.txt          # Python dependencies
├── run_simulation.py         # CLI simulation runner
├── STATUS.md                 # Project milestones & verification status
├── UI_REDESIGN_NOTES.md      # Light glassmorphism design system notes
└── walkthrough.md            # Technical walkthrough & architecture review
```

---

## 11. License

This project is licensed under the MIT License.
