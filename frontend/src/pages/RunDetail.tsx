import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, AlertTriangle, ChevronDown, ChevronUp, ExternalLink, CheckCircle, XCircle, Download, Lightbulb, X } from 'lucide-react'
import { getRun, downloadStepOutput, aiQuery, getSetupStatus, getRunAnomalies, getAnomalyNarrative, getRunDiff } from '../lib/api'
import type { StepRun, StepAnomaly, AnomalyMetric, StepDiff } from '../lib/types'
import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import Sk from '../components/shared/Skeleton'

function fmtDur(ms: number | null) {
  if (!ms) return '—'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`
}

const TYPE_META: Record<string, { cls: string; label: string }> = {
  db_procedure: { cls: 'tbadge-procedure', label: 'Proc' },
  db_query:     { cls: 'tbadge-query',     label: 'Query' },
  report:       { cls: 'tbadge-report',    label: 'Report' },
  email:        { cls: 'tbadge-email',     label: 'Email' },
  drive_upload: { cls: 'tbadge-drive',     label: 'Drive' },
}

const STATUS_TEXT_CLS: Record<string, string> = {
  success: 'text-success',
  failed:  'text-failure',
  running: 'text-running',
  skipped: 'text-text-dim',
}

const STATUS_BORDER_CLS: Record<string, string> = {
  success: 'border-success',
  failed:  'border-failure',
  running: 'border-running',
  skipped: 'border-text-dim',
}

const DURATION_TEXT_CLS: Record<string, string> = {
  success: 'text-success-text',
  running: 'text-running-text',
}

function AnomalyRow({ label, metric, a, aiEnabled, narrative, narrating, onNarrate, onDismiss }: {
  label: string; metric: 'rows' | 'duration'; a: AnomalyMetric
  aiEnabled: boolean
  narrative: string | null; narrating: boolean
  onNarrate: () => void; onDismiss: () => void
}) {
  const pctAbs = Math.abs(a.pct_diff)
  const dir    = a.pct_diff > 0 ? 'above' : 'below'
  const valStr  = metric === 'rows' ? `${a.value.toLocaleString()} rows` : fmtDur(a.value)
  const meanStr = metric === 'rows' ? `${Math.round(a.mean).toLocaleString()} rows` : fmtDur(Math.round(a.mean))
  return (
    <div className="flex flex-col gap-[5px]">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[11px] text-text-3 min-w-[52px] font-[inherit]">{label}</span>
        <span className="text-[11px] font-mono text-text-2">{valStr}</span>
        <span className="text-[10.5px] py-px px-1.5 rounded-[3px] bg-[rgba(249,115,22,0.1)] text-accent font-[inherit]">
          {pctAbs.toFixed(0)}% {dir} avg ({meanStr})
        </span>
        {aiEnabled && narrative === null && (
          <button
            onClick={onNarrate}
            disabled={narrating}
            className={`text-[10.5px] py-0.5 px-[7px] border border-[rgba(249,115,22,0.3)] bg-transparent text-accent rounded-[3px] font-[inherit] ${narrating ? 'cursor-default opacity-70' : 'cursor-pointer opacity-100'}`}
          >
            {narrating ? '…' : 'Why?'}
          </button>
        )}
      </div>
      {narrative !== null && (
        <div className="flex items-start gap-2 py-1.5 px-2.5 bg-[rgba(249,115,22,0.06)] border border-[rgba(249,115,22,0.15)] rounded-[5px]">
          <span className="text-[11.5px] text-text-2 leading-[1.65] flex-1 font-[inherit]">{narrative}</span>
          <button onClick={onDismiss} className="flex bg-transparent border-none cursor-pointer text-text-3 p-0 shrink-0"><X size={11} /></button>
        </div>
      )}
    </div>
  )
}

function StepStatusIcon({ status, stepOrder }: { status: string; stepOrder: number }) {
  if (status === 'success') return <CheckCircle size={12} />
  if (status === 'failed')  return <XCircle size={12} />
  if (status === 'running') return <span className="w-1.5 h-1.5 rounded-full bg-running animate-[ff-pulse_1.4s_infinite]" />
  return <span className="font-mono text-[10px] font-bold">{stepOrder}</span>
}

function StepLogsTab({ s, diagnosisPanel }: { s: StepRun; diagnosisPanel: React.ReactNode }) {
  return (
    <>
      {s.error_message && (
        <div className="mb-2.5">
          <div className="py-2 px-3 bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-r-sm text-failure-text whitespace-pre-wrap mb-1.5">
            {s.error_message}
          </div>
          {diagnosisPanel}
        </div>
      )}
      {s.logs
        ? <pre className="text-text-2 bg-bg m-0 whitespace-pre-wrap max-h-60 overflow-auto">{s.logs}</pre>
        : !s.error_message && <span className="text-text-dim">No logs for this step.</span>}
    </>
  )
}

function StepOutputTab({ s }: { s: StepRun }) {
  const [downloading, setDownloading] = useState(false)
  async function handleDownload() {
    if (!s.output_path) return
    setDownloading(true)
    try {
      const filename = s.output_path.split(/[\\/]/).pop() ?? 'output'
      await downloadStepOutput(s.id, filename)
    } finally {
      setDownloading(false)
    }
  }
  const hasOutput = s.output_path || s.drive_url || s.email_sent_to.length > 0 || s.rows_affected != null
  return (
    <>
      {s.output_path && (
        <div className="mb-2.5">
          <div className="text-text-muted text-[11px] mb-1.5">{s.output_path.split(/[\\/]/).pop()}</div>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className={`inline-flex items-center gap-1.5 py-1.5 px-3 rounded-r-sm border border-border-strong text-xs font-[inherit] ${downloading ? 'bg-surface text-text-dim cursor-default' : 'bg-surface2 text-text-primary cursor-pointer'}`}
          >
            <Download size={12} />
            {downloading ? 'Downloading…' : 'Download file'}
          </button>
        </div>
      )}
      {s.drive_url && (
        <a href={s.drive_url} target="_blank" rel="noreferrer" className="text-running-text inline-flex items-center gap-[5px] mb-1.5 text-xs">
          View in Drive <ExternalLink size={11} />
        </a>
      )}
      {s.email_sent_to.length > 0 && (
        <div className="text-text-3 mb-1.5">
          Sent to: {s.email_sent_to.map(addr => (
            <span key={addr} className="chip ml-1.5 h-5 text-[11px]">{addr}</span>
          ))}
        </div>
      )}
      {s.rows_affected != null && (
        <div className="text-text-3">Rows affected: <span className="text-text-2">{s.rows_affected.toLocaleString()}</span></div>
      )}
      {!hasOutput && <span className="text-text-dim">No output recorded.</span>}
    </>
  )
}

function StepInfoTab({ s }: { s: StepRun }) {
  return (
    <div className="flex flex-col gap-1.5 text-text-3">
      <div>Type: <span className="text-text-2">{s.step_type}</span></div>
      <div>Order: <span className="text-text-2">#{s.step_order}</span></div>
      <div>Status: <span className="text-text-2">{s.status}</span></div>
      <div>Started: <span className="text-text-2">{new Date(s.started_at).toLocaleTimeString()}</span></div>
      {s.finished_at && <div>Finished: <span className="text-text-2">{new Date(s.finished_at).toLocaleTimeString()}</span></div>}
      {s.duration_ms != null && <div>Duration: <span className="text-text-2">{s.duration_ms}ms</span></div>}
    </div>
  )
}

function DiagnosisPanel({ diagnosis, diagnosing, onDiagnose, onDismiss, aiEnabled }: {
  diagnosis: string | null; diagnosing: boolean; onDiagnose: () => void; onDismiss: () => void; aiEnabled: boolean
}) {
  if (diagnosis !== null) {
    return (
      <div className="py-2.5 px-3 bg-[rgba(249,115,22,0.06)] border border-[rgba(249,115,22,0.2)] rounded-r-sm">
        <div className="flex items-center justify-between mb-[7px]">
          <span className="text-[11px] font-semibold text-accent flex items-center gap-1 font-[inherit]">
            <Lightbulb size={11} /> AI Diagnosis
          </span>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-text-dim font-[inherit]">via Ollama</span>
            <button onClick={onDismiss} className="flex bg-transparent border-none cursor-pointer text-text-3 p-0">
              <X size={12} />
            </button>
          </div>
        </div>
        <div className="text-xs text-text-2 leading-[1.7] whitespace-pre-wrap font-[inherit]">
          {diagnosis}
        </div>
      </div>
    )
  }
  if (aiEnabled) {
    return (
      <button
        onClick={onDiagnose}
        disabled={diagnosing}
        className={`inline-flex items-center gap-[5px] text-[11px] py-[3px] px-[9px] rounded border border-[rgba(249,115,22,0.3)] bg-[rgba(249,115,22,0.06)] text-accent font-[inherit] ${diagnosing ? 'cursor-default opacity-70' : 'cursor-pointer opacity-100'}`}
      >
        <Lightbulb size={11} />
        {diagnosing ? 'Diagnosing…' : 'Explain this error'}
      </button>
    )
  }
  return null
}

function AnomalyPanel({ anomaly, aiEnabled, rowsNarrative, rowsNarrating, durNarrative, durNarrating, onNarrate, onDismissNarrative }: {
  anomaly: StepAnomaly; aiEnabled: boolean
  rowsNarrative: string | null; rowsNarrating: boolean
  durNarrative: string | null; durNarrating: boolean
  onNarrate: (metric: 'rows' | 'duration', a: AnomalyMetric) => void
  onDismissNarrative: (metric: 'rows' | 'duration') => void
}) {
  return (
    <div className="py-2.5 px-4 border-b border-border bg-[rgba(249,115,22,0.03)] flex flex-col gap-2.5">
      <div className="flex items-center gap-1.5">
        <AlertTriangle size={12} className="text-accent" />
        <span className="text-[11px] font-semibold text-accent font-[inherit]">Anomaly Detected</span>
        <span className="text-[10.5px] text-text-dim font-[inherit]">— this step result is &gt;2σ outside its 30-run average</span>
      </div>
      {anomaly.rows_anomaly && (
        <AnomalyRow
          label="Rows" metric="rows" a={anomaly.rows_anomaly}
          aiEnabled={aiEnabled}
          narrative={rowsNarrative} narrating={rowsNarrating}
          onNarrate={() => onNarrate('rows', anomaly.rows_anomaly!)}
          onDismiss={() => onDismissNarrative('rows')}
        />
      )}
      {anomaly.duration_anomaly && (
        <AnomalyRow
          label="Duration" metric="duration" a={anomaly.duration_anomaly}
          aiEnabled={aiEnabled}
          narrative={durNarrative} narrating={durNarrating}
          onNarrate={() => onNarrate('duration', anomaly.duration_anomaly!)}
          onDismiss={() => onDismissNarrative('duration')}
        />
      )}
    </div>
  )
}

function TimelineStep({ s, last, aiEnabled, anomaly }: { s: StepRun; last: boolean; aiEnabled: boolean; anomaly: StepAnomaly | null }) {
  const [open, setOpen]           = useState(s.status === 'failed' || !!anomaly)
  const [activeTab, setActiveTab] = useState(0)
  const [diagnosis, setDiagnosis] = useState<string | null>(null)
  const [diagnosing, setDiagnosing] = useState(false)
  const [rowsNarrative, setRowsNarrative] = useState<string | null>(null)
  const [rowsNarrating, setRowsNarrating] = useState(false)
  const [durNarrative, setDurNarrative]   = useState<string | null>(null)
  const [durNarrating, setDurNarrating]   = useState(false)

  async function handleNarrate(metric: 'rows' | 'duration', a: AnomalyMetric) {
    const setNarrative = metric === 'rows' ? setRowsNarrative : setDurNarrative
    const setNarrating = metric === 'rows' ? setRowsNarrating : setDurNarrating
    setNarrating(true)
    try {
      const { result } = await getAnomalyNarrative({ step_name: s.step_name, metric, value: a.value, mean: a.mean, pct_diff: a.pct_diff })
      setNarrative(result)
    } catch {
      setNarrative('Could not reach Ollama. Is it running?')
    } finally {
      setNarrating(false)
    }
  }

  async function handleDiagnose() {
    if (!s.error_message) return
    setDiagnosing(true)
    try {
      const { result } = await aiQuery({ task: 'diagnose', step_type: s.step_type, error: s.error_message, logs: s.logs })
      setDiagnosis(result)
    } catch {
      setDiagnosis('Could not reach Ollama. Is it running?')
    } finally {
      setDiagnosing(false)
    }
  }

  const typeMeta = TYPE_META[s.step_type] ?? { cls: 'tbadge-query', label: s.step_type }
  const statusTextCls = STATUS_TEXT_CLS[s.status] ?? 'text-text-dim'
  const statusBorderCls = STATUS_BORDER_CLS[s.status] ?? 'border-text-dim'
  const durationCls = DURATION_TEXT_CLS[s.status] ?? 'text-text-dim'

  const diagnosisPanel = (
    <DiagnosisPanel
      diagnosis={diagnosis}
      diagnosing={diagnosing}
      onDiagnose={handleDiagnose}
      onDismiss={() => setDiagnosis(null)}
      aiEnabled={aiEnabled}
    />
  )

  return (
    <div className="flex gap-3.5 relative">
      {/* Rail */}
      <div className="flex flex-col items-center shrink-0 w-6 pt-3.5">
        <div className={`w-6 h-6 rounded-full bg-surface border-2 ${statusBorderCls} flex items-center justify-center ${statusTextCls} relative z-[1] ${s.status === 'running' ? 'shadow-[0_0_0_4px_rgba(59,130,246,0.15)]' : ''}`}>
          <StepStatusIcon status={s.status} stepOrder={s.step_order} />
        </div>
        {!last && <div className="flex-1 w-0.5 bg-border mt-0.5" />}
      </div>

      {/* Card */}
      <div className={`flex-1 mb-1.5 rounded-[10px] overflow-hidden border ${open ? 'bg-surface border-border-strong' : 'bg-bg-code border-border'}${s.status === 'skipped' ? ' opacity-50' : ''}`}>
        <button
          onClick={() => setOpen(x => !x)}
          className="w-full bg-transparent border-none cursor-pointer flex items-center gap-3 py-3 px-4 text-left"
        >
          <span className={`tbadge ${typeMeta.cls}`}>{typeMeta.label}</span>
          <span className="mono text-[13px] font-medium text-text-primary">{s.step_name}</span>
          <span className="flex-1 text-[11.5px] text-text-muted flex items-center gap-3">
            {s.rows_affected != null && <span>{s.rows_affected.toLocaleString()} rows</span>}
            {anomaly && <span title="Statistical anomaly detected" className="inline-flex items-center gap-[3px] text-accent"><AlertTriangle size={12} /> anomaly</span>}
          </span>
          <span className={`mono text-[11.5px] ${durationCls} min-w-[50px] text-right`}>
            {fmtDur(s.duration_ms)}
          </span>
          {open ? <ChevronUp size={14} className="text-text-muted" /> : <ChevronDown size={14} className="text-text-muted" />}
        </button>

        {open && (
          <div className="border-t border-border bg-bg">
            {/* Anomaly panel */}
            {anomaly && (
              <AnomalyPanel
                anomaly={anomaly}
                aiEnabled={aiEnabled}
                rowsNarrative={rowsNarrative}
                rowsNarrating={rowsNarrating}
                durNarrative={durNarrative}
                durNarrating={durNarrating}
                onNarrate={handleNarrate}
                onDismissNarrative={(m) => m === 'rows' ? setRowsNarrative(null) : setDurNarrative(null)}
              />
            )}
            {/* Tabs */}
            <div className="flex items-center border-b border-border px-4">
              {['Logs', 'Output', 'Info'].map((t, i) => (
                <button key={t} onClick={() => setActiveTab(i)} className={`bg-transparent border-none py-[9px] px-3.5 text-xs cursor-pointer font-[inherit] border-b-2 ${activeTab === i ? 'text-accent font-semibold border-b-accent' : 'text-text-muted font-medium border-b-transparent'}`}>{t}</button>
              ))}
            </div>

            {/* Content */}
            <div className="py-3 px-4 font-mono text-[11.5px] leading-[1.7]">
              {activeTab === 0 && <StepLogsTab s={s} diagnosisPanel={diagnosisPanel} />}
              {activeTab === 1 && <StepOutputTab s={s} />}
              {activeTab === 2 && <StepInfoTab s={s} />}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function fmtBytes(n: number): string {
  if (n < 1024)           return `${n} B`
  if (n < 1024 * 1024)    return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

function DeltaBadge({ delta, unit, pct }: { delta: number | null; unit?: string; pct?: boolean }) {
  if (delta === null || delta === undefined) return <span className="text-text-dim">—</span>
  const up    = delta > 0
  const zero  = delta === 0
  const colorCls = zero ? 'text-text-muted' : up ? 'text-failure-text' : 'text-success-text'
  const label = zero ? '±0' : `${up ? '+' : ''}${pct ? `${delta}%` : `${delta.toLocaleString()}${unit ? ' ' + unit : ''}`}`
  return <span className={`${colorCls} text-[11px] font-mono`}>{label}</span>
}

function DiffPanel({ runId, prevRunId }: { runId: string; prevRunId: string | null }) {
  const [open, setOpen] = useState(false)
  const { data: diff, isLoading } = useQuery({
    queryKey: ['run-diff', runId],
    queryFn:  () => getRunDiff(runId),
    enabled:  open,
    staleTime: 300_000,
  })

  if (prevRunId === null && !isLoading && diff) return null

  return (
    <div className="mb-4">
      <button
        onClick={() => setOpen(x => !x)}
        className="btn btn-sm flex items-center gap-1.5 text-xs"
      >
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        Diff vs previous run
      </button>

      {open && (
        <div className="card mt-2 p-0 overflow-hidden">
          {isLoading && (
            <div className="py-3.5 px-4 text-text-muted text-xs">Loading diff…</div>
          )}
          {diff && !diff.prev_run_id && (
            <div className="py-3.5 px-4 text-text-muted text-xs">
              No previous successful run found — nothing to compare.
            </div>
          )}
          {diff && diff.prev_run_id && diff.steps.length > 0 && (
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr className="border-b border-border">
                  {['Step', 'Rows', 'Δ Rows', 'Duration', 'Δ Duration', 'File size', 'Δ Size'].map(h => (
                    <th key={h} className="py-2 px-3 text-left text-[11px] font-semibold text-text-muted uppercase tracking-[0.04em]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {diff.steps.map((s: StepDiff, i: number) => (
                  <tr key={s.step_name} className={`${i < diff.steps.length - 1 ? 'border-b border-border' : ''} ${s.is_new_step ? 'bg-[rgba(99,102,241,0.04)]' : 'bg-transparent'}`}>
                    <td className="py-2 px-3 text-text-primary font-medium">
                      {s.step_name}
                      {s.is_new_step && <span className="ml-1.5 text-[10px] py-px px-[5px] rounded-[3px] bg-[rgba(99,102,241,0.15)] text-indigo-400">new</span>}
                    </td>
                    <td className="py-2 px-3 text-text-muted font-mono">
                      {s.rows_current != null ? s.rows_current.toLocaleString() : '—'}
                    </td>
                    <td className="py-2 px-3">
                      <DeltaBadge delta={s.rows_delta} />
                    </td>
                    <td className="py-2 px-3 text-text-muted font-mono">
                      {s.duration_current != null ? fmtDur(s.duration_current) : '—'}
                    </td>
                    <td className="py-2 px-3">
                      <DeltaBadge delta={s.duration_delta_pct} pct />
                    </td>
                    <td className="py-2 px-3 text-text-muted font-mono">
                      {s.size_current != null ? fmtBytes(s.size_current) : '—'}
                    </td>
                    <td className="py-2 px-3">
                      <DeltaBadge delta={s.size_delta} unit="B" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}

export default function RunDetail() {
  const { id } = useParams()
  const { data: run, isLoading } = useQuery({
    queryKey: ['run', id],
    queryFn: () => getRun(id!),
    refetchInterval: (q) => q.state.data?.status === 'running' ? 3000 : false,
  })
  const { data: setupStatus } = useQuery({ queryKey: ['setup-status'], queryFn: getSetupStatus, staleTime: 60_000 })
  const aiEnabled = setupStatus?.ai?.enabled ?? true
  const { data: anomalies = [] } = useQuery({
    queryKey: ['run-anomalies', id],
    queryFn: () => getRunAnomalies(id!),
    enabled: !!id && !!run && run.status !== 'running',
    staleTime: 300_000,
  })
  const anomalyMap = new Map(anomalies.map(a => [a.step_id, a]))

  // Pre-fetch prev_run_id so the DiffPanel button knows whether to show
  const { data: diffMeta } = useQuery({
    queryKey: ['run-diff-meta', id],
    queryFn:  () => getRunDiff(id!),
    enabled:  !!id && !!run && run.status !== 'running',
    staleTime: 300_000,
  })

  if (isLoading || !run) return (
    <>
      <TopBar crumbs={['Workspace', 'Run History', '…']} />
      <div className="scroll">
        <div className="flex items-start justify-between gap-4 mb-[18px]">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2.5">
              <Sk h={22} r={6} style={{ width: 220 }} />
              <Sk h={18} r={4} style={{ width: 60 }} />
            </div>
            <Sk h={12} style={{ width: 320 }} />
          </div>
        </div>
        <div className="grid grid-cols-4 gap-3 mb-[18px]">
          {[0, 1, 2, 3].map(i => (
            <div key={i} className="card py-3.5 px-4">
              <Sk h={11} style={{ width: 55, marginBottom: 8 }} />
              <Sk h={18} style={{ width: 70 }} />
            </div>
          ))}
        </div>
        <Sk h={6} r={4} style={{ marginBottom: 20 }} />
        <div className="flex flex-col gap-2.5">
          {[0, 1, 2].map(i => (
            <div key={i} className="card py-3.5 px-4 flex items-center gap-3">
              <Sk h={20} r={4} style={{ width: 60 }} />
              <Sk h={14} style={{ width: '35%' }} />
              <Sk h={12} style={{ width: 80, marginLeft: 'auto' }} />
            </div>
          ))}
        </div>
      </div>
    </>
  )

  const steps = run.step_runs ?? []

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Run History', run.pipeline_name, run.id.slice(0, 12)]}
        actions={
          <div className="flex gap-2">
            <button className="btn btn-sm" onClick={() => {
              const lines = (run.step_runs ?? []).map(s =>
                `[${s.step_order}] ${s.step_name} (${s.status})\n${s.logs ?? ''}${s.error_message ? '\nERROR: ' + s.error_message : ''}`
              ).join('\n\n---\n\n')
              const blob = new Blob([`Run: ${run.pipeline_name}\nID: ${run.id}\nStarted: ${run.started_at}\n\n${lines}`], { type: 'text/plain' })
              const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
              a.download = `run-${run.id.slice(0, 8)}.txt`; a.click()
            }}><Download size={12} /> Export logs</button>
            <Link to="/runs" className="btn btn-sm"><ArrowLeft size={12} /> Back</Link>
          </div>
        }
      />

      <div className="scroll">
        {/* Run header */}
        <div className="flex items-start justify-between gap-4 mb-[18px]">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <h1 className="text-[22px] font-semibold tracking-[-0.02em] m-0 text-text-primary">{run.pipeline_name}</h1>
              <StatusBadge status={run.status} animate />
            </div>
            <div className="flex items-center gap-3.5 text-xs text-text-muted flex-wrap">
              <span className="mono">{run.id}</span>
              <span>·</span>
              <span>Started <span className="text-text-2">{new Date(run.started_at).toLocaleString()}</span></span>
              <span>·</span>
              <span>Triggered by <span className="text-text-2">{run.triggered_by}</span></span>
            </div>
          </div>
        </div>

        {/* Stats strip */}
        <div className="grid grid-cols-4 gap-3 mb-[18px]">
          {[
            { label: 'Duration',  value: fmtDur(run.duration_ms),       mono: true },
            { label: 'Steps',     value: `${steps.filter(s => s.status === 'success').length} / ${steps.length}`, mono: true },
            { label: 'Started',   value: new Date(run.started_at).toLocaleTimeString(), mono: true },
            { label: 'Trigger',   value: run.triggered_by,              mono: false },
          ].map(s => (
            <div key={s.label} className="card py-3.5 px-4">
              <div className="text-[11px] text-text-muted uppercase tracking-[0.04em] font-semibold mb-1.5">{s.label}</div>
              <div className={`${s.mono ? 'mono' : ''} text-lg font-semibold text-text-primary ${s.mono ? 'tracking-[-0.02em]' : 'tracking-normal'}`}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* Progress bar */}
        <div className="mb-5">
          <div className="flex gap-0.5 h-1.5 rounded overflow-hidden bg-surface2">
            {steps.map(s => {
              const barCls = s.status === 'success' ? 'bg-success'
                : s.status === 'running' ? 'bg-[linear-gradient(90deg,var(--running),var(--running-text))]'
                : (s.status === 'failed' ? 'bg-failure' : 'bg-surface2')
              return (
                <div
                  key={s.id}
                  className={`relative overflow-hidden ${barCls}`}
                  style={{ flex: s.status === 'success' || s.status === 'running' ? (s.duration_ms ?? 1) : 1 }}
                >
                  {s.status === 'running' && (
                    <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.3),transparent)] animate-[shimmer_1.6s_infinite]" />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Diff vs previous run */}
        {run.status !== 'running' && (
          <DiffPanel runId={run.id} prevRunId={diffMeta?.prev_run_id ?? null} />
        )}

        {/* Error banner */}
        {run.error_message && (
          <div className="mb-4 py-2.5 px-3.5 bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-r text-[12.5px] text-failure-text">
            <strong className="text-failure-text">Failed at step:</strong> {run.error_step}<br />
            {run.error_message}
          </div>
        )}

        {/* Timeline */}
        <div className="flex flex-col pb-5">
          {steps.map((s, i) => <TimelineStep key={s.id} s={s} last={i === steps.length - 1} aiEnabled={aiEnabled} anomaly={anomalyMap.get(s.id) ?? null} />)}
        </div>
      </div>
    </>
  )
}
