# PREIMPACT — UI Visual Redesign & Decongestion Notes: Light Glassmorphism Architecture

**Date:** 2026-09-28  
**Scope:** Visual layout decongestion and conversion to a light/soft glassmorphism design system (zero alterations to application logic, backend calculations, data provenance, API routes, or copy)  
**Status:** Complete & Verified (`npm run build` passing in 194ms, 118/118 tests passing)

---

## 1. Executive Summary & Layout Hierarchy Transformation

The PreImpact dashboard visual layer was overhauled to address interface congestion and replace dark "AI-style" neon glows with a **professional, light, soft frosted glassmorphism aesthetic** suitable for institutional emergency management.

### Information Architecture & Layout Decongestion
Previously, simultaneous sidebars, stacked top ribbons, and oversized permanent boxes squeezed the map into a cramped ~45% center slot with excessive vertical scrolling (>1500px in the right column).

The layout hierarchy was restructured into a clear 4-tier model:
1. **HERO (~68% width):** Interactive Map Canvas with full visual prominence.
2. **PRIMARY INFORMATION (~32% width):** Selected Asset Disruption Card & Gemini Evidence Brief pinned cleanly on the right column without stacked clutter underneath.
3. **SECONDARY INFORMATION:** Cyclone Scenario awareness summarized in a single compact, horizontal frosted-glass ribbon beneath the header.
4. **SUPPORTING INFORMATION:** Network graph metrics, facility POIs, asset ranking tables, and data methodology organized into floating frosted glass drawers and overlay modals accessible on demand.

```
┌────────────────────────────────────────────────────────────────────────┐
│ Header: PREIMPACT · Mode Switcher · Counterfactual Sim Trigger · Tabs  │
├────────────────────────────────────────────────────────────────────────┤
│ Cyclone Scenario Ribbon: Fani Analogue · Max Wind · Surge · Progression│
├───────────────────────────────────────────────┬────────────────────────┤
│ HERO MAP CANVAS (~68% width)                  │ PRIMARY ASSET DOSSIER  │
│                                               │ (~32% width)           │
│ [🌪 Cyclone Scenario ▾]  [🌐 Graph & POIs ▾]  │ • Asset ID & Name      │
│                                               │ • Hazard Exposure Level│
│ • Full Leaflet Map & Hazard Footprint         │ • 10-Second Flow:      │
│ • Floating On-Demand Glass Drawers            │   16.7m → 26.3m (+9.5m)│
│ • Dynamic Simulation HUD                      │ • Consequential Impact │
│ • Collapsible Frosted Legend (Bottom-Left)    │ • Priority Score (0-1) │
│                                               │ • Gemini Evidence Brief│
└───────────────────────────────────────────────┴────────────────────────┘
```

---

## 2. Light & Soft Glassmorphism Design System

### A. Atmospheric Canvas & Frosted Glass Surfaces
- **Light Atmosphere:** Replaced heavy opaque black backgrounds with an atmospheric light slate canvas (`#f4f6fa` with gradient `linear-gradient(135deg, #f8fafc 0%, #eef2f7 50%, #e2e8f0 100%)`).
- **Frosted Translucency:** Applied soft translucent white surfaces with multi-stop backdrop blurring:
  - Base Panels & Header: `rgba(255, 255, 255, 0.75–0.82)` with `backdrop-filter: blur(20px) saturate(160%)`
  - Floating Drawers & HUD: `rgba(255, 255, 255, 0.88)` with `backdrop-filter: blur(18px) saturate(150%)`
  - Cards & Metric Tiles: `rgba(255, 255, 255, 0.62–0.68)` with `backdrop-filter: blur(14px)`
- **Delicate Glass Borders:** Thin, subtle translucent borders (`1px solid rgba(226, 232, 240, 0.7)` and `rgba(255, 255, 255, 0.75)`) replacing heavy dark borders.
- **Elevation & Inner Highlights:** Subtle top-edge light highlights (`box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.9)`) paired with soft, diffuse ambient drop shadows (`0 6px 24px -2px rgba(15, 23, 42, 0.07)`).

### B. High-Contrast Readable Slate Typography
- **Primary Typography:** Maintained clean, authoritative `Inter` across all headings, navigation items, scenario cards, and body text.
- **Numerical & Tabular Monospace:** Retained `JetBrains Mono` strictly for asset IDs (`B006`), travel times (`16.7 min → 26.3 min`), percentages (`+57%`), and priority indices (`0.391`).
- **Contrast & Legibility:** Dark slate typography (`#0f172a` for primary headings, `#334155` for body, `#64748b` for secondary labels) delivers WCAG AAA contrast against translucent white frosted glass backgrounds.

### C. Restrained Semantic Color Palette
- **Critical / Route Severed:** Authoritative emergency red (`#dc2626`, badge text `#b91c1c`, glass tint `rgba(239, 68, 68, 0.08)`).
- **High Exposure:** Deep orange (`#ea580c`, badge text `#c2410c`, glass tint `rgba(249, 115, 22, 0.08)`).
- **Medium Exposure:** Deep amber (`#ca8a04`, badge text `#854d0e`, glass tint `rgba(234, 179, 8, 0.10)`).
- **Safe / Low:** Forestry green (`#16a34a`, badge text `#15803d`, glass tint `rgba(34, 197, 94, 0.08)`).
- **Baseline Route / Blue Line:** Steel blue (`#2563eb`, glass tint `rgba(37, 99, 235, 0.08)`).
- **Eliminated AI Tropes:** Completely removed neon purple glows, pulsing drop-shadow rings, pink/cyan gradient fills, and arcade particle effects.

---

## 3. Specific Component Improvements

### 1. Cyclone Summary Banner (`CycloneSummaryBanner.jsx`)
- Streamlined from two heavy stacked rows into a compact, single-line frosted-glass ribbon beneath the toolbar.
- Preserves all situational facts:
  - Cyclone scenario name: *Cyclone Fani Replay Analogue (Very Severe Cyclonic Storm)*
  - Meteorological metrics: Max Wind `175 km/h` · Storm Surge `3.5 m`
  - Deterministic pipeline progression: `126 Total Bridges → 126 Exposed → 12 Analyzed`
  - Geographic facility counts: `5 Hospitals | 9 Communities | ~89,400 Population`

### 2. Map Hero Experience & Collapsible Legend (`PreImpactMap.jsx`)
- **Expanded Real Estate:** Map expanded from ~45% to ~68% width of the desktop viewport.
- **Floating Quick Controls:** Two lightweight frosted-glass pills (`🌪 Cyclone Scenario ▾` and `🌐 Graph & POIs ▾`) float on the top-left of the map, allowing users to inspect cyclone details or facility counts in a floating drawer without leaving the map.
- **Collapsible Map Legend:** Converted from an oversized permanent box into a compact, collapsible frosted pill with click-to-expand behavior (`.map-legend.legend-collapsed`) and `L.DomEvent.disableClickPropagation` to prevent map drag conflicts.

### 3. Isolated Primary Disruption Dossier (`DisruptionCard.jsx`)
- Removed `MethodologyNote` and ancillary panels from the bottom of the right column, eliminating the 1500px vertical scrollbar.
- The 10-second disruption story is immediately visible above the fold on initial load:
  - **Asset Header:** `BRIDGE B006 | DR15` with `EXTREME (0.965)` hazard exposure badge.
  - **IF UNAVAILABLE Banner:** Bold callout indicating hypothetical cyclone disruption.
  - **Time Flow Comparison:** Baseline `16.7 min` (Bridge Open) $\rightarrow$ Counterfactual `26.3 min` (Alternate Route).
  - **Delta Callout:** `+9.5 min emergency travel delay (+57% transit time)`.
  - **Impact Grid:** 3 Hospitals Affected, 1 Shelter Affected, ~89,400 Estimated Population.
  - **Resilience Priority Score:** `0.391` (Medium) with geometric component bars ($E=0.965, D=0.144, C=0.75$).
  - **Gemini Briefing:** Integrated structured intelligence briefing with tabs A, B, C, D.

### 4. Focused Supporting Drawers & Modals
- **Asset Priorities Tab (`CRITICAL ASSET PRIORITIES`):** Opens a focused full-height overlay modal directly over the map canvas, allowing users to compare the 12 analyzed bridges, sort by priority, and click any bridge to instantly focus it on the map and return (`← Return to Map`).
- **Data & Methodology Tab (`DATA & METHODOLOGY`):** Opens a dedicated provenance drawer showing verified OSM facility sources, synthetic fallback labels, and model assumptions.

---

## 4. Strict Confirmation of Verification & Constraints

- **Text & Copy Integrity:** 100% of headlines, labels, metric names, button texts, Gemini explanations, and provenance disclaimers are preserved verbatim.
- **Algorithm & Logic Invariance:** Dijkstra routing, NetworkX graph immutability, geometric mean calculation, and API endpoints remain untouched.
- **Automated Verification:**
  - `npm run build`: Succeeded in 194ms with 0 errors.
  - `pytest tests/ -v`: 118/118 tests passing in 5.37s.
