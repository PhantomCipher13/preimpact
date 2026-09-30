import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo)
    this.setState({ errorInfo })
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #f8fafc 0%, #eef2f7 50%, #e2e8f0 100%)',
          fontFamily: "'Inter', -apple-system, sans-serif",
          padding: '20px',
        }}>
          <div style={{
            maxWidth: '560px',
            width: '100%',
            background: 'rgba(255, 255, 255, 0.92)',
            backdropFilter: 'blur(20px)',
            borderRadius: '14px',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            boxShadow: '0 14px 38px -4px rgba(15, 23, 42, 0.12)',
            padding: '32px',
            color: '#0f172a',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
              <span style={{ fontSize: '24px' }}>⚠</span>
              <h2 style={{ fontSize: '18px', fontWeight: 800, margin: 0, color: '#b91c1c' }}>
                PreImpact Rendering Error
              </h2>
            </div>
            <p style={{ fontSize: '13px', color: '#334155', lineHeight: 1.6, marginBottom: '16px' }}>
              An unexpected error occurred while rendering the dashboard. The underlying data engine remains intact.
            </p>
            {this.state.error && (
              <pre style={{
                background: '#f1f5f9',
                border: '1px solid #cbd5e1',
                borderRadius: '8px',
                padding: '12px',
                fontSize: '11.5px',
                fontFamily: "'JetBrains Mono', monospace",
                color: '#dc2626',
                overflowX: 'auto',
                marginBottom: '20px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}>
                {this.state.error.toString()}
              </pre>
            )}
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={this.handleReload}
                style={{
                  background: '#2563eb',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px 18px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Reload Dashboard
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
