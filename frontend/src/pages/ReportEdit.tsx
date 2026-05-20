import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Play, Save, RefreshCw, Check } from 'lucide-react'
import {
  getReportConfig, createReportConfig, updateReportConfig, previewReport,
  getDbConnections,
} from '../lib/api'
import type { ReportFormat } from '../lib/types'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'

const VAR_HINTS = ['{{ current_date }}', '{{ current_month }}', '{{ current_year }}', '{{ timestamp }}', '{{ run_id }}']

export default function ReportEdit() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: existing, isLoading } = useQuery({ queryKey: ['report-config', id], queryFn: () => getReportConfig(id!), enabled: !isNew })
  const { data: dbConns = [] } = useQuery({ queryKey: ['db-connections'], queryFn: getDbConnections })

  const [name, setName]           = useState('')
  const [desc, setDesc]           = useState('')
  const [connId, setConnId]       = useState('')
  const [query, setQuery]         = useState('')
  const [format, setFormat]       = useState<ReportFormat>('excel')
  const [filename, setFilename]   = useState('report_{{ current_month }}.xlsx')
  const [sheetName, setSheetName] = useState('Sheet1')
  const [title, setTitle]         = useState('')
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [preview, setPreview]     = useState<{ columns: string[]; rows: unknown[][] } | null>(null)
  const [previewing, setPreviewing] = useState(false)

  useEffect(() => {
    if (existing) {
      setName(existing.name)
      setDesc(existing.description ?? '')
      setConnId(existing.connection_id ?? '')
      setQuery(existing.query)
      setFormat(existing.format)
      setFilename(existing.output_filename)
      setSheetName(existing.sheet_name ?? 'Sheet1')
      setTitle(existing.title ?? '')
    }
  }, [existing])

  const handleSave = async () => {
    const errs: Record<string, string> = {}
    if (!name.trim()) errs.name = 'Name is required'
    if (!query.trim()) errs.query = 'SQL query is required'
    if (Object.keys(errs).length) { setFieldErrors(errs); return }
    setFieldErrors({})
    setSaving(true); setError('')
    try {
      const payload = { name, description: desc, connection_id: connId || null, query, format, output_filename: filename, sheet_name: sheetName, title }
      isNew ? await createReportConfig(payload) : await updateReportConfig(id!, payload)
      qc.invalidateQueries({ queryKey: ['report-configs'] })
      navigate('/reports')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
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
    <><TopBar crumbs={crumbs} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
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
            <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
              {saving ? <Spinner size={12} /> : <Save size={12} />} Save report
            </button>
          </div>
        }
      />

      <div className="scroll" style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20, alignItems: 'start' }}>
        {/* Left config panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em', margin: '0 0 4px', color: 'var(--text)' }}>{name || 'New Report'}</h1>
            {desc && <p style={{ color: 'var(--text-muted)', fontSize: 12.5, margin: 0 }}>{desc}</p>}
          </div>

          {error && <div style={{ padding: '8px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 7, fontSize: 12.5, color: '#F87171' }}>{error}</div>}

          {/* Name / description */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>Details</div>
            <div className="field">
              <label>Name *</label>
              <input className="input" value={name} onChange={e => { setName(e.target.value); if (fieldErrors.name) setFieldErrors(f => ({ ...f, name: '' })) }} placeholder="My report" />
              {fieldErrors.name && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{fieldErrors.name}</span>}
            </div>
            <div className="field">
              <label>Description</label>
              <input className="input" value={desc} onChange={e => setDesc(e.target.value)} />
            </div>
          </div>

          {/* Data source */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>Data source</div>
            <div className="field">
              <label>Connection</label>
              <select className="input" value={connId} onChange={e => setConnId(e.target.value)} style={{ height: 34 }}>
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
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                {(['excel', 'csv', 'pdf'] as ReportFormat[]).map(f => (
                  <button key={f} onClick={() => setFormat(f)} style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                    padding: '10px 4px',
                    background: format === f ? 'rgba(249,115,22,0.08)' : 'var(--bg)',
                    border: `1px solid ${format === f ? 'var(--accent)' : 'var(--border)'}`,
                    borderRadius: 7,
                    color: format === f ? 'var(--accent-h)' : '#94A3B8',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    fontSize: 11.5,
                    fontWeight: 600,
                    boxShadow: format === f ? '0 0 0 3px rgba(249,115,22,0.1)' : 'none',
                  }}>
                    {format === f && <Check size={12} />}
                    {f === 'excel' ? 'Excel' : f === 'csv' ? 'CSV' : 'PDF'}
                  </button>
                ))}
              </div>
            </div>

            {format === 'excel' && (
              <div className="field">
                <label>Sheet name</label>
                <input className="input" value={sheetName} onChange={e => setSheetName(e.target.value)} />
              </div>
            )}
            {format === 'pdf' && (
              <div className="field">
                <label>Title</label>
                <input className="input" value={title} onChange={e => setTitle(e.target.value)} />
              </div>
            )}

            <div className="field">
              <label>Output filename</label>
              <input className="input mono-input" value={filename} onChange={e => setFilename(e.target.value)} />
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                <span style={{ fontSize: 10.5, color: 'var(--text-dim)' }}>Variables:</span>
                {VAR_HINTS.map(v => (
                  <button key={v} onClick={() => setFilename(f => {
                    const ext = format === 'excel' ? '.xlsx' : format === 'csv' ? '.csv' : '.pdf'
                    return f.replace(/\.(xlsx|csv|pdf)$/, '') + v + ext
                  })} className="mono" style={{ fontSize: 10.5, padding: '1px 6px', background: 'rgba(249,115,22,0.08)', color: 'var(--accent-h)', borderRadius: 3, border: '1px solid rgba(249,115,22,0.2)', cursor: 'pointer', fontFamily: 'var(--font-mono)' }}>
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
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderBottom: '1px solid var(--border)', background: '#161922' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text)', fontWeight: 500 }}>
                <span className="mono" style={{ color: '#94A3B8' }}>query.sql</span>
              </div>
              <button className="btn btn-sm btn-ghost" onClick={handlePreview} disabled={previewing}>
                {previewing ? <Spinner size={12} /> : <RefreshCw size={12} />} Run
              </button>
              {fieldErrors.query && <span style={{ fontSize: 11.5, color: 'var(--failure)', marginLeft: 8 }}>{fieldErrors.query}</span>}
            </div>
            <div style={{ background: '#0F1117', padding: 0 }}>
              <textarea
                className="input mono-input"
                rows={12}
                value={query}
                onChange={e => setQuery(e.target.value)}
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
