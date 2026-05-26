import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, AlertTriangle, ChevronDown, ChevronUp, ExternalLink, CheckCircle, XCircle, Download, Lightbulb, X } from 'lucide-react'
import { getRun, downloadStepOutput, aiQuery, getSetupStatus, getRunAnomalies, getAnomalyNarrative } from '../lib/api'
import type { StepRun, StepAnomaly, AnomalyMetric } from '../lib/types'
import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'

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

const STATUS_COLOR: Record<string, string> = {
  success: 'var(--success)',
  failed:  'var(--failure)',
  running: 'var(--running)',
  skipped: 'var(--text-dim)',
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: 'var(--text-3)', minWidth: 52, fontFamily: 'inherit' }}>{label}</span>
        <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-2)' }}>{valStr}</span>
        <span style={{ fontSize: 10.5, padding: '1px 6px', borderRadius: 3, background: 'rgba(249,115,22,0.1)', color: '#F97316', fontFamily: 'inherit' }}>
          {pctAbs.toFixed(0)}% {dir} avg ({meanStr})
        </span>
        {aiEnabled && narrative === null && (
          <button
            onClick={onNarrate}
            disabled={narrating}
            style={{ fontSize: 10.5, padding: '2px 7px', border: '1px solid rgba(249,115,22,0.3)', background: 'transparent', color: '#F97316', borderRadius: 3, cursor: narrating ? 'default' : 'pointer', opacity: narrating ? 0.7 : 1, fontFamily: 'inherit' }}
          >
            {narrating ? '…' : 'Why?'}
          </button>
        )}
      </div>
      {narrative !== null && (
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '6px 10px', background: 'rgba(249,115,22,0.06)', border: '1px solid rgba(249,115,22,0.15)', borderRadius: 5 }}>
          <span style={{ fontSize: 11.5, color: 'var(--text-2)', lineHeight: 1.65, flex: 1, fontFamily: 'inherit' }}>{narrative}</span>
          <button onClick={onDismiss} style={{ display: 'flex', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', padding: 0, flexShrink: 0 }}><X size={11} /></button>
        </div>
      )}
    </div>
  )
}

function StepStatusIcon({ status, stepOrder, statusColor }: { status: string; stepOrder: number; statusColor: string }) {
  if (status === 'success') return <CheckCircle size={12} />
  if (status === 'failed')  return <XCircle size={12} />
  if (status === 'running') return <span style={{ width: 6, height: 6, borderRadius: '50%', background: statusColor, animation: 'ff-pulse 1.4s infinite' }} />
  return <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fontWeight: 700 }}>{stepOrder}</span>
}

function StepLogsTab({ s, diagnosisPanel }: { s: StepRun; diagnosisPanel: React.ReactNode }) {
  return (
    <>
      {s.error_message && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ padding: '8px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, color: 'var(--failure-text)', whiteSpace: 'pre-wrap', marginBottom: 6 }}>
            {s.error_message}
          </div>
          {diagnosisPanel}
        </div>
      )}
      {s.logs
        ? <pre style={{ color: 'var(--text-2)', background: 'var(--bg)', margin: 0, whiteSpace: 'pre-wrap', maxHeight: 240, overflow: 'auto' }}>{s.logs}</pre>
        : !s.error_message && <span style={{ color: 'var(--text-dim)' }}>No logs for this step.</span>}
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
        <div style={{ marginBottom: 10 }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 6 }}>{s.output_path.split(/[\\/]/).pop()}</div>
          <button
            onClick={handleDownload}
            disabled={downloading}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '6px 12px', borderRadius: 6, border: '1px solid var(--border-strong)',
              background: downloading ? 'var(--surface)' : 'var(--surface-2)',
              color: downloading ? 'var(--text-dim)' : 'var(--text)',
              fontSize: 12, cursor: downloading ? 'default' : 'pointer', fontFamily: 'inherit',
            }}
          >
            <Download size={12} />
            {downloading ? 'Downloading…' : 'Download file'}
          </button>
        </div>
      )}
      {s.drive_url && (
        <a href={s.drive_url} target="_blank" rel="noreferrer" style={{ color: 'var(--running-text)', display: 'inline-flex', alignItems: 'center', gap: 5, marginBottom: 6, fontSize: 12 }}>
          View in Drive <ExternalLink size={11} />
        </a>
      )}
      {s.email_sent_to.length > 0 && (
        <div style={{ color: 'var(--text-3)', marginBottom: 6 }}>
          Sent to: {s.email_sent_to.map(addr => (
            <span key={addr} className="chip" style={{ marginLeft: 6, height: 20, fontSize: 11 }}>{addr}</span>
          ))}
        </div>
      )}
      {s.rows_affected != null && (
        <div style={{ color: 'var(--text-3)' }}>Rows affected: <span style={{ color: 'var(--text-2)' }}>{s.rows_affected.toLocaleString()}</span></div>
      )}
      {!hasOutput && <span style={{ color: 'var(--text-dim)' }}>No output recorded.</span>}
    </>
  )
}

function StepInfoTab({ s }: { s: StepRun }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, color: 'var(--text-3)' }}>
      <div>Type: <span style={{ color: 'var(--text-2)' }}>{s.step_type}</span></div>
      <div>Order: <span style={{ color: 'var(--text-2)' }}>#{s.step_order}</span></div>
      <div>Status: <span style={{ color: 'var(--text-2)' }}>{s.status}</span></div>
      <div>Started: <span style={{ color: 'var(--text-2)' }}>{new Date(s.started_at).toLocaleTimeString()}</span></div>
      {s.finished_at && <div>Finished: <span style={{ color: 'var(--text-2)' }}>{new Date(s.finished_at).toLocaleTimeString()}</span></div>}
      {s.duration_ms != null && <div>Duration: <span style={{ color: 'var(--text-2)' }}>{s.duration_ms}ms</span></div>}
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
  const statusColor = STATUS_COLOR[s.status] ?? 'var(--text-dim)'
  const durationColor = s.status === 'success' ? 'var(--success-text)' : (s.status === 'running' ? 'var(--running-text)' : 'var(--text-dim)')

  const diagnosisPanelResult = diagnosis !== null ? (
    <div style={{ padding: '10px 12px', background: 'rgba(249,115,22,0.06)', border: '1px solid rgba(249,115,22,0.2)', borderRadius: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 7 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: '#F97316', display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'inherit' }}>
          <Lightbulb size={11} /> AI Diagnosis
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'inherit' }}>via Ollama</span>
          <button onClick={() => setDiagnosis(null)} style={{ display: 'flex', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', padding: 0 }}>
            <X size={12} />
          </button>
        </div>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.7, whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
        {diagnosis}
      </div>
    </div>
  ) : null
  const diagnosisPanel = diagnosisPanelResult ?? (aiEnabled ? (
    <button
      onClick={handleDiagnose}
      disabled={diagnosing}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, padding: '3px 9px', borderRadius: 4, border: '1px solid rgba(249,115,22,0.3)', background: 'rgba(249,115,22,0.06)', color: '#F97316', cursor: diagnosing ? 'default' : 'pointer', fontFamily: 'inherit', opacity: diagnosing ? 0.7 : 1 }}
    >
      <Lightbulb size={11} />
      {diagnosing ? 'Diagnosing…' : 'Explain this error'}
    </button>
  ) : null)

  return (
    <div style={{ display: 'flex', gap: 14, position: 'relative' }}>
      {/* Rail */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0, width: 24, paddingTop: 14 }}>
        <div style={{
          width: 24, height: 24, borderRadius: '50%',
          background: 'var(--surface)',
          border: `2px solid ${statusColor}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: statusColor,
          position: 'relative',
          zIndex: 1,
          boxShadow: s.status === 'running' ? `0 0 0 4px rgba(59,130,246,0.15)` : 'none',
        }}>
          <StepStatusIcon status={s.status} stepOrder={s.step_order} statusColor={statusColor} />
        </div>
        {!last && <div style={{ flex: 1, width: 2, background: 'var(--border)', marginTop: 2 }} />}
      </div>

      {/* Card */}
      <div style={{
        flex: 1, marginBottom: 6,
        background: open ? 'var(--surface)' : 'var(--bg-code)',
        border: `1px solid ${open ? 'var(--border-strong)' : 'var(--border)'}`,
        borderRadius: 10,
        overflow: 'hidden',
        opacity: s.status === 'skipped' ? 0.5 : 1,
      }}>
        <button
          onClick={() => setOpen(x => !x)}
          style={{ width: '100%', background: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', textAlign: 'left' }}
        >
          <span className={`tbadge ${typeMeta.cls}`}>{typeMeta.label}</span>
          <span className="mono" style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)' }}>{s.step_name}</span>
          <span style={{ flex: 1, fontSize: 11.5, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 12 }}>
            {s.rows_affected != null && <span>{s.rows_affected.toLocaleString()} rows</span>}
            {anomaly && <span title="Statistical anomaly detected" style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color: '#F97316' }}><AlertTriangle size={12} /> anomaly</span>}
          </span>
          <span className="mono" style={{ fontSize: 11.5, color: durationColor, minWidth: 50, textAlign: 'right' }}>
            {fmtDur(s.duration_ms)}
          </span>
          {open ? <ChevronUp size={14} style={{ color: 'var(--text-muted)' }} /> : <ChevronDown size={14} style={{ color: 'var(--text-muted)' }} />}
        </button>

        {open && (
          <div style={{ borderTop: '1px solid var(--border)', background: 'var(--bg)' }}>
            {/* Anomaly panel */}
            {anomaly && (
              <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)', background: 'rgba(249,115,22,0.03)', display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <AlertTriangle size={12} style={{ color: '#F97316' }} />
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#F97316', fontFamily: 'inherit' }}>Anomaly Detected</span>
                  <span style={{ fontSize: 10.5, color: 'var(--text-dim)', fontFamily: 'inherit' }}>— this step result is &gt;2σ outside its 30-run average</span>
                </div>
                {anomaly.rows_anomaly && (
                  <AnomalyRow
                    label="Rows" metric="rows" a={anomaly.rows_anomaly}
                    aiEnabled={aiEnabled}
                    narrative={rowsNarrative} narrating={rowsNarrating}
                    onNarrate={() => handleNarrate('rows', anomaly.rows_anomaly!)}
                    onDismiss={() => setRowsNarrative(null)}
                  />
                )}
                {anomaly.duration_anomaly && (
                  <AnomalyRow
                    label="Duration" metric="duration" a={anomaly.duration_anomaly}
                    aiEnabled={aiEnabled}
                    narrative={durNarrative} narrating={durNarrating}
                    onNarrate={() => handleNarrate('duration', anomaly.duration_anomaly!)}
                    onDismiss={() => setDurNarrative(null)}
                  />
                )}
              </div>
            )}
            {/* Tabs */}
            <div style={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid var(--border)', padding: '0 16px' }}>
              {['Logs', 'Output', 'Info'].map((t, i) => (
                <button key={t} onClick={() => setActiveTab(i)} style={{
                  background: 'transparent', border: 'none',
                  color: activeTab === i ? 'var(--accent)' : 'var(--text-muted)',
                  padding: '9px 14px', fontSize: 12,
                  fontWeight: activeTab === i ? 600 : 500,
                  cursor: 'pointer',
                  borderBottom: activeTab === i ? '2px solid var(--accent)' : '2px solid transparent',
                  fontFamily: 'inherit',
                }}>{t}</button>
              ))}
            </div>

            {/* Content */}
            <div style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5, lineHeight: 1.7 }}>
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

  if (isLoading || !run) return (
    <><TopBar crumbs={['Workspace', 'Run History', '…']} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
  )

  const steps = run.step_runs ?? []

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Run History', run.pipeline_name, run.id.slice(0, 12)]}
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
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
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <h1 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', margin: 0, color: 'var(--text)' }}>{run.pipeline_name}</h1>
              <StatusBadge status={run.status} animate />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 12, color: 'var(--text-muted)', flexWrap: 'wrap' }}>
              <span className="mono">{run.id}</span>
              <span>·</span>
              <span>Started <span style={{ color: 'var(--text-2)' }}>{new Date(run.started_at).toLocaleString()}</span></span>
              <span>·</span>
              <span>Triggered by <span style={{ color: 'var(--text-2)' }}>{run.triggered_by}</span></span>
            </div>
          </div>
        </div>

        {/* Stats strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 18 }}>
          {[
            { label: 'Duration',  value: fmtDur(run.duration_ms),       mono: true },
            { label: 'Steps',     value: `${steps.filter(s => s.status === 'success').length} / ${steps.length}`, mono: true },
            { label: 'Started',   value: new Date(run.started_at).toLocaleTimeString(), mono: true },
            { label: 'Trigger',   value: run.triggered_by,              mono: false },
          ].map(s => (
            <div key={s.label} className="card" style={{ padding: '14px 16px' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600, marginBottom: 6 }}>{s.label}</div>
              <div className={s.mono ? 'mono' : ''} style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)', letterSpacing: s.mono ? '-0.02em' : 'normal' }}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* Progress bar */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 2, height: 6, borderRadius: 4, overflow: 'hidden', background: 'var(--surface-2)' }}>
            {steps.map((s, i) => {
              const barBackground = s.status === 'success' ? 'var(--success)'
                : s.status === 'running' ? 'linear-gradient(90deg,var(--running),var(--running-text))'
                : (s.status === 'failed' ? 'var(--failure)' : 'var(--surface-2)')
              return (
                <div key={i} style={{
                  flex: s.status === 'success' || s.status === 'running' ? (s.duration_ms ?? 1) : 1,
                  background: barBackground,
                  position: 'relative',
                  overflow: 'hidden',
                }}>
                  {s.status === 'running' && (
                    <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(90deg,transparent,rgba(255,255,255,0.3),transparent)', animation: 'shimmer 1.6s infinite' }} />
                  )}
                </div>
              )
            })}
          </div>
          <style>{`@keyframes shimmer { 0% { transform:translateX(-100%); } 100% { transform:translateX(100%); } }`}</style>
        </div>

        {/* Error banner */}
        {run.error_message && (
          <div style={{ marginBottom: 16, padding: '10px 14px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 8, fontSize: 12.5, color: 'var(--failure-text)' }}>
            <strong style={{ color: 'var(--failure-text)' }}>Failed at step:</strong> {run.error_step}<br />
            {run.error_message}
          </div>
        )}

        {/* Timeline */}
        <div style={{ display: 'flex', flexDirection: 'column', paddingBottom: 20 }}>
          {steps.map((s, i) => <TimelineStep key={s.id} s={s} last={i === steps.length - 1} aiEnabled={aiEnabled} anomaly={anomalyMap.get(s.id) ?? null} />)}
        </div>
      </div>
    </>
  )
}
