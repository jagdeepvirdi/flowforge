import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Save, ArrowLeft, Play } from 'lucide-react'
import {
  getReportConfig, createReportConfig, updateReportConfig, previewReport,
  getDbConnections,
} from '../lib/api'
import type { ReportFormat } from '../lib/types'
import PageHeader from '../components/shared/PageHeader'
import Spinner from '../components/shared/Spinner'

const VAR_HINTS = ['{{ current_date }}', '{{ current_month }}', '{{ current_year }}', '{{ run_id }}']

export default function ReportEdit() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: existing, isLoading } = useQuery({ queryKey: ['report-config', id], queryFn: () => getReportConfig(id!), enabled: !isNew })
  const { data: dbConns = [] } = useQuery({ queryKey: ['db-connections'], queryFn: getDbConnections })

  const [name, setName]             = useState('')
  const [desc, setDesc]             = useState('')
  const [connId, setConnId]         = useState('')
  const [query, setQuery]           = useState('')
  const [format, setFormat]         = useState<ReportFormat>('excel')
  const [filename, setFilename]     = useState('report_{{ current_month }}.xlsx')
  const [sheetName, setSheetName]   = useState('Sheet1')
  const [title, setTitle]           = useState('')
  const [saving, setSaving]         = useState(false)
  const [error, setError]           = useState('')
  const [preview, setPreview]       = useState<{ columns: string[]; rows: unknown[][] } | null>(null)
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
    if (!name.trim()) { setError('Name is required'); return }
    if (!query.trim()) { setError('Query is required'); return }
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
    if (!id) { setError('Save the config first to preview'); return }
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

  if (!isNew && isLoading) return <div className="p-8 flex justify-center"><Spinner /></div>

  return (
    <div className="p-8 max-w-3xl">
      <PageHeader title={isNew ? 'New Report Config' : 'Edit Report Config'}
        action={
          <div className="flex gap-2">
            <Link to="/reports" className="btn-secondary"><ArrowLeft size={14}/> Back</Link>
            {!isNew && (
              <button className="btn-secondary" onClick={handlePreview} disabled={previewing}>
                {previewing ? <Spinner size={14}/> : <Play size={14}/>} Preview
              </button>
            )}
            <button className="btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? <Spinner size={14}/> : <Save size={14}/>} Save
            </button>
          </div>
        }
      />

      {error && <div className="mb-4 text-danger text-sm bg-danger/10 border border-danger/20 rounded-input px-3 py-2">{error}</div>}

      <div className="card mb-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div><label className="label">Name *</label><input className="input" value={name} onChange={e => setName(e.target.value)}/></div>
          <div><label className="label">Connection</label>
            <select className="input" value={connId} onChange={e => setConnId(e.target.value)}>
              <option value="">Select connection…</option>
              {dbConns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
        </div>
        <div><label className="label">Description</label><input className="input" value={desc} onChange={e => setDesc(e.target.value)}/></div>

        <div className="grid grid-cols-3 gap-4">
          <div><label className="label">Format</label>
            <select className="input" value={format} onChange={e => setFormat(e.target.value as ReportFormat)}>
              <option value="excel">Excel</option>
              <option value="csv">CSV</option>
              <option value="pdf">PDF</option>
            </select>
          </div>
          {format === 'excel' && <div><label className="label">Sheet name</label><input className="input" value={sheetName} onChange={e => setSheetName(e.target.value)}/></div>}
          {format === 'pdf' && <div><label className="label">Title</label><input className="input" value={title} onChange={e => setTitle(e.target.value)}/></div>}
        </div>

        <div>
          <label className="label">Output filename</label>
          <input className="input font-mono text-sm" value={filename} onChange={e => setFilename(e.target.value)}/>
          <div className="flex gap-1 mt-1.5 flex-wrap">
            {VAR_HINTS.map(v => (
              <button key={v} className="text-xs font-mono bg-surface2 border border-border px-1.5 py-0.5 rounded text-text-muted hover:text-text-primary"
                onClick={() => setFilename(f => f.replace('.xlsx', '').replace('.csv', '').replace('.pdf', '') + v + (format === 'excel' ? '.xlsx' : format === 'csv' ? '.csv' : '.pdf'))}>
                {v}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="label">SQL Query</label>
          <textarea className="input font-mono text-sm resize-none" rows={8} value={query} onChange={e => setQuery(e.target.value)} placeholder="SELECT ..."/>
        </div>
      </div>

      {/* Preview */}
      {preview && (
        <div className="card overflow-hidden p-0">
          <div className="px-4 py-2.5 border-b border-border text-xs font-medium text-text-muted">
            Preview — first {preview.rows.length} rows
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="border-b border-border bg-surface2">
                <tr>{preview.columns.map(c => <th key={c} className="text-left px-3 py-2 text-text-muted">{c}</th>)}</tr>
              </thead>
              <tbody>
                {preview.rows.map((row, i) => (
                  <tr key={i} className="border-b border-border/50 last:border-0">
                    {(row as unknown[]).map((cell, j) => <td key={j} className="px-3 py-1.5 font-mono text-text-primary">{String(cell ?? '')}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
