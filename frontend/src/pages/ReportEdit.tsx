import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowLeft, Play, Save, RefreshCw, Check } from 'lucide-react'
import {
  getReportConfig, createReportConfig, updateReportConfig, previewReport,
  getDbConnections,
} from '../lib/api'
import type { ReportFormat } from '../lib/types'
import { useProjectStore } from '../lib/store'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'

const VAR_HINTS = ['{{ current_date }}', '{{ current_month }}', '{{ current_year }}', '{{ timestamp }}', '{{ run_id }}']
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

export default function ReportEdit() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { activeProjectId } = useProjectStore()

  const { data: existing, isLoading } = useQuery({ queryKey: ['report-config', id], queryFn: () => getReportConfig(id!), enabled: !isNew })
  const { data: dbConns = [] } = useQuery({ queryKey: ['db-connections'], queryFn: getDbConnections })

  const { register, handleSubmit, watch, getValues, setValue, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '', desc: '', connId: '', query: '',
      format: 'excel',
      filename: 'report_{{ current_month }}.xlsx',
      sheetName: 'Sheet1', title: '',
    },
  })

  const [error, setError] = useState('')
  const [preview, setPreview] = useState<{ columns: string[]; rows: unknown[][] } | null>(null)
  const [previewing, setPreviewing] = useState(false)

  const format = watch('format')
  const name   = watch('name')

  useEffect(() => {
    if (existing) reset({
      name:      existing.name,
      desc:      existing.description ?? '',
      connId:    existing.connection_id ?? '',
      query:     existing.query,
      format:    existing.format,
      filename:  existing.output_filename,
      sheetName: existing.sheet_name ?? 'Sheet1',
      title:     existing.title ?? '',
    })
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed')
    } finally {
      setPreviewing(false)
    }
  }

  const crumbs = isNew ? ['Workspace', 'Reports', 'New Report'] : ['Workspace', 'Reports', name || 'Edit Report']

  if (!isNew && isLoading) return (
    <>
      <TopBar crumbs={crumbs} />
      <div className="scroll" style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20, alignItems: 'start' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Sk h={28} r={6} style={{ width: 180 }} />
          {[['Details', 2], ['Data source', 1], ['Output', 4]].map(([label, rows]) => (
            <div key={label as string} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <Sk h={13} style={{ width: 80 }} />
              {Array.from({ length: rows as number }).map((_, i) => (
                <div key={i} className="field">
                  <Sk h={12} style={{ width: 70, marginBottom: 6 }} />
                  <Sk h={34} r={6} />
                </div>
              ))}
            </div>
          ))}
        </div>
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border)', background: 'var(--bg-code)' }}>
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
          <div style={{ display: 'flex', gap: 8 }}>
            <Link to="/reports" className="btn btn-sm"><ArrowLeft size={12} /> Back</Link>
            {!isNew && (
              <button className="btn btn-sm" onClick={handlePreview} disabled={previewing}>
                {previewing ? <Spinner size={12} /> : <Play size={12} />} Run query
              </button>
            )}
            <button className="btn btn-primary btn-sm" onClick={handleSubmit(onSubmit)} disabled={isSubmitting}>
              {isSubmitting ? <Spinner size={12} /> : <Save size={12} />} Save report
            </button>
          </div>
        }
      />

      <div className="scroll" style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20, alignItems: 'start' }}>
        {/* Left config panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em', margin: '0 0 4px', color: 'var(--text)' }}>{name || 'New Report'}</h1>
          </div>

          {error && <div style={{ padding: '8px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 7, fontSize: 12.5, color: 'var(--failure-text)' }}>{error}</div>}

          {/* Name / description */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>Details</div>
            <div className="field">
              <label>Name *</label>
              <input className="input" {...register('name')} placeholder="My report" />
              {errors.name && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{errors.name.message}</span>}
            </div>
            <div className="field">
              <label>Description</label>
              <input className="input" {...register('desc')} />
            </div>
          </div>

          {/* Data source */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>Data source</div>
            <div className="field">
              <label>Connection</label>
              <select className="input" {...register('connId')} style={{ height: 34 }}>
                <option value="">Select connection…</option>
                {dbConns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>

          {/* Output */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>Output</div>

            {/* Format selector */}
            <div className="field">
              <label>Format</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
                {(['excel', 'csv', 'pdf', 'json'] as ReportFormat[]).map(f => (
                  <button key={f} type="button" onClick={() => {
                    setValue('format', f)
                    setValue('filename', getValues('filename').replace(/\.(xlsx|csv|pdf|json)$/, '') + FORMAT_EXT[f])
                  }} style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                    padding: '10px 4px',
                    background: format === f ? 'rgba(249,115,22,0.08)' : 'var(--bg)',
                    border: `1px solid ${format === f ? 'var(--accent)' : 'var(--border)'}`,
                    borderRadius: 7,
                    color: format === f ? 'var(--accent-h)' : 'var(--text-3)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    fontSize: 11.5,
                    fontWeight: 600,
                    boxShadow: format === f ? '0 0 0 3px rgba(249,115,22,0.1)' : 'none',
                  }}>
                    {format === f && <Check size={12} />}
                    {f === 'excel' ? 'Excel' : f === 'csv' ? 'CSV' : f === 'pdf' ? 'PDF' : 'JSON'}
                  </button>
                ))}
              </div>
            </div>

            {format === 'excel' && (
              <div className="field">
                <label>Sheet name</label>
                <input className="input" {...register('sheetName')} />
              </div>
            )}
            {format === 'pdf' && (
              <div className="field">
                <label>Title</label>
                <input className="input" {...register('title')} />
              </div>
            )}

            <div className="field">
              <label>Output filename</label>
              <input className="input mono-input" {...register('filename')} />
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                <span style={{ fontSize: 10.5, color: 'var(--text-dim)' }}>Variables:</span>
                {VAR_HINTS.map(v => (
                  <button key={v} type="button" onClick={() => {
                    setValue('filename', getValues('filename').replace(/\.(xlsx|csv|pdf|json)$/, '') + v + FORMAT_EXT[format])
                  }} className="mono" style={{ fontSize: 10.5, padding: '1px 6px', background: 'rgba(249,115,22,0.08)', color: 'var(--accent-h)', borderRadius: 3, border: '1px solid rgba(249,115,22,0.2)', cursor: 'pointer', fontFamily: 'var(--font-mono)' }}>
                    {v}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right panel: SQL editor + preview */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* SQL editor */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderBottom: '1px solid var(--border)', background: 'var(--bg-code)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text)', fontWeight: 500 }}>
                <span className="mono" style={{ color: 'var(--text-3)' }}>query.sql</span>
              </div>
              <button className="btn btn-sm btn-ghost" onClick={handlePreview} disabled={previewing}>
                {previewing ? <Spinner size={12} /> : <RefreshCw size={12} />} Run
              </button>
              {errors.query && <span style={{ fontSize: 11.5, color: 'var(--failure)', marginLeft: 8 }}>{errors.query.message}</span>}
            </div>
            <div style={{ background: 'var(--bg)', padding: 0 }}>
              <textarea
                className="input mono-input"
                rows={12}
                {...register('query')}
                placeholder="SELECT ..."
                style={{ background: 'var(--bg)', border: 'none', borderRadius: 0, resize: 'vertical', height: 'auto', padding: '14px 16px', color: 'var(--text-2)', lineHeight: 1.7, outline: 'none' }}
              />
            </div>
          </div>

          {/* Preview table */}
          {preview && (
            <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderBottom: '1px solid var(--border)' }}>
                <span style={{ fontSize: 12, color: 'var(--text)', fontWeight: 600 }}>Query preview</span>
                <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>· {preview.rows.length} rows</span>
              </div>
              <div style={{ overflow: 'auto', maxHeight: 360 }}>
                <table className="tbl">
                  <thead>
                    <tr>{preview.columns.map(c => <th key={c}>{c}</th>)}</tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, i) => (
                      <tr key={i}>
                        {(row as unknown[]).map((cell, j) => (
                          <td key={j} className="mono" style={{ fontSize: 12 }}>{String(cell ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
