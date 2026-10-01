// PreImpactMap.jsx — Leaflet map with cyclone track, hazard footprint, exposed bridges, and reroutes
import { useEffect, useRef } from 'react'

let L = null

export default function PreImpactMap({ demoData, selectedResult, onSelectResult, simulationPhase, simulationStep }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const layersRef = useRef([])

  useEffect(() => {
    import('leaflet').then((leaflet) => {
      L = leaflet.default

      delete L.Icon.Default.prototype._getIconUrl
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      })

      if (!mapInstanceRef.current && mapRef.current) {
        const map = L.map(mapRef.current, {
          center: [20.530, 86.600],
          zoom: 11,
          zoomControl: true,
        })

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors · PreImpact Decision Support',
          maxZoom: 18,
        }).addTo(map)

        mapInstanceRef.current = map
      }
    })

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [])

  // Re-draw layers when data or selectedResult changes
  useEffect(() => {
    if (!mapInstanceRef.current || !L || !demoData) return

    const map = mapInstanceRef.current

    // Clear previous layers
    layersRef.current.forEach(l => {
      try { map.removeLayer(l) } catch (_) {}
    })
    layersRef.current = []

    const nodePos = demoData.node_positions || {}
    const cyclone = demoData.cyclone_scenario || {}
    const activeResult = selectedResult || demoData.counterfactual_results?.[0]

    function addLayer(layer) {
      layer.addTo(map)
      layersRef.current.push(layer)
      return layer
    }

    // ── 1. Cyclone Hazard Swath & Footprint ────────────────────────────

    // A. Gale-force wind buffer (85 km radius circle around landfall)
    if (cyclone.landfall_lat && cyclone.landfall_lon) {
      addLayer(L.circle([cyclone.landfall_lat, cyclone.landfall_lon], {
        radius: (cyclone.gale_wind_radius_km || 85) * 1000,
        color: '#f97316',
        fillColor: '#f97316',
        fillOpacity: 0.05,
        weight: 1,
        dashArray: '6 6',
        interactive: false,
      }))

      // B. Core destructive wind swath (45 km radius circle around landfall)
      addLayer(L.circle([cyclone.landfall_lat, cyclone.landfall_lon], {
        radius: (cyclone.core_wind_radius_km || 45) * 1000,
        color: '#dc2626',
        fillColor: '#dc2626',
        fillOpacity: 0.10,
        weight: 1.5,
        interactive: false,
      }))
    }

    // C. Storm Surge Inundation Zone Polygon (Coastal Kendrapara strip)
    if (cyclone.surge_zone_polygon && cyclone.surge_zone_polygon.length >= 3) {
      addLayer(L.polygon(cyclone.surge_zone_polygon, {
        color: '#0284c7',
        fillColor: '#38bdf8',
        fillOpacity: 0.16,
        weight: 1.5,
        dashArray: '4 4',
      }).bindTooltip('🌊 Storm Surge Hazard Footprint (~3.5m peak surge)', { sticky: true }))
    }

    // ── 2. Cyclone Track Line & Waypoints ──────────────────────────────
    const waypoints = cyclone.track_waypoints || []
    if (waypoints.length >= 2) {
      const trackCoords = waypoints.map(w => [w.lat, w.lon])
      addLayer(L.polyline(trackCoords, {
        color: '#991b1b',
        weight: 3.5,
        opacity: 0.85,
        dashArray: '8 6',
      }).bindTooltip(`🌀 ${cyclone.name || 'Cyclone Scenario Track'} (Fani Replay Analogue)`, { sticky: true }))

      waypoints.forEach(w => {
        const wpMarker = L.circleMarker([w.lat, w.lon], {
          radius: w.hour === 0 ? 8 : 4.5,
          color: w.hour === 0 ? '#b91c1c' : '#7f1d1d',
          fillColor: w.hour === 0 ? '#ef4444' : '#fca5a5',
          fillOpacity: 0.9,
          weight: 2,
        })
        wpMarker.bindPopup(`
          <div class="map-popup">
            <b>🌀 Cyclone Track Waypoint: T${w.hour >= 0 ? '+' : ''}${w.hour}h</b><br>
            <b>Wind:</b> ${w.wind_kmh} km/h<br>
            <b>Stage:</b> ${w.stage}<br>
            <i>${cyclone.data_label || 'MODELED SCENARIO'}</i>
          </div>
        `)
        addLayer(wpMarker)
      })
    }

    // Landfall Eye Icon
    if (cyclone.landfall_lat && cyclone.landfall_lon) {
      const eyeIcon = L.divIcon({
        className: '',
        html: `<div class="cyclone-eye-marker" title="Landfall Point">🌀</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      })
      addLayer(L.marker([cyclone.landfall_lat, cyclone.landfall_lon], { icon: eyeIcon })
        .bindPopup(`
          <div class="map-popup">
            <b>🌀 Cyclone Landfall Point</b><br>
            <b>Location:</b> ${cyclone.landfall_point?.name || 'Kendrapara Coast'}<br>
            <b>Peak Wind:</b> ${cyclone.max_wind_kmh || 175} km/h (Gusts: ${cyclone.gust_wind_kmh || 205} km/h)<br>
            <b>Storm Surge:</b> ~${cyclone.storm_surge_m || 3.5}m<br>
            <b>Pressure:</b> ${cyclone.central_pressure_hpa || 937} hPa<br>
            <span class="popup-label">${cyclone.data_label || 'MODELED SCENARIO REPLAY'}</span>
          </div>
        `))
    }

    // ── 3. Active Counterfactual Routes ───────────────────────────────
    // Find the most disrupted or representative change for the active result
    let activeBaseline = null
    let activeScenario = null
    let activeChangeLabel = ''

    if (activeResult?.changes && activeResult.changes.length > 0) {
      // Find top change (prefer unreachable or max delta)
      const topCh = activeResult.changes.find(c => c.became_unreachable) || activeResult.changes[0]
      activeBaseline = topCh.baseline_path || topCh.baseline?.path_nodes
      activeScenario = topCh.scenario_path || topCh.scenario?.path_nodes
      activeChangeLabel = `${topCh.origin_label} → ${topCh.dest_label}`
    } else if (demoData.headline) {
      activeBaseline = demoData.headline.baseline_path
      activeScenario = demoData.headline.scenario_path
      activeChangeLabel = `${demoData.headline.origin_label} → ${demoData.headline.dest_label}`
    }

    // Determine simulation state: 'initial' | 'baseline' | 'severed' | 'rerouted' | 'completed'
    const currentPhase = simulationPhase || simulationStep || 'initial'
    const isBaselineOpen = currentPhase === 'initial' || currentPhase === 'baseline'
    const isSevered = currentPhase === 'severed'
    const isRerouted = currentPhase === 'rerouted'
    const isCompleted = currentPhase === 'completed'

    // Route 1: Baseline corridor
    // - In 'initial' or 'baseline': Vibrant solid blue corridor (normal open access)
    // - In 'severed': Red dashed interrupted line (access cut)
    // - In 'completed': Subtle underlying blue route to show the original baseline comparison
    if (activeBaseline && activeBaseline.length >= 2) {
      const coords = activeBaseline
        .filter(n => nodePos[n])
        .map(n => [nodePos[n].lat, nodePos[n].lon])
      if (coords.length >= 2) {
        if (isSevered) {
          addLayer(L.polyline(coords, {
            color: '#dc2626',
            weight: 6,
            opacity: 0.85,
            dashArray: '8 6',
          }).bindTooltip(`⛔ DIRECT ROUTE SEVERED: ${activeChangeLabel} (Bridge Unavailable)`, { sticky: true }))
        } else if (isBaselineOpen) {
          addLayer(L.polyline(coords, {
            color: '#1d4ed8',
            weight: 6,
            opacity: 0.95,
          }).bindTooltip(`Normal Baseline Access: ${activeChangeLabel} (Bridge Available)`, { sticky: true }))
        } else if (isCompleted) {
          addLayer(L.polyline(coords, {
            color: '#3b82f6',
            weight: 4,
            opacity: 0.45,
          }).bindTooltip(`Original Baseline Route: ${activeChangeLabel} (Bridge Open)`, { sticky: true }))
        }
      }
    }

    // Route 2: Alternate detour corridor
    // - In 'initial', 'baseline', 'severed': Hidden (do NOT show detour before reroute completes)
    // - In 'rerouted' or 'completed': Prominent bold orange dashed detour (#ea580c)
    const showAlternate = isRerouted || isCompleted

    if (showAlternate && activeScenario && activeScenario.length >= 2) {
      const coords = activeScenario
        .filter(n => nodePos[n])
        .map(n => [nodePos[n].lat, nodePos[n].lon])
      if (coords.length >= 2) {
        addLayer(L.polyline(coords, {
          color: '#ea580c',
          weight: isRerouted ? 7 : 6,
          opacity: 0.95,
          dashArray: '12 6',
        }).bindTooltip(`Counterfactual Detour: ${activeChangeLabel} (Bridge Unavailable)`, { sticky: true }))
      }
    }

    // ── 4. Exposed Bridge Assets ──────────────────────────────────────
    const allBridges = demoData.bridges || []
    const selectedBridgeId = activeResult?.asset_id

    allBridges.forEach(b => {
      if (!b.midpoint_lat || !b.midpoint_lon) return
      const isSelected = b.asset_id === selectedBridgeId
      const exp = b.exposure || {}
      const expScore = exp.exposure_score ?? 0.5
      const expLabel = exp.exposure_label ?? 'Exposed'

      if (isSelected) {
        // Selected bridge marker
        // Before simulation ('initial' or 'baseline'): Bridge is AVAILABLE / OPEN (marker: 🌉, pulse-open)
        // During 'severed': Red flashing severed marker ✖ (sever-flash)
        // During 'rerouted' or 'completed': Red unavailable marker ✖ (pulse-selected)
        const isBridgeAvailable = isBaselineOpen
        const iconHtml = isBridgeAvailable
          ? `<div class="bridge-marker pulse-open" title="Bridge Available (Baseline Open)">🌉</div>`
          : `<div class="bridge-marker pulse-selected ${isSevered ? 'sever-flash' : ''}" title="Selected Counterfactual Asset">✖</div>`

        const selectedIcon = L.divIcon({
          className: '',
          html: iconHtml,
          iconSize: [36, 36],
          iconAnchor: [18, 18],
        })
        const marker = L.marker([b.midpoint_lat, b.midpoint_lon], { icon: selectedIcon, zIndexOffset: 1000 })
        marker.bindPopup(`
          <div class="map-popup">
            <span class="${isBridgeAvailable ? 'popup-tag-safe' : 'popup-tag-danger'}">
              ${isBridgeAvailable ? '✓ BASELINE ACCESS — BRIDGE AVAILABLE' : '⚠ SELECTED COUNTERFACTUAL ASSET'}
            </span>
            <div style="font-size:13px;font-weight:700;margin:4px 0;">${b.asset_id}: ${b.name}</div>
            <b>Highway:</b> ${b.highway_type} (${Math.round(b.length_m || 0)}m)<br>
            <b>Hazard Exposure:</b> ${expScore.toFixed(3)} (${expLabel})<br>
            <b>Dist. to Track:</b> ${exp.distance_from_track_km ?? '?'} km<br>
            <b>Surge Zone:</b> ${exp.in_surge_zone ? 'YES' : 'NO'}<br>
            <div style="margin-top:6px;font-size:10px;color:${isBridgeAvailable ? '#15803d' : '#fca5a5'};">
              ${isBridgeAvailable
                ? 'Bridge is accessible under normal baseline transit.'
                : 'Simulating hypothetical unavailability during cyclone.'}
            </div>
          </div>
        `)
        addLayer(marker)
      } else {
        // Other candidate / exposed bridges (clickable dots color-coded by hazard exposure)
        const dotColor = expScore >= 0.75 ? '#dc2626' : expScore >= 0.55 ? '#ea580c' : expScore >= 0.35 ? '#ca8a04' : '#16a34a'
        const marker = L.circleMarker([b.midpoint_lat, b.midpoint_lon], {
          radius: 6.5,
          color: '#ffffff',
          fillColor: dotColor,
          fillOpacity: 0.9,
          weight: 1.5,
        })
        marker.bindPopup(`
          <div class="map-popup">
            <b>${b.asset_id}: ${b.name}</b><br>
            <b>Exposure:</b> ${expScore.toFixed(3)} (${expLabel})<br>
            <b>Highway:</b> ${b.highway_type}<br>
            <div style="margin-top:8px;">
              <button id="btn-select-${b.asset_id}" style="background:#1e3a5f;color:#93c5fd;border:1px solid #3b82f6;padding:3px 8px;font-size:10px;border-radius:3px;cursor:pointer;">
                Simulate Bridge Unavailability →
              </button>
            </div>
          </div>
        `)
        marker.on('popupopen', () => {
          const btn = document.getElementById(`btn-select-${b.asset_id}`)
          if (btn && onSelectResult) {
            btn.onclick = () => {
              const cf = demoData.counterfactual_results?.find(r => r.asset_id === b.asset_id)
              if (cf) onSelectResult(cf)
            }
          }
        })
        marker.on('click', () => {
          const cf = demoData.counterfactual_results?.find(r => r.asset_id === b.asset_id)
          if (cf && onSelectResult) onSelectResult(cf)
        })
        addLayer(marker)
      }
    })

    // ── 5. Hospitals (red cross icon) ─────────────────────────────────
    demoData.hospitals?.forEach(h => {
      const nid = h.nearest_node ?? h.node_id
      const pos = (nid !== undefined ? nodePos[nid] : null) || (h.original_lat ? { lat: h.original_lat, lon: h.original_lon } : null)
      if (!pos) return
      const icon = L.divIcon({
        className: '',
        html: `<div class="hosp-marker">🏥</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      })
      const name = h.poi_name || h.name || 'Hospital'
      const osmIdStr = h.osm_id ? `<br><b>OSM ID:</b> <code>${h.osm_id}</code>` : ''
      const coordStr = `<br><b>Coords:</b> ${pos.lat.toFixed(4)}, ${pos.lon.toFixed(4)}`
      const sourceStr = h.osm_source === 'REAL'
        ? `<br><span style="color:#86efac;font-weight:bold;">✓ REAL OpenStreetMap Data</span>`
        : `<br><span style="color:#fed7aa;">~ Estimated Location</span>`

      addLayer(L.marker([pos.lat, pos.lon], { icon })
        .bindPopup(`<b>🏥 ${name}</b>${sourceStr}${osmIdStr}${coordStr}`))
    })

    // ── 6. Shelters (green home icon) ────────────────────────────────
    demoData.shelters?.forEach(s => {
      const nid = s.nearest_node ?? s.node_id
      const pos = (nid !== undefined ? nodePos[nid] : null) || (s.original_lat ? { lat: s.original_lat, lon: s.original_lon } : null)
      if (!pos) return
      const icon = L.divIcon({
        className: '',
        html: `<div class="shelter-marker">🏠</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      })
      const name = s.poi_name || s.name || 'Shelter'
      const sourceStr = `<br><span style="color:#fed7aa;">~ ESTIMATED / FALLBACK Location</span>`
      const coordStr = `<br><b>Coords:</b> ${pos.lat.toFixed(4)}, ${pos.lon.toFixed(4)}`

      addLayer(L.marker([pos.lat, pos.lon], { icon })
        .bindPopup(`<b>🏠 ${name}</b>${sourceStr}${coordStr}`))
    })

    // ── 7. Settlements (yellow circles) ──────────────────────────────
    demoData.settlements?.forEach(s => {
      const nid = s.nearest_node ?? s.node_id
      const pos = (nid !== undefined ? nodePos[nid] : null) || (s.original_lat ? { lat: s.original_lat, lon: s.original_lon } : null)
      if (!pos) return
      const name = s.poi_name || s.name || 'Settlement'
      const popStr = s.population_estimate ? `~${s.population_estimate.toLocaleString()}` : 'N/A'
      addLayer(L.circleMarker([pos.lat, pos.lon], {
        radius: 7,
        fillColor: '#FFD600',
        color: '#1e293b',
        weight: 1.5,
        fillOpacity: 0.85,
      }).bindPopup(`
        <b>${name}</b><br>
        Est. population: ${popStr}<br>
        <i style="color:#94a3b8;">${s.data_label || 'ESTIMATED / MODELED — not census microdata'}</i>
      `))
    })

    // ── 8. Map Legend (Compact & Collapsible) ────────────────────────
    if (!mapInstanceRef.current._legendAdded) {
      const legend = L.control({ position: 'bottomleft' })
      legend.onAdd = () => {
        const div = L.DomUtil.create('div', 'map-legend legend-collapsed')
        div.innerHTML = `
          <div class="legend-header" title="Toggle Legend">
            <span class="legend-title">🗺 MAP LEGEND</span>
            <span class="legend-toggle-icon">▾</span>
          </div>
          <div class="legend-content">
            <div class="legend-row"><span class="legend-line blue-line"></span> Baseline Route (normal access)</div>
            <div class="legend-row"><span class="legend-line orange-line dashed"></span> Alternate Route (bridge unavailable)</div>
            <div class="legend-row"><span class="legend-line track-line"></span> Cyclone Replay Track (IMD Analogue)</div>
            <div class="legend-row"><span class="legend-zone-swath"></span> Core Wind Swath (≥150 km/h)</div>
            <div class="legend-row"><span class="legend-zone-surge"></span> Storm Surge Footprint (~3.5m)</div>
            <div class="legend-row"><span class="legend-icon">✖</span> Selected Bridge (removed in scenario)</div>
            <div class="legend-row"><span class="legend-dot-exp dot-high"></span> Exposed Bridge (High/Extreme)</div>
            <div class="legend-row"><span class="legend-dot-exp dot-med"></span> Exposed Bridge (Medium/Low)</div>
            <div class="legend-row"><span class="legend-icon">🏥</span> Hospital · <span class="legend-icon">🏠</span> Shelter</div>
            <div class="legend-note">MODELED SCENARIO — not an operational forecast</div>
          </div>
        `
        L.DomEvent.disableClickPropagation(div)
        const header = div.querySelector('.legend-header')
        if (header) {
          header.addEventListener('click', (e) => {
            e.stopPropagation()
            div.classList.toggle('legend-collapsed')
          })
        }
        return div
      }
      legend.addTo(map)
      mapInstanceRef.current._legendAdded = true
    }

  }, [demoData, selectedResult, simulationPhase, simulationStep])

  return (
    <div className="map-container">
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    </div>
  )
}
