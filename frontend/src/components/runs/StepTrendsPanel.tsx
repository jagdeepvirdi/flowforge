import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronUp, TrendingUp } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { getStepRunTrends } from '../../lib/api'

// Styling constants mirrored from ChartPreview.tsx so every Recharts view in
// the app reads as one system.
const axisStyle = { fontSize: 11, fill: '#64748B' }
const gridStroke = 'rgba(255,255,255,0.06)'
const tipStyle = {
  contentStyle: { background: '#1A1D27', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 6, fontSize: 12 },
  labelStyle: { color: '#F1F5F9', fontWeight: 600 },
  itemStyle: { color: '#94A3B8' },
}
const DAY_WINDOWS = [7, 30, 90]

function fmtDur(ms: number | null | undefined): string {
  if (ms == null) return '—'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

/** Collapsible, lazy-loaded "duration over time" chart — surfaces gradual
 * slowdowns per step type before they cause timeouts. Aggregates the
 * step_runs data that's already collected for every step type; no new
 * data collection. */
export default function StepTrendsPanel({ pipelineId }: { pipelineId?: string }) {
  const [open, setOpen] = useState(false)
  const [stepType, setStepType] = useState('')
  const [days, setDays] = useState(30)

  const { data, isLoading } = useQuery({
    queryKey: ['step-run-trends', pipelineId, stepType, days],
    queryFn: () => getStepRunTrends({ pipeline_id: pipelineId || undefined, step_type: stepType || undefined, days }),
    enabled: open,
    staleTime: 60_000,
  })

  const totalRuns = data?.series.reduce((sum, p) => sum + p.run_count, 0) ?? 0
  const totalFailures = data?.series.reduce((sum, p) => sum + p.failure_count, 0) ?? 0

  return (
    <div style={{ marginBottom: 16 }}>
      <button
        onClick={() => setOpen(x => !x)}
        className="btn btn-sm"
        style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}
      >
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        <TrendingUp size={12} />
        Performance Trends
      </button>

      {open && (
        <div className="card" style={{ marginTop: 8, padding: 0, overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', padding: '10px 14px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Duration over time</span>
            <select
              className="btn btn-sm"
              value={stepType}
              onChange={e => setStepType(e.target.value)}
              style={{ cursor: 'pointer', marginLeft: 'auto' }}
            >
              <option value="">All step types</option>
              {(data?.available_step_types ?? []).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <div style={{ display: 'flex', gap: 1, background: 'var(--surface-2)', borderRadius: 7, padding: 2, border: '1px solid var(--border)' }}>
              {DAY_WINDOWS.map(d => (
                <button key={d} onClick={() => setDays(d)} style={{
                  background: days === d ? 'var(--surface)' : 'transparent',
                  border: 'none',
                  color: days === d ? 'var(--text)' : 'var(--text-muted)',
                  padding: '4px 10px',
                  borderRadius: 5,
                  fontSize: 11.5,
                  fontWeight: days === d ? 600 : 500,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}>{d}d</button>
              ))}
            </div>
          </div>

          {isLoading && (
            <div style={{ padding: '14px 16px', color: 'var(--text-muted)', fontSize: 12 }}>Loading trends…</div>
          )}

          {data && data.series.length === 0 && (
            <div style={{ padding: '14px 16px', color: 'var(--text-muted)', fontSize: 12 }}>
              No step runs in the last {days} days{stepType ? ` for step type "${stepType}"` : ''}.
            </div>
          )}

          {data && data.series.length > 0 && (
            <>
              <div style={{ padding: '20px 8px 4px', height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.series} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                    <XAxis dataKey="date" tick={axisStyle} axisLine={false} tickLine={false} />
                    <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={54} tickFormatter={v => fmtDur(v)} />
                    <Tooltip {...tipStyle} formatter={(value: number) => fmtDur(value)} />
                    <Legend wrapperStyle={{ fontSize: 11, color: '#94A3B8' }} />
                    <Line name="Avg duration" dataKey="avg_duration_ms" stroke="#F97316" strokeWidth={2} dot={false} activeDot={{ r: 4 }} connectNulls />
                    <Line name="p95 duration" dataKey="p95_duration_ms" stroke="#3B82F6" strokeWidth={2} strokeDasharray="4 3" dot={false} activeDot={{ r: 4 }} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div style={{ display: 'flex', gap: 16, padding: '8px 14px 12px', fontSize: 11, color: 'var(--text-muted)' }}>
                <span>{totalRuns} step run{totalRuns === 1 ? '' : 's'}</span>
                <span>{totalFailures} failure{totalFailures === 1 ? '' : 's'}</span>
                <span>Window: last {data.window_days} days</span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
