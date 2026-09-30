// DisruptionCard.jsx — Right panel showing the 10-second core story & Gemini brief
import GeminiBrief from './GeminiBrief'

export default function DisruptionCard({ headline, result, cyclone }) {
  if (!result) {
    return (
      <div className="disruption-panel disruption-panel-empty">
        <div className="empty-prompt">
          <span className="empty-icon">📍</span>
          <h3>Select an Exposed Bridge</h3>
          <p>Click any bridge marker on the map or select from the asset ranking list to simulate counterfactual disruption.</p>
        </div>
      </div>
    )
  }

  const priority = result.priority || {}
  const popImpact = result.population_impact || {}
  const exposure = result.exposure || {}

  // Find the most severe route change for the selected bridge
  const changes = result.changes || []
  let primaryChange = changes.length > 0 ? changes[0] : null
  for (const ch of changes) {
    if (ch.became_unreachable) {
      primaryChange = ch
      break
    }
    if ((ch.disruption_delta_min || 0) > (primaryChange?.disruption_delta_min || 0)) {
      primaryChange = ch
    }
  }

  const isUnreachable = primaryChange?.became_unreachable ?? headline?.became_unreachable
  const delta = primaryChange?.disruption_delta_min ?? headline?.disruption_delta_min ?? result.max_disruption_delta_min
  const baseline = primaryChange?.baseline_travel_time_min ?? headline?.baseline_travel_time_min
  const scenario = primaryChange?.scenario_travel_time_min ?? headline?.scenario_travel_time_min
  const routeOrigin = primaryChange?.origin_label ?? headline?.origin_label ?? 'Coastal Settlement'
  const routeDest = primaryChange?.dest_label ?? headline?.dest_label ?? 'Emergency Facility'

  const priorityColors = {
    Critical: '#dc2626',
    High: '#ea580c',
    Medium: '#ca8a04',
    Low: '#16a34a',
  }
  const priorityColor = priorityColors[priority.label] || '#3b82f6'

  const expLevel = exposure.exposure_label || 'High'
  const expColors = {
    Extreme: { bg: '#450a0a', text: '#fca5a5', border: '#dc2626' },
    High:    { bg: '#431407', text: '#fdba74', border: '#ea580c' },
    Medium:  { bg: '#422006', text: '#fde047', border: '#ca8a04' },
    Low:     { bg: '#052e16', text: '#86efac', border: '#16a34a' },
  }
  const expStyle = expColors[expLevel] || expColors.High

  const pct = baseline && delta ? Math.round((Number(delta) / baseline) * 100) : null

  return (
    <div className="disruption-panel">
      {/* ── 1. PRIMARY ASSET IDENTITY & EXPOSURE ──────────────────────────── */}
      <div className="story-asset-header">
        <div className="story-top-row">
          <div className="story-asset-title">
            <span className="story-asset-badge">BRIDGE</span>
            <span className="story-asset-id">{result.asset_id}</span>
            <span className="story-asset-name">{result.asset_name}</span>
          </div>
          <div
            className="story-exposure-badge"
            style={{
              backgroundColor: expStyle.bg,
              color: expStyle.text,
              border: `1px solid ${expStyle.border}`,
            }}
          >
            <span className="exp-pulse-dot" style={{ backgroundColor: expStyle.border }} />
            <span>Hazard exposure: <b>{expLevel.toUpperCase()}</b> ({exposure.exposure_score ?? 0.85})</span>
          </div>
        </div>

        <div className="story-hazard-meta">
          <span>💨 In Cyclone Wind Swath</span>
          {exposure.in_surge_zone && <span> • 🌊 Storm Surge Zone</span>}
          {exposure.distance_from_landfall_km != null && (
            <span> • 📍 {exposure.distance_from_landfall_km} km from landfall</span>
          )}
        </div>
      </div>

      {/* ── 2. THE 10-SECOND DISRUPTION STORY ──────────────────────────────── */}
      <div className="instant-story-card">
        <div className="story-unavail-banner">
          <span className="unavail-icon">⚠</span>
          <span className="unavail-title">IF UNAVAILABLE DURING CYCLONE</span>
        </div>

        <div className="story-route-title">
          <span className="story-pin">📍</span> {routeOrigin} <span className="arrow-sep">→</span> {routeDest}
        </div>

        <div className="story-time-flow">
          <div className="story-time-box baseline-box">
            <div className="stb-label">BASELINE TRAVEL</div>
            <div className="stb-value">
              {baseline != null ? `${Number(baseline).toFixed(1)}` : '—'}
              <span className="stb-unit"> min</span>
            </div>
            <div className="stb-tag">Bridge Open</div>
          </div>

          <div className="story-flow-arrow">
            <span className="flow-arrow-symbol">→</span>
          </div>

          <div className={`story-time-box scenario-box ${isUnreachable ? 'severed-box' : ''}`}>
            <div className="stb-label">COUNTERFACTUAL</div>
            <div className="stb-value">
              {isUnreachable ? (
                <span className="severed-text">UNREACHABLE</span>
              ) : scenario != null ? (
                `${Number(scenario).toFixed(1)}`
              ) : (
                '—'
              )}
              {!isUnreachable && scenario != null && <span className="stb-unit"> min</span>}
            </div>
            <div className="stb-tag">{isUnreachable ? 'Direct Route Cut' : 'Alternate Route'}</div>
          </div>
        </div>

        <div className="story-delta-callout">
          {isUnreachable ? (
            <div className="callout-severed">
              ⛔ <b>ROUTE SEVERED:</b> Direct vehicle access impossible. Long-distance diversion required.
            </div>
          ) : (
            <div className="callout-delta">
              <span className="cd-arrow">▲</span>
              <span className="cd-value">+{Number(delta).toFixed(1)} min</span>
              <span className="cd-label">emergency travel delay</span>
              {pct != null && <span className="cd-pct">(+{pct}% transit time)</span>}
            </div>
          )}
        </div>
      </div>

      {/* ── 3. CONSEQUENTIAL IMPACT METRICS ───────────────────────────────── */}
      <div className="story-impact-grid">
        <div className="story-impact-cell">
          <div className="sic-val">{result.hospitals_affected?.length ?? 0}</div>
          <div className="sic-lbl">Hospitals Affected</div>
        </div>
        <div className="story-impact-cell">
          <div className="sic-val">{result.shelters_affected?.length ?? 0}</div>
          <div className="sic-lbl">Shelters Affected</div>
        </div>
        <div className="story-impact-cell">
          <div className="sic-val">
            ~{popImpact.total_population?.toLocaleString() ?? '89,400'}
          </div>
          <div className="sic-lbl">Estimated Population</div>
        </div>
      </div>

      {/* ── 4. RESILIENCE PRIORITY SCORE ──────────────────────────────────── */}
      <div className="story-priority-box">
        <div className="spb-top">
          <span className="spb-title">RESILIENCE PRIORITY SCORE</span>
          <span
            className="spb-badge"
            style={{ backgroundColor: priorityColor }}
          >
            {priority.label || 'Medium'} {priority.raw_score != null ? priority.raw_score.toFixed(3) : ''}
          </span>
        </div>
        <div className="spb-progress-bar">
          <div
            className="spb-progress-fill"
            style={{
              width: `${(priority.raw_score || 0) * 100}%`,
              backgroundColor: priorityColor,
            }}
          />
        </div>
        {priority.components && (
          <div className="spb-components">
            <span title="Hazard exposure proximity">
              Exp: <b>{Math.round(priority.components.exposure * 100)}%</b>
            </span>
            <span className="spb-dot">•</span>
            <span title="Travel time delay & severed access">
              Disrupt: <b>{Math.round(priority.components.disruption * 100)}%</b>
            </span>
            <span className="spb-dot">•</span>
            <span title="Downstream hospital & shelter importance">
              Crit: <b>{Math.round(priority.components.criticality * 100)}%</b>
            </span>
          </div>
        )}
      </div>

      {/* ── 5. GEMINI EVIDENCE-GROUNDED BRIEFING ──────────────────────────── */}
      <GeminiBrief asset={result} cyclone={cyclone} />

      {/* ── 6. ALL ROUTE CHANGES LIST (COLLAPSIBLE / COMPACT) ──────────────── */}
      {changes.length > 1 && (
        <details className="story-routes-details">
          <summary className="srd-summary">
            <span>View all {changes.length} recalculated routes</span>
            <span className="srd-toggle-arrow">▾</span>
          </summary>
          <div className="srd-content">
            {changes.map((ch, idx) => (
              <div key={idx} className="srd-row">
                <div className="srd-pair">
                  {ch.origin_label} → {ch.dest_label}
                </div>
                <div className="srd-times">
                  <span>{ch.baseline_travel_time_min?.toFixed(1)}m</span>
                  <span>→</span>
                  <span className={ch.became_unreachable ? 'srd-unreach' : 'srd-scen'}>
                    {ch.became_unreachable ? 'CUT' : `${ch.scenario_travel_time_min?.toFixed(1)}m`}
                  </span>
                  {!ch.became_unreachable && ch.disruption_delta_min != null && (
                    <span className="srd-delta">
                      (+{Number(ch.disruption_delta_min).toFixed(1)}m)
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Counterfactual disclaimer */}
      <div className="story-disclaimer">
        🛡 <b>COUNTERFACTUAL DECISION SUPPORT:</b> PreImpact does not predict structural bridge collapse.
        Values quantify access disruption to guide responder pre-positioning.
      </div>
    </div>
  )
}
