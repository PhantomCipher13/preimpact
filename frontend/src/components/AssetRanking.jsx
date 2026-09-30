// AssetRanking.jsx — M2 bridge ranking panel with full impact columns
export default function AssetRanking({ results, selectedId, onSelect }) {
  if (!results || results.length === 0) return null

  const priorityColor = (label) => ({
    Critical: '#dc2626', High: '#ea580c', Medium: '#ca8a04', Low: '#16a34a'
  }[label] || '#666')

  return (
    <div className="ranking-table-wrap">
      <div className="ranking-header">
        <div className="section-label">BRIDGE RANKING — COUNTERFACTUAL IMPACT</div>
        <div className="ranking-sublabel">
          Sorted by Resilience Priority Score · MODELLED RESULTS
        </div>
      </div>
      <div className="ranking-table">
        {/* Column headers */}
        <div className="rank-row rank-header">
          <span>Asset</span>
          <span>Exposure</span>
          <span>Max Δ (min)</span>
          <span>Pop. Affected</span>
          <span>Hosp.</span>
          <span>Shelt.</span>
          <span>Priority</span>
        </div>
        {results.map((r, idx) => {
          const priority = r.priority || {}
          const pop      = r.population_impact || {}
          const exposure = r.exposure || {}
          const isSelected = selectedId === r.asset_id
          return (
            <div
              key={r.asset_id}
              className={`rank-row rank-data ${isSelected ? 'rank-selected' : ''}`}
              onClick={() => onSelect(r)}
            >
              <span className="rank-asset-id">
                <span className="rank-num">{idx + 1}</span>
                <span className="rank-id">{r.asset_id}</span>
              </span>
              <span>
                <span className={`exposure-dot exp-${exposure.exposure_label?.toLowerCase()}`}>
                  ●
                </span>
                {' '}{exposure.exposure_label || '?'}
              </span>
              <span className="rank-delta">
                +{r.max_disruption_delta_min?.toFixed(1) ?? '—'}
              </span>
              <span className="rank-pop">
                ~{(pop.affected_population ?? 0).toLocaleString()}
                <span className="est-label">est.</span>
              </span>
              <span>{r.hospitals_affected?.length ?? 0}</span>
              <span>{r.shelters_affected?.length ?? 0}</span>
              <span>
                <span
                  className="priority-pill"
                  style={{ background: priorityColor(priority.label) }}
                >
                  {priority.label || '?'}
                </span>
                <span className="priority-score-sm">{priority.raw_score?.toFixed(2)}</span>
              </span>
            </div>
          )
        })}
      </div>
      <div className="ranking-footer">
        ⚠ COUNTERFACTUAL MODELLED RESULTS — not failure predictions.
        Priority = Exposure × Disruption × Criticality (geometric mean).
      </div>
    </div>
  )
}
