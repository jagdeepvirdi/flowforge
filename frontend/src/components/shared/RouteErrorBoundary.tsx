import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** Short label shown in the error card, e.g. "Step editor". Defaults to "This page". */
  label?: string
}

interface State {
  hasError: boolean
  error: Error | null
  showDetail: boolean
}

export default class RouteErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, showDetail: false }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    const { label = 'This page' } = this.props
    const { error, showDetail } = this.state

    return (
      <div className="scroll" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
        <div className="card" style={{ maxWidth: 460, width: '100%', padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 28, marginBottom: 12, color: 'var(--failure)' }}>⚠</div>
          <h2 style={{ margin: '0 0 8px', fontSize: 16, color: 'var(--text)', fontWeight: 600 }}>
            Something went wrong
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '0 0 20px', lineHeight: 1.5 }}>
            {label} encountered an unexpected error.
            {error?.message ? ` ${error.message}` : ''}
          </p>

          <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 16 }}>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => window.location.reload()}
            >
              Reload page
            </button>
            <button
              className="btn btn-sm"
              onClick={() => this.setState({ hasError: false, error: null, showDetail: false })}
            >
              Try again
            </button>
          </div>

          {error?.stack && (
            <div style={{ textAlign: 'left' }}>
              <button
                type="button"
                onClick={() => this.setState(s => ({ showDetail: !s.showDetail }))}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--text-dim)', fontSize: 11.5, fontFamily: 'inherit',
                  padding: 0, marginBottom: 6,
                }}
              >
                {showDetail ? '▾' : '▸'} Error details
              </button>
              {showDetail && (
                <pre style={{
                  margin: 0, padding: '10px 12px',
                  background: 'var(--bg)', border: '1px solid var(--border)',
                  borderRadius: 6, fontSize: 10.5, color: 'var(--text-3)',
                  overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                  maxHeight: 200, overflowY: 'auto',
                }}>
                  {error.stack}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }
}
