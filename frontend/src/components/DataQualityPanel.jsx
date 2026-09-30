// DataQualityPanel.jsx — Shows source/provenance for each data layer
// Updated for PARTIAL_REAL_DATA mode (M2 correction)

const TYPE_STYLES = {
  REAL:          { bg: '#14532d', color: '#86efac', icon: '✓' },
  ESTIMATED:     { bg: '#713f12', color: '#fde68a', icon: '~' },
  MODELLED:      { bg: '#1e3a8a', color: '#93c5fd', icon: 'M' },
  SYNTHETIC:     { bg: '#3b1764', color: '#d8b4fe', icon: 'S' },
  COUNTERFACTUAL:{ bg: '#1e1b4b', color: '#c4b5fd', icon: 'CF' },
  DEMO:          { bg: '#292524', color: '#d6d3d1', icon: 'D' },
  UNKNOWN:       { bg: '#1c1917', color: '#78716c', icon: '?' },
}

export function ProvenanceBadge({ type, label }) {
  const key  = (type || 'UNKNOWN').toUpperCase().split('/')[0].trim()
  const style = TYPE_STYLES[key] || TYPE_STYLES.UNKNOWN
  return (
    <span
      className="prov-badge"
      style={{ background: style.bg, color: style.color }}
      title={`Data type: ${type}`}
    >
      {style.icon} {label || type}
    </span>
  )
}

function inferType(value) {
  const v = (value || '').toUpperCase()
  if (v.startsWith('REAL')) return 'REAL'
  if (v.startsWith('SYNTHETIC') || v.startsWith('MODELLED') || v.startsWith('MODELED')) return 'SYNTHETIC'
  if (v.startsWith('ESTIMATED') || v.startsWith('FALLBACK')) return 'ESTIMATED'
  if (v.startsWith('COUNTERFACTUAL')) return 'COUNTERFACTUAL'
  if (v.startsWith('DEMO')) return 'DEMO'
  return 'MODELLED'
}

const MODE_CONFIG = {
  REAL_OSM: {
    badge: 'mode-real',
    icon: '✓',
    label: 'REAL OSM DATA',
    description: 'Full OpenStreetMap road network — genuine download',
    alertClass: null,
  },
  PARTIAL_REAL_DATA: {
    badge: 'mode-partial',
    icon: '⚠',
    label: 'PARTIAL REAL DATA',
    description: 'Hospital locations: Real OSM · Road network: Modelled synthetic (live OSM unavailable)',
    alertClass: 'alert-partial',
  },
  DEMO_FALLBACK: {
    badge: 'mode-demo',
    icon: '⚠',
    label: 'DEMO FALLBACK',
    description: 'All data is synthetic. No real OSM data loaded.',
    alertClass: 'alert-demo',
  },
}

export default function DataQualityPanel({ dataLabels, graphSource, mode, warning, modeDescription }) {
  if (!dataLabels) return null

  const entries = Object.entries(dataLabels)
  const cfg = MODE_CONFIG[mode] || MODE_CONFIG['DEMO_FALLBACK']

  return (
    <div className="data-quality-panel">
      <div className="section-label">DATA PROVENANCE</div>

      {/* Mode banner */}
      <div className={`dq-mode-banner ${cfg.alertClass || ''}`}>
        <span className={`dq-mode-badge ${cfg.badge}`}>
          {cfg.icon} {cfg.label}
        </span>
        <span className="dq-mode-desc">{modeDescription || cfg.description}</span>
        {graphSource && (
          <span className="dq-graph-src">graph_source: <code>{graphSource}</code></span>
        )}
      </div>

      {/* Warning box for non-REAL_OSM modes */}
      {warning && (
        <div className="dq-warning-box">
          <span className="dq-warning-icon">⚠</span>
          <span>{warning}</span>
        </div>
      )}

      {/* Per-layer provenance table */}
      <div className="dq-table">
        {entries.map(([key, value]) => {
          const type = inferType(value)
          return (
            <div key={key} className="dq-row">
              <span className="dq-key">{key.replace(/_/g, ' ')}</span>
              <ProvenanceBadge type={type} label={type} />
              <span className="dq-value" title={value}>{value}</span>
            </div>
          )
        })}
      </div>

      <div className="dq-footer">
        All counterfactual results are MODELLED SCENARIO ANALYSIS — not failure predictions.
      </div>
    </div>
  )
}
