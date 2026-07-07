import { Component, type ReactNode } from 'react'

type Props = Readonly<{
  children: ReactNode
  /** Short label shown in the error card, e.g. "Step editor". Defaults to "This page". */
  label?: string
}>

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
      <div className="scroll flex justify-center items-center min-h-[300px]">
        <div className="card max-w-[460px] w-full p-6 text-center">
          <div className="text-[28px] mb-3 text-failure">⚠</div>
          <h2 className="m-0 mb-2 text-base text-text-primary font-semibold">
            Something went wrong
          </h2>
          <p className="text-text-muted text-[13px] m-0 mb-5 leading-normal">
            {label} encountered an unexpected error.
            {error?.message ? ` ${error.message}` : ''}
          </p>

          <div className="flex gap-2 justify-center mb-4">
            <button
              className="btn btn-primary btn-sm"
              onClick={() => globalThis.location.reload()}
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
            <div className="text-left">
              <button
                type="button"
                onClick={() => this.setState(s => ({ showDetail: !s.showDetail }))}
                className="bg-transparent border-none cursor-pointer text-text-dim text-[11.5px] font-[inherit] p-0 mb-1.5"
              >
                {showDetail ? '▾' : '▸'} Error details
              </button>
              {showDetail && (
                <pre className="m-0 py-2.5 px-3 bg-bg border border-border rounded-r-sm text-[10.5px] text-text-3 overflow-x-auto whitespace-pre-wrap break-words max-h-[200px] overflow-y-auto">
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
