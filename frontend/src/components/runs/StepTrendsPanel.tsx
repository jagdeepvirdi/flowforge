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
    <div className="mb-4">
      <button
        onClick={() => setOpen(x => !x)}
        className="btn btn-sm flex items-center gap-1.5 text-xs"
      >
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        <TrendingUp size={12} />
        Performance Trends
      </button>

      {open && (
        <div className="card mt-2 !p-0 overflow-hidden">
          <div className="flex items-center gap-2.5 flex-wrap py-2.5 px-3.5 border-b border-border">
            <span className="text-xs font-semibold text-text-primary">Duration over time</span>
            <select
              className="btn btn-sm cursor-pointer ml-auto"
              value={stepType}
              onChange={e => setStepType(e.target.value)}
            >
              <option value="">All step types</option>
              {(data?.available_step_types ?? []).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <div className="flex gap-px bg-surface2 rounded-[7px] p-0.5 border border-border">
              {DAY_WINDOWS.map(d => (
                <button key={d} onClick={() => setDays(d)} className={`border-none py-1 px-2.5 rounded-[5px] text-[11.5px] cursor-pointer font-[inherit] ${days === d ? 'bg-surface text-text-primary font-semibold' : 'bg-transparent text-text-muted font-medium'}`}>{d}d</button>
              ))}
            </div>
          </div>

          {isLoading && (
            <div className="py-3.5 px-4 text-text-muted text-xs">Loading trends…</div>
          )}

          {data && data.series.length === 0 && (
            <div className="py-3.5 px-4 text-text-muted text-xs">
              No step runs in the last {days} days{stepType ? ` for step type "${stepType}"` : ''}.
            </div>
          )}

          {data && data.series.length > 0 && (
            <>
              <div className="pt-5 px-2 pb-1 h-[260px]">
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
              <div className="flex gap-4 pt-2 px-3.5 pb-3 text-[11px] text-text-muted">
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
