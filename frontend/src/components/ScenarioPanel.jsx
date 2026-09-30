// ScenarioPanel.jsx — Left panel: cyclone scenario + bridge ranking
export default function ScenarioPanel({ demoData, selectedResult, onSelectResult }) {
  if (!demoData) return null

  const cyclone = demoData.cyclone_scenario || {}
  const results = demoData.counterfactual_results || []

  return (
    <div className="scenario-panel">
      {/* Cyclone Scenario Box */}
      <div className="panel-section">
        <div className="section-label">CYCLONE SCENARIO</div>
        <div className="cyclone-card">
          <div className="cyclone-name">{cyclone.name}</div>
          <div className="cyclone-stats">
            <div className="stat-item">
              <span className="stat-value">{cyclone.max_wind_kmh}</span>
              <span className="stat-unit">km/h</span>
              <span className="stat-label">Max Wind</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{cyclone.storm_surge_m}</span>
              <span className="stat-unit">m</span>
              <span className="stat-label">Storm Surge</span>
            </div>
          </div>
          <div className="data-provenance">{cyclone.source}</div>
        </div>
      </div>

      {/* Network Stats */}
      <div className="panel-section">
        <div className="section-label">GRAPH STATUS</div>
        <div className="graph-stats">
          <div className="stat-row">
            <span>Mode</span>
            {demoData.mode === 'REAL_OSM' ? (
              <span className="badge-real">✓ REAL OSM</span>
            ) : demoData.mode === 'PARTIAL_REAL_DATA' ? (
              <span className="badge-partial">⚠ PARTIAL REAL</span>
            ) : (
              <span className="badge-demo">DEMO SYNTHETIC</span>
            )}
          </div>
          <div className="stat-row">
            <span>Road network</span>
            <span className="highlight-sm">
              {demoData.mode === 'REAL_OSM'
                ? 'OpenStreetMap'
                : 'Modeled fallback (real coords)'}
            </span>
          </div>
          <div className="stat-row">
            <span>Nodes / Edges</span>
            <span>{demoData.node_count} / {demoData.edge_count}</span>
          </div>
          <div className="stat-row">
            <span>Bridges detected</span>
            <span className="highlight">{demoData.bridges_detected}</span>
          </div>
        </div>
        {demoData.mode === 'PARTIAL_REAL_DATA' && (
          <div className="provenance-note-inline">
            ⚠ Road network: Modeled fallback — live OSM road retrieval unavailable
          </div>
        )}
        {demoData.mode === 'REAL_OSM' && (
          <div className="provenance-note-inline real-note">
            ✓ Genuine OpenStreetMap road network
          </div>
        )}
      </div>

      {/* Facilities & Hospitals with Provenance */}
      <div className="panel-section">
        <div className="section-label">EMERGENCY FACILITIES</div>
        {demoData.hospitals?.slice(0, 5).map((h, i) => (
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
        {demoData.shelters?.slice(0, 3).map((s, i) => (
          <div key={i} className="facility-row">
            <span className="facility-icon">🏠</span>
            <div className="facility-info">
              <span className="facility-name">{s.poi_name || s.name}</span>
              <span className="facility-source">
                <span className="source-est">ESTIMATED / FALLBACK</span>
              </span>
            </div>
          </div>
        ))}
      </div>


      {/* Critical Asset Priorities — Ranked by Resilience Priority Score */}
      <div className="panel-section">
        <div className="section-label">CRITICAL ASSET PRIORITIES</div>
        <div className="section-sublabel">Ranked by Resilience Priority Score (Exposure × Disruption × Criticality)</div>
        <div className="bridge-list">
          {results.map((r, idx) => {
            const priority = r.priority || {}
            const exp = r.exposure || {}
            const isSelected = selectedResult?.asset_id === r.asset_id
            const isUnreachable = r.unreachable_count > 0
            return (
              <button
                key={r.asset_id}
                className={`bridge-row ${isSelected ? 'selected' : ''}`}
                onClick={() => onSelectResult(r)}
              >
                <div className="bridge-row-top">
                  <div className="bridge-id-wrap">
                    <span className="rank-num-pill">#{idx + 1}</span>
                    <span className="bridge-id">{r.asset_id}</span>
                  </div>
                  <span className="bridge-name" title={r.asset_name}>{r.asset_name}</span>
                  <span className={`priority-badge priority-${priority.label?.toLowerCase()}`}>
                    {priority.label || 'Low'}
                  </span>
                </div>
                <div className="bridge-row-stats">
                  <span className="stat-priority-score">
                    Score: <b>{priority.raw_score?.toFixed(3) ?? '0.000'}</b>
                  </span>
                  <span className="stat-delta">
                    {isUnreachable ? (
                      <span className="unreach-tag">⛔ UNREACHABLE</span>
                    ) : (
                      `Δ +${r.max_disruption_delta_min?.toFixed(1) ?? '0.0'} min`
                    )}
                  </span>
                </div>
                <div className="bridge-row-components">
                  <span>Exp: {exp.exposure_score?.toFixed(2) ?? '—'}</span>
                  <span>·</span>
                  <span>Disr: {priority.components?.disruption?.toFixed(2) ?? '—'}</span>
                  <span>·</span>
                  <span>Crit: {priority.components?.criticality?.toFixed(2) ?? '—'}</span>
                </div>
              </button>
            )
          })}
        </div>
      </div>


      {/* Settlements */}
      <div className="panel-section">
        <div className="section-label">SETTLEMENTS</div>
        {demoData.settlements?.map((s) => (
          <div key={s.node_id} className="settlement-row">
            <span className="settlement-dot">●</span>
            <span className="settlement-name">{s.name}</span>
            <span className="settlement-pop">~{s.population_estimate?.toLocaleString()}</span>
          </div>
        ))}
        <div className="data-provenance small">* Estimated population — not official census data</div>
      </div>
    </div>
  )
}
