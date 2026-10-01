import { useState, useEffect } from 'react'
import Header from './components/Header'
import ScenarioPanel from './components/ScenarioPanel'
import PreImpactMap from './components/PreImpactMap'
import DisruptionCard from './components/DisruptionCard'
import MethodologyNote from './components/MethodologyNote'
import AssetRanking from './components/AssetRanking'
import DataQualityPanel from './components/DataQualityPanel'
import CycloneSummaryBanner from './components/CycloneSummaryBanner'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function App() {
  const [demoData, setDemoData]     = useState(null)
  const [realData, setRealData]     = useState(null)
  const [activeMode, setActiveMode] = useState('real')   // 'real' | 'demo'
  const [loading, setLoading]       = useState(true)
  const [realLoading, setRealLoading] = useState(false)
  const [error, setError]           = useState(null)
  const [selectedResult, setSelectedResult] = useState(null)
  const [activeTab, setActiveTab]   = useState('map')    // 'map' | 'ranking' | 'data'
  const [simulationPhase, setSimulationPhase] = useState('initial') // 'initial' | 'baseline' | 'severed' | 'rerouted' | 'completed'
  const [activeOverlay, setActiveOverlay]   = useState(null) // null | 'scenario' | 'network'

  function runCounterfactualSimulation() {
    setActiveTab('map')
    const topResult = (selectedResult?.changes?.length > 0)
      ? selectedResult
      : (activeData?.counterfactual_results?.find(r => r.asset_id === 'B006') || activeData?.counterfactual_results?.[0])
    if (!topResult) return

    setSelectedResult(topResult)
    setSimulationPhase('baseline')

    setTimeout(() => {
      setSimulationPhase('severed')
    }, 1400)

    setTimeout(() => {
      setSimulationPhase('rerouted')
    }, 2800)

    setTimeout(() => {
      setSimulationPhase('completed')
    }, 7000)
  }

  useEffect(() => {
    loadInitialData()
  }, [])

  async function loadInitialData() {
    setLoading(true)
    setError(null)
    try {
      setRealLoading(true)
      const res = await fetch(`${API_BASE}/api/real`)
      if (!res.ok) throw new Error(`Real API status: ${res.status}`)
      const data = await res.json()
      setRealData(data)
      setActiveMode('real')
      if (data.counterfactual_results?.length > 0) {
        const b006 = data.counterfactual_results.find(r => r.asset_id === 'B006')
        setSelectedResult(b006 || data.counterfactual_results[0])
      }
      setSimulationPhase('initial')
    } catch (err) {
      console.warn('Real OSM data unavailable on startup, falling back to demo mode:', err)
      await fetchDemoData(true)
    } finally {
      setRealLoading(false)
      setLoading(false)
    }
  }

  async function fetchDemoData(isFallback = false) {
    setLoading(true)
    if (!isFallback) setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/demo`)
      if (!res.ok) throw new Error(`API error: ${res.status}`)
      const data = await res.json()
      setDemoData(data)
      setActiveMode('demo')
      if (data.counterfactual_results?.length > 0) {
        setSelectedResult(data.counterfactual_results[0])
      }
      if (isFallback) {
        setError('Real OSM endpoint unavailable — running in DEMO_FALLBACK mode')
      }
      setSimulationPhase('initial')
    } catch (err) {
      console.error('API fetch failed, using embedded fallback:', err)
      const fallback = buildFallbackData()
      setDemoData(fallback)
      setActiveMode('demo')
      setSelectedResult(fallback.counterfactual_results[0])
      setError('Backend unreachable — displaying embedded DEMO_FALLBACK data')
      setSimulationPhase('initial')
    } finally {
      setLoading(false)
    }
  }

  async function switchToRealMode() {
    if (realData?.counterfactual_results?.length > 0) {
      setActiveMode('real')
      const b006 = realData.counterfactual_results.find(r => r.asset_id === 'B006')
      setSelectedResult(b006 || realData.counterfactual_results[0])
      setSimulationPhase('initial')
    } else {
      await fetchRealData()
    }
  }

  function switchToDemoMode() {
    setActiveMode('demo')
    if (demoData?.counterfactual_results?.length > 0) {
      setSelectedResult(demoData.counterfactual_results[0])
    } else {
      fetchDemoData()
    }
    setSimulationPhase('initial')
  }

  async function fetchRealData() {
    setRealLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/real`)
      if (!res.ok) throw new Error(`Real API error: ${res.status}`)
      const data = await res.json()
      setRealData(data)
      setActiveMode('real')
      if (data.counterfactual_results?.length > 0) {
        const b006 = data.counterfactual_results.find(r => r.asset_id === 'B006')
        setSelectedResult(b006 || data.counterfactual_results[0])
      }
      setSimulationPhase('initial')
    } catch (err) {
      setError(`Real data unavailable: ${err.message}. Using demo mode.`)
    } finally {
      setRealLoading(false)
    }
  }

  const activeData = activeMode === 'real' && realData ? realData : demoData

  function buildFallbackData() {
    return {
      mode: 'DEMO',
      data_label: 'DEMO SCENARIO — All values are modelled estimates',
      graph_source: 'demo',
      node_count: 12, edge_count: 24, bridges_detected: 1,
      cyclone_scenario: {
        name: 'Scenario: Very Severe Cyclone (VSCS)',
        description: 'Modelled VSCS-class cyclone making landfall near Kendrapara coast.',
        max_wind_kmh: 175, storm_surge_m: 3.5,
        source: 'MODELLED SCENARIO', data_label: 'DEMO'
      },
      data_labels: {
        road_network: 'DEMO — synthetic graph',
        bridges: 'DEMO — synthetic bridge',
        hospitals: 'ESTIMATED — fallback coordinates',
        shelters: 'ESTIMATED — fallback coordinates',
        population: 'ESTIMATED — not census data',
        travel_time: 'MODELLED — length / speed assumption',
        hazard_exposure: 'MODELLED — VSCS scenario analogue',
        priority_score: 'MODELLED — Exposure × Disruption × Criticality',
      },
      bridges: [{
        asset_id: 'B001', name: 'Bridge_B1',
        midpoint_lat: 20.565, midpoint_lon: 86.5575,
        highway_type: 'primary', length_m: 600,
        exposure_level: 'High',
        exposure: { exposure_label: 'High', exposure_score: 0.85, data_label: 'MODELLED SCENARIO' }
      }],
      settlements: [
        { node_id: 1, name: 'Rajnagar Village',   population_estimate: 4200,  data_label: 'ESTIMATED' },
        { node_id: 2, name: 'Mahakalapada Town',  population_estimate: 8700,  data_label: 'ESTIMATED' },
        { node_id: 3, name: 'Satabhaya Village',  population_estimate: 2100,  data_label: 'ESTIMATED' },
        { node_id: 9, name: 'Kansarpal Village',  population_estimate: 1800,  data_label: 'ESTIMATED' },
      ],
      hospitals: [{ node_id: 8, name: 'Kendrapara District Hospital' }],
      shelters:  [{ node_id: 10, name: 'Cyclone Shelter CS-07' }],
      top_priority_bridge: 'B001',
      headline: {
        origin_label: 'Rajnagar Village', dest_label: 'Cyclone Shelter CS-07',
        baseline_travel_time_min: 10.5, scenario_travel_time_min: 27.84,
        disruption_delta_min: 17.34, became_unreachable: false,
        baseline_path: [1,4,5,6,7,10], scenario_path: [1,4,11,12,8,7,10],
      },
      node_positions: {
        1:{lat:20.570,lon:86.510,label:'Rajnagar Village'},
        2:{lat:20.565,lon:86.520,label:'Mahakalapada Town'},
        3:{lat:20.580,lon:86.500,label:'Satabhaya Village'},
        4:{lat:20.568,lon:86.530,label:'Junction_1'},
        5:{lat:20.565,lon:86.555,label:'Junction_2'},
        6:{lat:20.563,lon:86.560,label:'Bridge_B1'},
        7:{lat:20.560,lon:86.565,label:'Junction_3'},
        8:{lat:20.555,lon:86.580,label:'Kendrapara Hospital'},
        9:{lat:20.590,lon:86.575,label:'Kansarpal Village'},
        10:{lat:20.545,lon:86.545,label:'Cyclone Shelter CS-07'},
        11:{lat:20.600,lon:86.540,label:'Junction_North'},
        12:{lat:20.595,lon:86.565,label:'Junction_NE'},
      },
      counterfactual_results: [{
        asset_id:'B001', asset_name:'Bridge_B1',
        max_disruption_delta_min:17.3, mean_disruption_delta_min:12.1,
        unreachable_count:0, affected_pairs_count:4,
        hospitals_affected:[8], shelters_affected:[10],
        edges_removed:4, source:'demo',
        priority:{raw_score:0.452,label:'High',components:{exposure:0.85,disruption:0.144,criticality:0.75}},
        population_impact:{affected_population:15000,affected_settlements:3,total_population:16800,threshold_min:15.0},
        exposure:{exposure_label:'High',exposure_score:0.85,distance_from_landfall_km:14.2,
          in_surge_zone:true,data_label:'MODELLED SCENARIO'},
        changes:[
          {origin_label:'Rajnagar Village',dest_label:'Cyclone Shelter CS-07',
           baseline_travel_time_min:10.5,scenario_travel_time_min:27.84,disruption_delta_min:17.34,
           became_unreachable:false,baseline_path:[1,4,5,6,7,10],scenario_path:[1,4,11,12,8,7,10]},
          {origin_label:'Mahakalapada Town',dest_label:'Kendrapara District Hospital',
           baseline_travel_time_min:9.8,scenario_travel_time_min:24.3,disruption_delta_min:14.5,
           became_unreachable:false,baseline_path:[2,4,5,6,7,8],scenario_path:[2,4,11,12,8]},
        ]
      }]
    }
  }

  if (loading) return (
    <div className="loading-screen">
      <div className="loading-content">
        <div className="loading-spinner"></div>
        <h2>PREIMPACT</h2>
        <p>Loading counterfactual simulation engine…</p>
      </div>
    </div>
  )

  const result = selectedResult || activeData?.counterfactual_results?.[0]

  return (
    <div className="app-layout">
      <Header />

      {/* Mode switcher toolbar */}
      <div className="toolbar">
        <div className="toolbar-left">
          <button
            className={`mode-btn ${activeMode === 'demo' ? 'active' : ''}`}
            onClick={switchToDemoMode}
          >
            DEMO MODE
          </button>
          <button
            className={`mode-btn ${activeMode === 'real' ? 'active' : ''}`}
            onClick={switchToRealMode}
            disabled={realLoading}
          >
            {realLoading ? 'LOADING…' : 'REAL DATA'}
          </button>
          <div className="data-mode-badge">
            {activeData?.mode === 'REAL_OSM'
              ? <span className="badge-real">✓ REAL OSM DATA</span>
              : activeData?.mode === 'PARTIAL_REAL_DATA'
                ? <span className="badge-partial">⚠ PARTIAL REAL DATA — road network modelled</span>
                : activeData?.mode === 'DEMO_FALLBACK'
                  ? <span className="badge-fallback">⚠ DEMO FALLBACK — synthetic data only</span>
                  : <span className="badge-demo">DEMO SCENARIO</span>
            }
          </div>
        </div>
        <div className="toolbar-center">
          <button
            className={`demo-sim-btn ${['baseline', 'severed', 'rerouted'].includes(simulationPhase) ? 'simulating' : ''}`}
            onClick={runCounterfactualSimulation}
            disabled={['baseline', 'severed', 'rerouted'].includes(simulationPhase)}
            title="Automated walkthrough: baseline route → bridge unavailable → counterfactual reroute → AI brief"
          >
            {['baseline', 'severed', 'rerouted'].includes(simulationPhase) ? 'SIMULATING COUNTERFACTUAL…' : '▶ RUN COUNTERFACTUAL SIMULATION'}
          </button>
        </div>
        <div className="toolbar-right">
          <button
            className={`tab-btn ${activeTab === 'map' ? 'active' : ''}`}
            onClick={() => setActiveTab('map')}
          >
            MAP
          </button>
          <button
            className={`tab-btn ${activeTab === 'ranking' ? 'active' : ''}`}
            onClick={() => setActiveTab('ranking')}
          >
            CRITICAL ASSET PRIORITIES
          </button>
          <button
            className={`tab-btn ${activeTab === 'data' ? 'active' : ''}`}
            onClick={() => setActiveTab(activeTab === 'data' ? 'map' : 'data')}
          >
            DATA & METHODOLOGY
          </button>
        </div>
      </div>

      {error && <div className="api-warning">⚠ {error}</div>}

      {/* Top situational awareness ribbon */}
      <CycloneSummaryBanner
        summary={activeData?.summary}
        cyclone={activeData?.cyclone_scenario}
        mode={activeData?.mode}
      />

      <div className="main-content">
        {/* Left & Center: Large Hero Map Area (~68%) */}
        <div className="center-area">
          {/* Floating Map Controls for Scenario & POI Details */}
          <div className="map-floating-bar">
            <button
              className={`map-floating-pill ${activeOverlay === 'scenario' ? 'active' : ''}`}
              onClick={() => setActiveOverlay(activeOverlay === 'scenario' ? null : 'scenario')}
            >
              🌪 Cyclone Scenario ▾
            </button>
            <button
              className={`map-floating-pill ${activeOverlay === 'network' ? 'active' : ''}`}
              onClick={() => setActiveOverlay(activeOverlay === 'network' ? null : 'network')}
            >
              🌐 Graph & POIs ({activeData?.bridges_detected ?? 126} Bridges · {activeData?.hospitals?.length ?? 5} Hosp) ▾
            </button>
          </div>

          {/* Floating Drawer 1: Cyclone Scenario */}
          {activeOverlay === 'scenario' && (
            <div className="floating-glass-drawer">
              <div className="fgd-header">
                <span className="fgd-title">🌪 CYCLONE SCENARIO DETAILS</span>
                <button className="fgd-close" onClick={() => setActiveOverlay(null)}>✕</button>
              </div>
              <div className="fgd-body">
                <div className="cyclone-name">{activeData?.cyclone_scenario?.name}</div>
                <div className="cyclone-stats">
                  <div className="stat-item">
                    <span className="stat-value">{activeData?.cyclone_scenario?.max_wind_kmh}</span>
                    <span className="stat-unit">km/h</span>
                    <span className="stat-label">Max Wind</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-value">{activeData?.cyclone_scenario?.storm_surge_m}</span>
                    <span className="stat-unit">m</span>
                    <span className="stat-label">Storm Surge</span>
                  </div>
                </div>
                <div className="data-provenance">{activeData?.cyclone_scenario?.source}</div>
              </div>
            </div>
          )}

          {/* Floating Drawer 2: Network & Facilities */}
          {activeOverlay === 'network' && (
            <div className="floating-glass-drawer">
              <div className="fgd-header">
                <span className="fgd-title">🌐 NETWORK & POI DETAILS</span>
                <button className="fgd-close" onClick={() => setActiveOverlay(null)}>✕</button>
              </div>
              <div className="fgd-body">
                <div className="graph-stats">
                  <div className="stat-row">
                    <span>Mode</span>
                    {activeData?.mode === 'REAL_OSM' ? (
                      <span className="badge-real">✓ REAL OSM</span>
                    ) : (
                      <span className="badge-partial">⚠ PARTIAL REAL</span>
                    )}
                  </div>
                  <div className="stat-row">
                    <span>Road network</span>
                    <span className="highlight-sm">{activeData?.mode === 'REAL_OSM' ? 'OpenStreetMap' : 'Modeled fallback'}</span>
                  </div>
                  <div className="stat-row">
                    <span>Nodes / Edges</span>
                    <span>{activeData?.node_count} / {activeData?.edge_count}</span>
                  </div>
                  <div className="stat-row">
                    <span>Bridges detected</span>
                    <span className="highlight">{activeData?.bridges_detected}</span>
                  </div>
                </div>
                <div className="section-label" style={{ marginTop: '10px' }}>HOSPITALS & SHELTERS</div>
                {activeData?.hospitals?.slice(0, 4).map((h, i) => (
                  <div key={i} className="facility-row">
                    <span className="facility-icon">🏥</span>
                    <div className="facility-info">
                      <span className="facility-name">{h.poi_name || h.name}</span>
                      <span className="facility-source">
                        {h.osm_source === 'REAL' ? (
                          <span className="source-real">REAL OSM · ID: {h.osm_id || 'verified'}</span>
                        ) : (
                          <span className="source-est">ESTIMATED</span>
                        )}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Simulation HUD */}
          {['baseline', 'severed', 'rerouted'].includes(simulationPhase) && (
            <div className={`simulation-hud hud-${simulationPhase}`}>
              <div className="hud-phase-badge">
                {simulationPhase === 'baseline' && 'PHASE 1: BASELINE ACCESS'}
                {simulationPhase === 'severed' && 'PHASE 2: CYCLONE HAZARD — BRIDGE UNAVAILABLE'}
                {simulationPhase === 'rerouted' && 'PHASE 3: COUNTERFACTUAL REROUTE COMPLETE'}
              </div>
              <div className="hud-message">
                {simulationPhase === 'baseline' &&
                  `Normal emergency access route active via Bridge ${result?.asset_id} (${result?.asset_name})`}
                {simulationPhase === 'severed' &&
                  `Simulating hypothetical unavailability of Bridge ${result?.asset_id} — route severed ✖`}
                {simulationPhase === 'rerouted' &&
                  `Alternate route active: +${result?.max_disruption_delta_min ?? 9.5} min emergency delay · AI Briefing generated ✨`}
              </div>
            </div>
          )}

          {/* Primary Map Canvas */}
          <PreImpactMap
            demoData={activeData}
            selectedResult={result}
            onSelectResult={(r) => { setSelectedResult(r); setSimulationPhase('initial'); }}
            simulationPhase={simulationPhase}
            simulationStep={simulationPhase}
          />

          {/* Full Asset Ranking Overlay Modal */}
          {activeTab === 'ranking' && (
            <div className="map-overlay-modal">
              <div className="mom-header">
                <span className="mom-title">CRITICAL ASSET RESILIENCE PRIORITIES</span>
                <button
                  className="mom-close-btn"
                  onClick={() => setActiveTab('map')}
                >
                  ← Return to Map
                </button>
              </div>
              <div className="mom-content">
                <AssetRanking
                  results={activeData?.counterfactual_results || []}
                  selectedId={result?.asset_id}
                  onSelect={(r) => { setSelectedResult(r); setSimulationPhase('initial'); setActiveTab('map'); }}
                />
              </div>
            </div>
          )}

          {/* Methodology & Data Quality Drawer */}
          {activeTab === 'data' && (
            <div className="map-overlay-modal">
              <div className="mom-header">
                <span className="mom-title">DATA PROVENANCE & METHODOLOGY</span>
                <button
                  className="mom-close-btn"
                  onClick={() => setActiveTab('map')}
                >
                  ← Return to Map
                </button>
              </div>
              <div className="mom-content mom-data-view">
                <DataQualityPanel
                  dataLabels={activeData?.data_labels}
                  graphSource={activeData?.graph_source}
                  mode={activeData?.mode}
                  warning={activeData?.dq_warning}
                  modeDescription={activeData?.mode_description}
                />
                <MethodologyNote mode={activeData?.mode} />
              </div>
            </div>
          )}
        </div>

        {/* Right Panel: Selected Asset Disruption Dossier (~32%) */}
        <div className="right-panel">
          <DisruptionCard
            headline={activeData?.headline}
            result={result}
            cyclone={activeData?.cyclone_scenario}
          />
        </div>
      </div>
    </div>
  )
}

export default App
