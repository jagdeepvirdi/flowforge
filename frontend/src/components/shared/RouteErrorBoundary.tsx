import { Component, type ReactNode } from 'react'

interface State { hasError: boolean; error: Error | null }

export default class RouteErrorBoundary extends Component<{ children: ReactNode }, State> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="scroll" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
          <div className="card" style={{ maxWidth: 420, width: '100%', padding: 24, textAlign: 'center' }}>
            <div style={{ fontSize: 28, marginBottom: 12, color: 'var(--failure)' }}>⚠</div>
            <h2 style={{ margin: '0 0 8px', fontSize: 16, color: 'var(--text)', fontWeight: 600 }}>
              Something went wrong
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '0 0 16px', lineHeight: 1.5 }}>
              {this.state.error?.message ?? 'An unexpected error occurred on this page.'}
            </p>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
