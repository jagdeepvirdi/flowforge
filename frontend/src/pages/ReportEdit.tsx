import { Link } from 'react-router-dom'
import { ArrowLeft, Play, Save, RefreshCw, Check, BarChart2, Lightbulb, Wand2, Activity, X } from 'lucide-react'
import type { ReportFormat } from '../lib/types'
import ChartPreview from '../components/report/ChartPreview'
import ColumnFormattingCard from '../components/report/ColumnFormattingCard'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'
import { useReportConfigForm } from '../hooks/useReportConfigForm'
import { useReportPreviewTools } from '../hooks/useReportPreviewTools'

const VAR_HINTS = ['{{ current_date }}', '{{ current_month }}', '{{ current_year }}', '{{ mon_year }}', '{{ now_ts }}', '{{ timestamp }}', '{{ run_id }}']
const FORMAT_EXT: Record<ReportFormat, string> = { excel: '.xlsx', csv: '.csv', pdf: '.pdf', json: '.json' }

export default function ReportEdit() {
  const {
    id, isNew, isLoading, dbConns, aiEnabled,
    register, handleSubmit, getValues, setValue, errors, isSubmitting,
    columnFormatting, setColumnFormatting,
    error, setError,
    format, name,
    onSubmit,
  } = useReportConfigForm()

  const {
    preview, previewing, handlePreview,
    chartConfig, setChartConfig, visualizing, handleVisualize,
    explanation, setExplanation, explaining, handleExplain,
    optimization, setOptimization, optimizing, handleOptimize, acceptOptimization,
    profilePending, setProfilePending, profileResult, setProfileResult, profiling,
    handleSummarise, handleProfileProceed,
  } = useReportPreviewTools(id, getValues, setValue, setError)

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
