// CycloneSummaryBanner.jsx — Compact single-strip situational awareness ribbon
export default function CycloneSummaryBanner({ summary, cyclone, mode }) {
  const sc = cyclone || {}
  const sum = summary || {}

  const totalBridges = sum.total_bridges ?? 126
  const exposedBridges = sum.exposed_bridges ?? totalBridges
  const analyzedBridges = sum.analyzed_bridges ?? 12
  const hospitalsCount = sum.hospitals_potentially_affected ?? 5
  const communitiesCount = sum.communities_potentially_affected ?? 9
  const popEstimate = sum.population_estimate_affected ?? 89400

  return (
    <div className="cyclone-summary-banner">
      <div className="csb-identity">
        <span className="csb-icon">🌀</span>
        <div className="csb-titles">
          <div className="csb-title-line">
            <span className="csb-main-title">CYCLONE SCENARIO:</span>{' '}
            <span className="csb-scenario-name">{sc.name || 'VSCS Cyclone Replay Analogue'}</span>
            <span className="csb-replay-badge">HISTORICAL REPLAY</span>
          </div>
          <div className="csb-meta-line">
            <span className="csb-meta-item">📍 <b>Region:</b> {sc.region || 'Kendrapara District, Coastal Odisha'}</span>
            <span className="csb-meta-sep">•</span>
            <span className="csb-meta-item">⏱ <b>Exposure Window:</b> {sc.exposure_window || 'T-6h to T+12h Landfall'}</span>
            <span className="csb-meta-sep">•</span>
            <span className="csb-meta-item">💨 <b>Max Wind:</b> {sc.max_wind_kmh || 175} km/h</span>
            <span className="csb-meta-sep">•</span>
            <span className="csb-meta-item">🌊 <b>Peak Surge:</b> {sc.storm_surge_m || 3.5}m</span>
          </div>
        </div>
      </div>

      {/* Restrained horizontal metrics strip */}
      <div className="csb-metrics-row">
        <div className="csb-chip">
          <span className="csb-chip-label">TOTAL BRIDGES</span>
          <span className="csb-chip-val">{totalBridges}</span>
        </div>

        <span className="csb-arrow">→</span>

        <div className="csb-chip csb-chip-exposed">
          <span className="csb-chip-label">BRIDGES EXPOSED</span>
          <span className="csb-chip-val">{exposedBridges}</span>
        </div>

        <span className="csb-arrow">→</span>

        <div className="csb-chip csb-chip-critical">
          <span className="csb-chip-label">ANALYZED CRITICAL</span>
          <span className="csb-chip-val">{analyzedBridges}</span>
        </div>

        <div className="csb-divider"></div>

        <div className="csb-chip">
          <span className="csb-chip-label">HOSPITALS EXPOSED</span>
          <span className="csb-chip-val">{hospitalsCount}</span>
        </div>

        <div className="csb-chip">
          <span className="csb-chip-label">COMMUNITIES EXPOSED</span>
          <span className="csb-chip-val">{communitiesCount}</span>
        </div>

        <div className="csb-chip">
          <span className="csb-chip-label">EST. POPULATION</span>
          <span className="csb-chip-val">~{popEstimate.toLocaleString()}</span>
        </div>

        <div className="csb-provenance-box">
          <span className="csb-prov-badge">MODELED HAZARD FOOTPRINT</span>
          <span className="csb-prov-sub">IMD Archive & Replay Analogue · Not an operational forecast</span>
        </div>
      </div>
    </div>
  )
}
