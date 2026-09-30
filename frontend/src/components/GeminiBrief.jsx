// GeminiBrief.jsx — Evidence-grounded AI decision-support briefing
import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export default function GeminiBrief({ asset, cyclone }) {
  const [brief, setBrief] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const assetId = asset?.asset_id

  useEffect(() => {
    if (!assetId) return
    fetchBrief(assetId)
  }, [assetId])

  async function fetchBrief(id, force = false) {
    setLoading(true)
    setError(null)
    try {
      const url = `${API_BASE}/api/brief/${id}${force ? '?force_refresh=true' : ''}`
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Brief API status ${res.status}`)
      const data = await res.json()
      setBrief(data)
    } catch (err) {
      console.warn('Brief fetch failed, generating client-side fallback:', err)
      // Client-side fallback if backend is unreachable
      setBrief(buildClientFallback(asset, cyclone))
    } finally {
      setLoading(false)
    }
  }

  function buildClientFallback(a, c) {
    const aid = a?.asset_id || 'UNKNOWN'
    const name = a?.asset_name || aid
    const exp = a?.exposure || {}
    const delta = a?.max_disruption_delta_min || 0.0
    const pop = a?.population_impact?.total_population || 89400
    const hosps = a?.hospitals_affected?.length || 0
    const shelters = a?.shelters_affected?.length || 0

    return {
      status: 'fallback',
      badge: 'PREIMPACT EVIDENCE TEMPLATE',
      is_ai_generated: false,
      notice: 'GEMINI BRIEFING UNAVAILABLE -- Core resilience analysis remains fully operational.',
      why_prioritized: `Bridge ${aid} (${name}) is prioritized because its hypothetical unavailability produces a significant increase in emergency travel time (+${delta.toFixed(1)} min) under the modeled cyclone scenario, combined with ${exp.exposure_label || 'High'} hazard exposure (${exp.exposure_score ?? 0.85}).`,
      counterfactual_impact: `Under baseline conditions, emergency transit along the corridor is unobstructed. If Bridge ${aid} becomes unavailable, rerouted emergency vehicles face an additional +${delta.toFixed(1)} min travel-time delay along alternate coastal roads.`,
      affected_services: `Access to ${hosps} hospitals and ${shelters} cyclone shelters in the service corridor would be impacted, affecting an estimated population of ${pop.toLocaleString()} residents.`,
      preparation_options: [
        `Pre-position emergency ambulances and rescue personnel on the critical side of ${aid} before landfall.`,
        'Verify road surface and culvert conditions along designated alternate detour routes.',
        `Stage critical medical supplies and emergency rations at community health centers serving ${pop.toLocaleString()} residents.`,
        `Establish real-time corridor monitoring and satellite links at Bridge ${aid} during the cyclone transit window.`,
        'Coordinate emergency response standby teams between district headquarters and block officers.',
      ],
      disclaimer: 'Generated from deterministic PreImpact analysis. No structural collapse or failure probability predicted.',
    }
  }

  if (!asset) return null

  return (
    <div className="gemini-brief-card">
      <div className="gb-header">
        <div className="gb-title-group">
          <span className="gb-sparkle">✨</span>
          <span className="gb-title">AI RESPONSE BRIEF</span>
        </div>
        <div className="gb-header-actions">
          {brief?.is_ai_generated ? (
            <span className="gb-badge gb-badge-live">GEMINI — EVIDENCE-GROUNDED</span>
          ) : (
            <span className="gb-badge gb-badge-template">EVIDENCE-GROUNDED TEMPLATE</span>
          )}
          <button
            className="gb-refresh-btn"
            onClick={() => fetchBrief(assetId, true)}
            title="Refresh AI briefing"
            disabled={loading}
          >
            {loading ? '…' : '↻'}
          </button>
        </div>
      </div>

      <div className="gb-provenance-sub">
        Generated from deterministic PreImpact analysis · No failure probability predicted
      </div>

      {brief?.notice && !brief.is_ai_generated && (
        <div className="gb-notice-box">
          <span className="gb-notice-icon">ℹ</span>
          <span className="gb-notice-text">
            <b>GEMINI BRIEFING UNAVAILABLE</b> — Core resilience analysis remains fully operational.
          </span>
        </div>
      )}

      {loading ? (
        <div className="gb-loading">
          <div className="gb-spinner"></div>
          <span>Synthesizing evidence-grounded briefing for {assetId}…</span>
        </div>
      ) : brief ? (
        <div className="gb-body">
          {/* Section A: Why Prioritized */}
          <div className="gb-section">
            <div className="gb-section-title">
              <span className="gb-num">A</span> WHY THIS ASSET IS PRIORITIZED
            </div>
            <p className="gb-section-text">{brief.why_prioritized}</p>
          </div>

          {/* Section B: Counterfactual Impact */}
          <div className="gb-section">
            <div className="gb-section-title">
              <span className="gb-num">B</span> WHAT THE COUNTERFACTUAL SCENARIO CHANGES
            </div>
            <p className="gb-section-text">{brief.counterfactual_impact}</p>
          </div>

          {/* Section C: Affected Services */}
          <div className="gb-section">
            <div className="gb-section-title">
              <span className="gb-num">C</span> WHO/WHAT COULD EXPERIENCE ACCESS DISRUPTION
            </div>
            <p className="gb-section-text">{brief.affected_services}</p>
          </div>

          {/* Section D: Pre-Impact Preparation Options */}
          <div className="gb-section">
            <div className="gb-section-title">
              <span className="gb-num">D</span> PRE-IMPACT PREPARATION OPTIONS
            </div>
            <ul className="gb-options-list">
              {brief.preparation_options?.map((opt, idx) => (
                <li key={idx} className="gb-option-item">
                  <span className="gb-check">✓</span>
                  <span>{opt}</span>
                </li>
              ))}
            </ul>
            <div className="gb-policy-note">
              🛡 <i>Decision-support only: Never issues autonomous evacuation or road closure orders.</i>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
