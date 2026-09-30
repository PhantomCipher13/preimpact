// MethodologyNote.jsx — Full Trust, Governance & Methodology Panel
export default function MethodologyNote({ mode }) {
  const isReal = mode === 'REAL_OSM'

  return (
    <div className="methodology-box">
      <div className="method-trust-header">
        <span className="mth-icon">🛡</span>
        <div className="mth-titles">
          <span className="mth-main">WHAT PREIMPACT DOES</span>
          <span className="mth-sub">Counterfactual Resilience & Decision Support</span>
        </div>
      </div>

      <div className="method-core-statements">
        <div className="mcs-callout">
          <b>PreImpact does not predict infrastructure failure.</b>
        </div>
        <p className="mcs-desc">
          It evaluates <b>hypothetical infrastructure unavailability</b> and measures the resulting
          <b> emergency-access disruption</b> under a modeled cyclone scenario to guide pre-impact
          responder preparedness.
        </p>
      </div>

      {/* Methodology Progression Flow */}
      <div className="method-pipeline-title">ANALYTIC PROGRESSION</div>
      <div className="method-pipeline-flow">
        <span className="mpf-step">Hazard Exposure</span>
        <span className="mpf-arrow">→</span>
        <span className="mpf-step">Counterfactual Unavailability</span>
        <span className="mpf-arrow">→</span>
        <span className="mpf-step">Network Rerouting</span>
        <span className="mpf-arrow">→</span>
        <span className="mpf-step">Accessibility Change</span>
        <span className="mpf-arrow">→</span>
        <span className="mpf-step">Consequence</span>
        <span className="mpf-arrow">→</span>
        <span className="mpf-step">Resilience Priority</span>
        <span className="mpf-arrow">→</span>
        <span className="mpf-step mpf-human">Human Decision Support</span>
      </div>

      {/* 3-Column Provenance Categorization */}
      <div className="method-prov-grid">
        <div className="mpg-col mpg-real">
          <div className="mpg-header">
            <span className="mpg-dot dot-real"></span> REAL DATA
          </div>
          <ul className="mpg-list">
            <li><b>OSM road network:</b> {isReal ? '1,672 nodes, 4,115 edges' : 'Available in REAL mode'}</li>
            <li><b>OSM bridges:</b> {isReal ? '126 bridges detected' : 'OSM bridge=yes tags'}</li>
            <li><b>OSM hospitals:</b> 5 verified facilities with OSM IDs & coordinates</li>
          </ul>
        </div>

        <div className="mpg-col mpg-modeled">
          <div className="mpg-header">
            <span className="mpg-dot dot-modeled"></span> MODELED
          </div>
          <ul className="mpg-list">
            <li><b>Cyclone hazard footprint:</b> IMD Fani 2019 replay track & wind buffers</li>
            <li><b>Route consequences:</b> NetworkX Dijkstra shortest-path travel times</li>
            <li><b>Resilience priority:</b> (Exposure × Disruption × Criticality)<sup>1/3</sup></li>
          </ul>
        </div>

        <div className="mpg-col mpg-estimated">
          <div className="mpg-header">
            <span className="mpg-dot dot-estimated"></span> ESTIMATED
          </div>
          <ul className="mpg-list">
            <li><b>Population:</b> ~89,400 across Kendrapara settlements (Census 2011 estimates)</li>
            <li><b>Cyclone shelters:</b> Fallback coordinates where live Overpass returns null</li>
          </ul>
        </div>
      </div>

      <div className="method-footer">
        Priority = (Exposure × Disruption × Criticality)<sup>1/3</sup> · Decision support only · No autonomous orders
      </div>
    </div>
  )
}
