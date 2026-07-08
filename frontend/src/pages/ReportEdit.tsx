import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowLeft, Play, Save, RefreshCw, Check, BarChart2, Lightbulb, Wand2, Activity, X, Plus, Trash2 } from 'lucide-react'
import {
  getReportConfig, createReportConfig, updateReportConfig, previewReport,
  generateChartConfig, aiQuery, profileData, getDbConnections, getSetupStatus,
} from '../lib/api'
import type { ReportFormat, ColumnFormatRule, ColumnConditionalRule } from '../lib/types'
import ChartPreview, { type ChartConfig } from '../components/report/ChartPreview'
import { useProjectStore } from '../lib/store'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'

const VAR_HINTS = ['{{ current_date }}', '{{ current_month }}', '{{ current_year }}', '{{ mon_year }}', '{{ now_ts }}', '{{ timestamp }}', '{{ run_id }}']
const FORMAT_EXT: Record<ReportFormat, string> = { excel: '.xlsx', csv: '.csv', pdf: '.pdf', json: '.json' }

const schema = z.object({
  name:      z.string().min(1, 'Name is required'),
  desc:      z.string(),
  connId:    z.string(),
  query:     z.string().min(1, 'SQL query is required'),
  format:    z.enum(['excel', 'csv', 'pdf', 'json']),
  filename:  z.string().min(1),
  sheetName: z.string(),
  title:     z.string(),
})
type FormValues = z.infer<typeof schema>

const NUMBER_FORMAT_PRESETS = [
  { label: 'Integer',       value: '#,##0' },
  { label: '2 decimals',    value: '#,##0.00' },
  { label: 'Currency $',    value: '$#,##0.00' },
  { label: 'Percentage',    value: '0.00%' },
  { label: 'Date DD/MM/YY', value: 'DD/MM/YYYY' },
  { label: 'Date MM/DD/YY', value: 'MM/DD/YYYY' },
  { label: 'Date ISO',      value: 'YYYY-MM-DD' },
  { label: 'Datetime',      value: 'YYYY-MM-DD HH:MM:SS' },
]

const OPERATORS: { value: ColumnConditionalRule['operator']; label: string }[] = [
  { value: 'lt',  label: '<' },
  { value: 'lte', label: '≤' },
  { value: 'gt',  label: '>' },
  { value: 'gte', label: '≥' },
  { value: 'eq',  label: '=' },
  { value: 'ne',  label: '≠' },
]

function ColumnFormattingCard({
  rules, setRules,
}: {
  rules: ColumnFormatRule[]
  setRules: React.Dispatch<React.SetStateAction<ColumnFormatRule[]>>
}) {
  const updateRule = (i: number, patch: Partial<ColumnFormatRule>) =>
    setRules(prev => prev.map((r, j) => j === i ? { ...r, ...patch } : r))

  const addCond = (i: number) =>
    setRules(prev => prev.map((r, j) => j === i
      ? { ...r, conditional: [...(r.conditional ?? []), { operator: 'lt', value: 0, bg_color: 'FFC7CE', font_color: '9C0006' }] }
      : r))

  const updateCond = (ri: number, ci: number, patch: Partial<ColumnConditionalRule>) =>
    setRules(prev => prev.map((r, j) => j === ri
      ? { ...r, conditional: (r.conditional ?? []).map((c, k) => k === ci ? { ...c, ...patch } : c) }
      : r))

  const removeCond = (ri: number, ci: number) =>
    setRules(prev => prev.map((r, j) => j === ri
      ? { ...r, conditional: (r.conditional ?? []).filter((_, k) => k !== ci) }
      : r))

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold">Column Formatting</div>
        <button type="button" className="btn btn-sm"
          onClick={() => setRules(r => [...r, { column: '', number_format: '', width: undefined, conditional: [] }])}>
          <Plus size={10} /> Add rule
        </button>
      </div>
      {rules.length === 0 && (
        <p className="text-xs text-text-muted m-0">
          No formatting rules. Add one to apply number formats and conditional cell colours to Excel output.
        </p>
      )}
      {rules.map((rule, i) => (
        <div key={i} className="border border-border rounded-[7px] py-2.5 px-3 flex flex-col gap-2">
          {/* Rule header */}
          <div className="flex items-center gap-2">
            <input
              className="input flex-1 h-7 text-xs"
              placeholder="Column name (exact)"
              value={rule.column}
              onChange={e => updateRule(i, { column: e.target.value })}
            />
            <select
              className="input h-7 text-xs max-w-40"
              value={rule.number_format ?? ''}
              onChange={e => updateRule(i, { number_format: e.target.value })}
            >
              <option value="">Number format…</option>
              {NUMBER_FORMAT_PRESETS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
            <input
              className="input mono-input w-20 h-7 text-xs"
              placeholder="custom"
              value={rule.number_format ?? ''}
              onChange={e => updateRule(i, { number_format: e.target.value })}
            />
            <input
              className="input w-14 h-7 text-xs"
              type="number"
              placeholder="width"
              value={rule.width ?? ''}
              onChange={e => updateRule(i, { width: e.target.value ? Number(e.target.value) : undefined })}
              min={3} max={255}
            />
            <button type="button" onClick={() => setRules(r => r.filter((_, j) => j !== i))}
              className="bg-transparent border-none cursor-pointer text-text-muted py-0.5 px-1">
              <Trash2 size={12} />
            </button>
          </div>

          {/* Conditional rules */}
          {(rule.conditional ?? []).map((cond, ci) => (
            <div key={ci} className="flex items-center gap-1.5 pl-2 border-l-2 border-border">
              <span className="text-[11px] text-text-muted whitespace-nowrap">if value</span>
              <select className="input w-[46px] h-[26px] text-xs px-1"
                value={cond.operator}
                onChange={e => updateCond(i, ci, { operator: e.target.value as ColumnConditionalRule['operator'] })}>
                {OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <input className="input w-16 h-[26px] text-xs" type="number"
                value={cond.value} onChange={e => updateCond(i, ci, { value: Number(e.target.value) })} />
              <span className="text-[11px] text-text-muted">bg</span>
              <input type="color" value={`#${cond.bg_color}`}
                onChange={e => updateCond(i, ci, { bg_color: e.target.value.slice(1) })}
                className="w-7 h-[26px] cursor-pointer border border-border rounded p-px" />
              <span className="text-[11px] text-text-muted">text</span>
              <input type="color" value={cond.font_color ? `#${cond.font_color}` : '#000000'}
                onChange={e => updateCond(i, ci, { font_color: e.target.value.slice(1) })}
                className="w-7 h-[26px] cursor-pointer border border-border rounded p-px" />
              <button type="button" onClick={() => removeCond(i, ci)}
                className="bg-transparent border-none cursor-pointer text-text-muted py-0.5 px-1">
                <X size={11} />
              </button>
            </div>
          ))}
          <button type="button" className="btn btn-sm self-start text-[11px]"
            onClick={() => addCond(i)}>
            <Plus size={9} /> Add condition
          </button>
        </div>
      ))}
    </div>
  )
}

export default function ReportEdit() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { activeProjectId } = useProjectStore()

  const { data: existing, isLoading } = useQuery({ queryKey: ['report-config', id], queryFn: () => getReportConfig(id!), enabled: !isNew })
  const { data: dbConns = [] } = useQuery({ queryKey: ['db-connections'], queryFn: getDbConnections })
  const { data: setupStatus } = useQuery({ queryKey: ['setup-status'], queryFn: getSetupStatus, staleTime: 60_000 })
  const aiEnabled = setupStatus?.ai?.enabled ?? true

  const { register, handleSubmit, watch, getValues, setValue, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '', desc: '', connId: '', query: '',
      format: 'excel',
      filename: 'report_{{ current_month }}.xlsx',
      sheetName: 'Sheet1', title: '',
    },
  })

  const [columnFormatting, setColumnFormatting] = useState<ColumnFormatRule[]>([])
  const [error, setError] = useState('')
  const [preview, setPreview] = useState<{ columns: string[]; rows: unknown[][] } | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const [chartConfig, setChartConfig] = useState<ChartConfig | null>(null)
  const [visualizing, setVisualizing] = useState(false)
  const [explanation, setExplanation] = useState<string | null>(null)
  const [explaining, setExplaining] = useState(false)
  const [optimization, setOptimization] = useState<{ original: string; suggested: string } | null>(null)
  const [optimizing, setOptimizing] = useState(false)
  const [profileConsented, setProfileConsented] = useState(false)
  const [profilePending, setProfilePending] = useState(false)
  const [profileResult, setProfileResult] = useState<string | null>(null)
  const [profiling, setProfiling] = useState(false)

  const format = watch('format')
  const name   = watch('name')

  useEffect(() => {
    if (!existing) return
    reset({
      name:      existing.name,
      desc:      existing.description ?? '',
      connId:    existing.connection_id ?? '',
      query:     existing.query,
      format:    existing.format,
      filename:  existing.output_filename,
      sheetName: existing.sheet_name ?? 'Sheet1',
      title:     existing.title ?? '',
    })
    setColumnFormatting(existing.column_formatting ?? [])
  }, [existing, reset])

  const onSubmit = async (values: FormValues) => {
    setError('')
    try {
      const payload = {
        name: values.name, description: values.desc,
        connection_id: values.connId || null,
        query: values.query, format: values.format,
        output_filename: values.filename,
        sheet_name: values.sheetName, title: values.title,
        column_formatting: columnFormatting,
        ...(isNew && activeProjectId ? { project_id: activeProjectId } : {}),
      }
      isNew ? await createReportConfig(payload) : await updateReportConfig(id!, payload)
      qc.invalidateQueries({ queryKey: ['report-configs'] })
      navigate('/reports')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    }
  }

  const handlePreview = async () => {
    if (!id) { setError('Save the report first to preview'); return }
    setPreviewing(true)
    try {
      const result = await previewReport(id)
      setPreview(result)
      setChartConfig(null)
      setExplanation(null)
      setOptimization(null)
      setProfileResult(null)
      setProfilePending(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed')
    } finally {
      setPreviewing(false)
    }
  }

  const handleExplain = async () => {
    const sql = getValues('query').trim()
    if (!sql) return
    setExplaining(true)
    setError('')
    try {
      const { result } = await aiQuery({ task: 'explain', sql })
      setExplanation(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Explanation failed')
    } finally {
      setExplaining(false)
    }
  }

  const handleOptimize = async () => {
    const sql = getValues('query').trim()
    if (!sql) return
    setOptimizing(true)
    setError('')
    try {
      const { result } = await aiQuery({ task: 'optimize', sql })
      setOptimization({ original: sql, suggested: result })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Optimization failed')
    } finally {
      setOptimizing(false)
    }
  }

  const doProfile = async () => {
    if (!preview) return
    setProfiling(true)
    setProfileResult(null)
    setError('')
    try {
      const { result } = await profileData({ columns: preview.columns, rows: preview.rows })
      setProfileResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Profiling failed')
    } finally {
      setProfiling(false)
    }
  }

  const handleSummarise = () => {
    if (!preview) return
    if (profileConsented) {
      doProfile()
    } else {
      setProfilePending(true)
    }
  }

  const handleProfileProceed = () => {
    setProfileConsented(true)
    setProfilePending(false)
    doProfile()
  }

  const acceptOptimization = () => {
    if (!optimization) return
    setValue('query', optimization.suggested)
    setOptimization(null)
    setExplanation(null)
  }

  const handleVisualize = async () => {
    if (!preview) return
    setVisualizing(true)
    setError('')
    try {
      const cfg = await generateChartConfig({ columns: preview.columns, rows: preview.rows })
      setChartConfig(cfg)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Visualization failed')
    } finally {
      setVisualizing(false)
    }
  }

  const crumbs = isNew ? ['Workspace', 'Reports', 'New Report'] : ['Workspace', 'Reports', name || 'Edit Report']

  if (!isNew && isLoading) return (
    <>
      <TopBar crumbs={crumbs} />
      <div className="scroll grid grid-cols-[300px_1fr] gap-5 items-start">
        <div className="flex flex-col gap-3.5">
          <Sk h={28} r={6} style={{ width: 180 }} />
          {[['Details', 2], ['Data source', 1], ['Output', 4]].map(([label, rows]) => (
            <div key={label as string} className="card flex flex-col gap-3">
              <Sk h={13} style={{ width: 80 }} />
              {Array.from({ length: rows as number }, (_, i) => i).map(n => (
                <div key={'sk-row-' + n} className="field">
                  <Sk h={12} style={{ width: 70, marginBottom: 6 }} />
                  <Sk h={34} r={6} />
                </div>
              ))}
            </div>
          ))}
        </div>
        <div className="card p-0 overflow-hidden">
          <div className="py-2.5 px-3.5 border-b border-border bg-bg-code">
            <Sk h={13} style={{ width: 80 }} />
          </div>
          <Sk h={220} r={0} />
        </div>
      </div>
    </>
  )

  return (
    <>
      <TopBar
        crumbs={crumbs}
        actions={
          <div className="flex gap-2">
            <Link to="/reports" className="btn btn-sm"><ArrowLeft size={12} /> Back</Link>
            {!isNew && (
              <button className="btn btn-sm" onClick={handlePreview} disabled={previewing}>
                {previewing ? <Spinner size={12} /> : <Play size={12} />} Run query
              </button>
            )}
            {!isNew && preview && aiEnabled && (
              <button className="btn btn-sm" onClick={handleVisualize} disabled={visualizing}>
                {visualizing ? <Spinner size={12} /> : <BarChart2 size={12} />} Visualize
              </button>
            )}
            {!isNew && preview && aiEnabled && (
              <button className="btn btn-sm" onClick={handleSummarise} disabled={profiling}>
                {profiling ? <Spinner size={12} /> : <Activity size={12} />} Summarise
              </button>
            )}
            <button className="btn btn-primary btn-sm" onClick={handleSubmit(onSubmit)} disabled={isSubmitting}>
              {isSubmitting ? <Spinner size={12} /> : <Save size={12} />} Save report
            </button>
          </div>
        }
      />

      <div className="scroll grid grid-cols-[300px_1fr] gap-5 items-start">
        {/* Left config panel */}
        <div className="flex flex-col gap-3.5">
          <div>
            <h1 className="text-xl font-semibold tracking-[-0.02em] m-0 mb-1 text-text-primary">{name || 'New Report'}</h1>
          </div>

          {error && <div className="py-2 px-3 bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-[7px] text-[12.5px] text-failure-text">{error}</div>}

          {/* Name / description */}
          <div className="card flex flex-col gap-3">
            <div className="text-xs font-semibold mb-0.5">Details</div>
            <div className="field">
              <label htmlFor="rc-name">Name *</label>
              <input id="rc-name" className="input" {...register('name')} placeholder="My report" />
              {errors.name && <span className="text-[11.5px] text-failure">{errors.name.message}</span>}
            </div>
            <div className="field">
              <label htmlFor="rc-desc">Description</label>
              <input id="rc-desc" className="input" {...register('desc')} />
            </div>
          </div>

          {/* Data source */}
          <div className="card flex flex-col gap-3">
            <div className="text-xs font-semibold mb-0.5">Data source</div>
            <div className="field">
              <label htmlFor="rc-connection">Connection</label>
              <select id="rc-connection" className="input" {...register('connId')}>
                <option value="">Select connection…</option>
                {dbConns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>

          {/* Output */}
          <div className="card flex flex-col gap-3">
            <div className="text-xs font-semibold mb-0.5">Output</div>

            {/* Format selector */}
            <div className="field">
              <div className="label">Format</div>
              <div className="grid grid-cols-2 gap-1.5">
                {(['excel', 'csv', 'pdf', 'json'] as ReportFormat[]).map(f => {
                  const formatLabels: Record<string, string> = { excel: 'Excel', csv: 'CSV', pdf: 'PDF', json: 'JSON' }
                  const formatLabel = formatLabels[f] || f.toUpperCase()
                  return (
                  <button key={f} type="button" onClick={() => {
                    setValue('format', f)
                    setValue('filename', getValues('filename').replace(/\.(xlsx|csv|pdf|json)$/, '') + FORMAT_EXT[f])
                  }} className={`flex flex-col items-center gap-1 py-2.5 px-1 rounded-[7px] border cursor-pointer font-[inherit] text-[11.5px] font-semibold ${format === f ? 'bg-[rgba(249,115,22,0.08)] border-accent text-accent-hover shadow-[0_0_0_3px_rgba(249,115,22,0.1)]' : 'bg-bg border-border text-text-3'}`}>
                    {format === f && <Check size={12} />}
                    {formatLabel}
                  </button>
                  )
                })}
              </div>
            </div>

            {format === 'excel' && (
              <div className="field">
                <label htmlFor="rc-sheet-name">Sheet name</label>
                <input id="rc-sheet-name" className="input" {...register('sheetName')} />
              </div>
            )}
            {format === 'pdf' && (
              <div className="field">
                <label htmlFor="rc-title">Title</label>
                <input id="rc-title" className="input" {...register('title')} />
              </div>
            )}

            <div className="field">
              <label htmlFor="rc-filename">Output filename</label>
              <input id="rc-filename" className="input mono-input" {...register('filename')} />
              <div className="flex flex-wrap gap-1 mt-1.5">
                <span className="text-[10.5px] text-text-dim">Variables:</span>
                {VAR_HINTS.map(v => (
                  <button key={v} type="button" onClick={() => {
                    setValue('filename', getValues('filename').replace(/\.(xlsx|csv|pdf|json)$/, '') + v + FORMAT_EXT[format])
                  }} className="mono text-[10.5px] py-px px-1.5 bg-[rgba(249,115,22,0.08)] text-accent-hover rounded-[3px] border border-[rgba(249,115,22,0.2)] cursor-pointer font-mono">
                    {v}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Column Formatting — Excel only */}
          {format === 'excel' && (
            <ColumnFormattingCard rules={columnFormatting} setRules={setColumnFormatting} />
          )}
        </div>

        {/* Right panel: SQL editor + preview */}
        <div className="flex flex-col gap-3.5">
          {/* SQL editor */}
          <div className="card p-0 overflow-hidden">
            <div className="flex items-center justify-between py-2.5 px-3.5 border-b border-border bg-bg-code">
              <div className="flex items-center gap-2 text-xs text-text-primary font-medium">
                <span className="mono text-text-3">query.sql</span>
              </div>
              <div className="flex gap-1.5 items-center">
                {aiEnabled && (
                  <button className="btn btn-sm btn-ghost" onClick={handleExplain} disabled={explaining}>
                    {explaining ? <Spinner size={12} /> : <Lightbulb size={12} />} Explain
                  </button>
                )}
                {aiEnabled && (
                  <button className="btn btn-sm btn-ghost" onClick={handleOptimize} disabled={optimizing}>
                    {optimizing ? <Spinner size={12} /> : <Wand2 size={12} />} Optimize
                  </button>
                )}
                <button className="btn btn-sm btn-ghost" onClick={handlePreview} disabled={previewing}>
                  {previewing ? <Spinner size={12} /> : <RefreshCw size={12} />} Run
                </button>
              </div>
              {errors.query && <span className="text-[11.5px] text-failure ml-2">{errors.query.message}</span>}
            </div>
            <div className="bg-bg p-0">
              <textarea
                className="input mono-input bg-bg border-none rounded-none resize-y h-auto py-3.5 px-4 text-text-2 leading-[1.7] outline-none"
                rows={12}
                {...register('query')}
                placeholder="SELECT ..."
              />
            </div>
          </div>

          {/* SQL Optimization diff */}
          {optimization && (
            <div className="card p-0 overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between py-[9px] px-3.5 border-b border-border">
                <div className="flex items-center gap-1.5">
                  <Wand2 size={13} className="text-accent" />
                  <span className="text-xs font-semibold text-text-primary">SQL Optimization</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="text-[10.5px] text-text-dim">via Ollama</span>
                  <button onClick={() => setOptimization(null)} className="flex bg-transparent border-none cursor-pointer text-text-3 p-0.5">
                    <X size={14} />
                  </button>
                </div>
              </div>

              {/* Side-by-side diff */}
              <div className="grid grid-cols-2 gap-0">
                <div className="border-r border-border">
                  <div className="py-1.5 px-3.5 border-b border-border bg-[rgba(239,68,68,0.04)]">
                    <span className="text-[10.5px] font-semibold text-text-3 uppercase tracking-[0.05em]">Original</span>
                  </div>
                  <pre className="m-0 py-3 px-3.5 text-xs leading-[1.65] text-text-2 overflow-x-auto font-mono whitespace-pre-wrap break-all bg-[rgba(239,68,68,0.02)] max-h-80">
                    {optimization.original}
                  </pre>
                </div>
                <div>
                  <div className="py-1.5 px-3.5 border-b border-border bg-[rgba(34,197,94,0.05)]">
                    <span className="text-[10.5px] font-semibold text-text-3 uppercase tracking-[0.05em]">Suggested</span>
                  </div>
                  <pre className="m-0 py-3 px-3.5 text-xs leading-[1.65] text-text-2 overflow-x-auto font-mono whitespace-pre-wrap break-all bg-[rgba(34,197,94,0.02)] max-h-80">
                    {optimization.suggested}
                  </pre>
                </div>
              </div>

              {/* Footer actions */}
              <div className="flex gap-2 py-2.5 px-3.5 border-t border-border justify-end">
                <button className="btn btn-sm" onClick={() => setOptimization(null)}>Dismiss</button>
                <button className="btn btn-primary btn-sm" onClick={acceptOptimization}>Accept suggestion</button>
              </div>
            </div>
          )}

          {/* SQL Explanation */}
          {explanation !== null && (
            <div className="card p-0 overflow-hidden">
              <div className="flex items-center justify-between py-[9px] px-3.5 border-b border-border">
                <div className="flex items-center gap-1.5">
                  <Lightbulb size={13} className="text-accent" />
                  <span className="text-xs font-semibold text-text-primary">SQL Explanation</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="text-[10.5px] text-text-dim">via Ollama</span>
                  <button onClick={() => setExplanation(null)} className="flex bg-transparent border-none cursor-pointer text-text-3 p-0.5">
                    <X size={14} />
                  </button>
                </div>
              </div>
              <div className="py-3.5 px-4 text-[13px] text-text-2 leading-[1.75] whitespace-pre-wrap">
                {explanation}
              </div>
            </div>
          )}

          {/* Preview table */}
          {preview && (
            <div className="card overflow-hidden p-0">
              <div className="flex items-center justify-between py-2.5 px-3.5 border-b border-border">
                <span className="text-xs text-text-primary font-semibold">Query preview</span>
                <span className="text-[10.5px] text-text-muted">· {preview.rows.length} rows</span>
              </div>
              <div className="overflow-auto max-h-[360px]">
                <table className="tbl">
                  <thead>
                    <tr>{preview.columns.map(c => <th key={c}>{c}</th>)}</tr>
                  </thead>
                  <tbody>
                    {Array.from(preview.rows.entries()).map(([i, row]) => (
                      <tr key={i}>
                        {Array.from((row as unknown[]).entries()).map(([j, cell]) => (
                          <td key={j} className="mono text-xs">{String(cell ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Data profile opt-in banner */}
          {profilePending && (
            <div className="py-3 px-3.5 bg-[rgba(59,130,246,0.06)] border border-[rgba(59,130,246,0.18)] rounded-r flex flex-col gap-2.5">
              <div className="flex items-start gap-[9px]">
                <Activity size={14} className="text-running mt-px shrink-0" />
                <div>
                  <div className="text-xs font-semibold text-text-primary mb-1">Data Profiling — Local Only</div>
                  <div className="text-xs text-text-2 leading-[1.65]">
                    Your preview rows (up to 20) will be sent to your <strong>local Ollama instance</strong> for analysis.
                    No data leaves your machine.
                  </div>
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <button className="btn btn-sm" onClick={() => setProfilePending(false)}>Cancel</button>
                <button className="btn btn-primary btn-sm" onClick={handleProfileProceed} disabled={profiling}>
                  {profiling ? <Spinner size={12} /> : <Activity size={12} />} Proceed
                </button>
              </div>
            </div>
          )}

          {/* Data profile result */}
          {profileResult !== null && (
            <div className="card p-0 overflow-hidden">
              <div className="flex items-center justify-between py-[9px] px-3.5 border-b border-border">
                <div className="flex items-center gap-1.5">
                  <Activity size={13} className="text-accent" />
                  <span className="text-xs font-semibold text-text-primary">Data Profile</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="text-[10.5px] text-text-dim">via Ollama</span>
                  <button onClick={() => setProfileResult(null)} className="flex bg-transparent border-none cursor-pointer text-text-3 p-0.5">
                    <X size={14} />
                  </button>
                </div>
              </div>
              <div className="py-3.5 px-4 text-[13px] text-text-2 leading-[1.75] whitespace-pre-wrap">
                {profileResult}
              </div>
            </div>
          )}

          {/* AI Chart */}
          {chartConfig && preview && (
            <ChartPreview
              columns={preview.columns}
              rows={preview.rows}
              config={chartConfig}
              onConfigChange={setChartConfig}
            />
          )}
        </div>
      </div>
    </>
  )
}
