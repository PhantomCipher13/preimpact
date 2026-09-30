// Header.jsx — App header with title and demo badge
export default function Header() {
  return (
    <header className="app-header">
      <div className="header-left">
        <div className="header-logo">
          <span className="logo-icon">⚡</span>
          <span className="logo-text">PREIMPACT</span>
        </div>
        <div className="header-subtitle">
          Counterfactual Infrastructure Resilience Engine
        </div>
      </div>
      <div className="header-right">
        <span className="demo-badge">DEMO SCENARIO</span>
        <span className="region-badge">📍 Kendrapara, Odisha</span>
      </div>
    </header>
  )
}
