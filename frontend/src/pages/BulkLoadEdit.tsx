import { useState } from 'react'
import { useNavigate, useParams, Link, type NavigateFunction } from 'react-router-dom'
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { ArrowLeft, Save, FlaskConical, TriangleAlert } from 'lucide-react'
import {
  getBulkLoadConfig, createBulkLoadConfig, updateBulkLoadConfig,
  getDbConnections, validateBulkLoadConfigRaw, type BulkLoadPreview,
} from '../lib/api'
import type { BulkLoadConfig, DbConnection } from '../lib/types'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'

const VAR_HINTS = ['{{ current_date }}', '{{ current_month }}', '{{ current_year }}', '{{ timestamp }}']

export default function BulkLoadEdit() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: existing, isLoading } = useQuery({
    queryKey: ['bulk-load-config', id],
    queryFn: () => getBulkLoadConfig(id!),
    enabled: !isNew,
  })
  const { data: dbConns = [] } = useQuery({ queryKey: ['db-connections'], queryFn: getDbConnections })

  const crumbs = isNew
    ? ['Workspace', 'Bulk Loads', 'New Bulk Load']
    : ['Workspace', 'Bulk Loads', 'Edit Bulk Load']

  if (!isNew && isLoading) return (
    <><TopBar crumbs={crumbs} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
  )

  // Keyed by id so navigating between two different configs' edit pages (or
  // between /new and an edit page) always mounts a fresh form instance —
  // local state is seeded once from `existing` below, not synced via effect.
  return (
    <BulkLoadForm
      key={id ?? 'new'}
      id={id}
      isNew={isNew}
      existing={existing}
      dbConns={dbConns}
      navigate={navigate}
      qc={qc}
    />
  )
}

function BulkLoadForm({ id, isNew, existing, dbConns, navigate, qc }: {
  id?: string
  isNew: boolean
  existing?: BulkLoadConfig
  dbConns: DbConnection[]
  navigate: NavigateFunction
  qc: QueryClient
}) {
  const [name, setName]                     = useState(existing?.name ?? '')
  const [desc, setDesc]                     = useState(existing?.description ?? '')
  const [connId, setConnId]                 = useState(existing?.connection_id ?? '')
  const [sourceDir, setSourceDir]           = useState(existing?.source_directory ?? '')
  const [filePrefix, setFilePrefix]         = useState(existing?.file_prefix ?? '')
  const [filePrefixExclude, setFilePrefixExclude] = useState(existing?.file_prefix_exclude ?? '')
  const [fileType, setFileType]             = useState(existing?.file_type ?? 'csv')
  const [delimiter, setDelimiter]           = useState(existing?.delimiter ?? ',')
  const [headerRows, setHeaderRows]         = useState(existing?.header_rows ?? 1)
  const [footerRows, setFooterRows]         = useState(existing?.footer_rows ?? 0)
  const [targetTable, setTargetTable]       = useState(existing?.target_table ?? '')
  const [loadMode, setLoadMode]             = useState(existing?.load_mode ?? 'append')
  const [useSqlLoader, setUseSqlLoader]     = useState(existing?.use_sqlloader ?? false)
  const [archiveDir, setArchiveDir]         = useState(existing?.archive_directory ?? '')
  const [onNoFiles, setOnNoFiles]           = useState(existing?.on_no_files ?? 'skip')
  const [colMapRaw, setColMapRaw]           = useState(JSON.stringify(existing?.column_mapping ?? [], null, 2))
  const [saving, setSaving]                 = useState(false)
  const [error, setError]                   = useState('')
  const [fieldErrors, setFieldErrors]       = useState<Record<string, string>>({})

  const [testing, setTesting]               = useState(false)
  const [testError, setTestError]           = useState('')
  const [preview, setPreview]               = useState<BulkLoadPreview | null>(null)
  const [dryRun, setDryRun]                 = useState(false)

  const buildPayload = () => {
    let columnMapping: { source: string; target: string }[] = []
    try { columnMapping = JSON.parse(colMapRaw) } catch { /* invalid JSON — fall back to empty mapping */ }
    return {
      name, description: desc,
      connection_id: connId || null,
      source_directory: sourceDir,
      file_prefix: filePrefix,
      file_prefix_exclude: filePrefixExclude,
      file_type: fileType,
      delimiter,
      header_rows: headerRows,
      footer_rows: footerRows,
      target_table: targetTable,
      load_mode: loadMode,
      use_sqlloader: useSqlLoader,
      archive_directory: archiveDir,
      on_no_files: onNoFiles,
      column_mapping: columnMapping,
    }
  }

  const handleSave = async () => {
    const errs: Record<string, string> = {}
    if (!name.trim()) errs.name = 'Name is required'
    if (!sourceDir.trim()) errs.sourceDir = 'Source directory is required'
    if (!targetTable.trim()) errs.targetTable = 'Target table is required'
    if (Object.keys(errs).length) { setFieldErrors(errs); return }
    setFieldErrors({})

    setSaving(true); setError('')
    try {
      const payload = buildPayload()
      isNew
        ? await createBulkLoadConfig(payload)
        : await updateBulkLoadConfig(id!, payload)
      qc.invalidateQueries({ queryKey: ['bulk-load-configs'] })
      navigate('/bulk-loads')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    if (!sourceDir.trim()) { setTestError('Source directory is required to run a test'); return }
    setTesting(true); setTestError(''); setPreview(null)
    try {
      const result = await validateBulkLoadConfigRaw(buildPayload(), dryRun)
      setPreview(result)
    } catch (err) {
      setTestError(err instanceof Error ? err.message : 'Test failed')
    } finally {
      setTesting(false)
    }
  }

  /** "Row 2, 5, 9 and 9 more" — caps the numbers shown so one systemic issue
   * can't crowd out other findings; the table highlight below still marks
   * every affected row, not just the capped ones. */
  const formatRowNumbers = (indices: number[], cap = 3): string => {
    const shown = indices.slice(0, cap).map(i => i + 1)
    const extra = indices.length - shown.length
    const label = shown.length === 1 && extra === 0 ? 'Row' : 'Rows'
    return extra > 0 ? `${label} ${shown.join(', ')} and ${extra} more` : `${label} ${shown.join(', ')}`
  }

  const errorGroups = preview?.error_groups ?? []
  const errorRowIndices = new Set(errorGroups.flatMap(g => g.row_indices))
  const errorCellKeys = new Set(
    errorGroups.flatMap(g => g.column ? g.row_indices.map(i => `${i}:${g.column}`) : []),
  )

  const crumbs = isNew
    ? ['Workspace', 'Bulk Loads', 'New Bulk Load']
    : ['Workspace', 'Bulk Loads', name || 'Edit Bulk Load']

  return (
    <>
      <TopBar
        crumbs={crumbs}
        actions={
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--text-muted)', cursor: 'pointer' }}>
              <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} />
              Attempt insert (rolled back)
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <Link to="/bulk-loads" className="btn btn-sm"><ArrowLeft size={12} />{' '}Back</Link>
              <button className="btn btn-sm" onClick={handleTest} disabled={testing}>
                {testing ? <Spinner size={12} /> : <FlaskConical size={12} />}{' '}Test File
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
                {saving ? <Spinner size={12} /> : <Save size={12} />}{' '}Save
              </button>
            </div>
          </div>
        }
      />

      <div className="scroll" style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20, alignItems: 'start' }}>
        {/* Left: details + source */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em', margin: '0 0 4px', color: 'var(--text)' }}>{name || 'New Bulk Load'}</h1>
            {desc && <p style={{ color: 'var(--text-muted)', fontSize: 12.5, margin: 0 }}>{desc}</p>}
          </div>

          {error && (
            <div style={{ padding: '8px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 7, fontSize: 12.5, color: 'var(--failure-text)' }}>
              {error}
            </div>
          )}

          {/* Details */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>Details</div>
            <div className="field">
              <label htmlFor="bulk-name">Name *</label>
              <input id="bulk-name" className="input" value={name} onChange={e => { setName(e.target.value); if (fieldErrors.name) setFieldErrors(f => ({ ...f, name: '' })) }} placeholder="Daily subscriber load" />
              {fieldErrors.name && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{fieldErrors.name}</span>}
            </div>
            <div className="field">
              <label htmlFor="bulk-desc">Description</label>
              <input id="bulk-desc" className="input" value={desc} onChange={e => setDesc(e.target.value)} />
            </div>
          </div>

          {/* Connection */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>Target database</div>
            <div className="field">
              <label htmlFor="bulk-connection">Connection</label>
              <select id="bulk-connection" className="input" value={connId} onChange={e => setConnId(e.target.value)} style={{ height: 34 }}>
                <option value="">Select connection…</option>
                {dbConns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="bulk-target-table">Target table *</label>
              <input id="bulk-target-table" className="input mono-input" value={targetTable}
                onChange={e => { setTargetTable(e.target.value); if (fieldErrors.targetTable) setFieldErrors(f => ({ ...f, targetTable: '' })) }}
                placeholder="STAGING.SUBSCRIPTIONS" />
              {fieldErrors.targetTable && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{fieldErrors.targetTable}</span>}
            </div>
            <div className="field">
              <label htmlFor="bulk-load-mode">Load mode</label>
              <select id="bulk-load-mode" className="input" value={loadMode} onChange={e => setLoadMode(e.target.value)} style={{ height: 34 }}>
                <option value="append">Append — insert rows without touching existing data</option>
                <option value="replace">Replace — truncate table then insert</option>
              </select>
            </div>
            <div className="field">
              <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input type="checkbox" checked={useSqlLoader} onChange={e => setUseSqlLoader(e.target.checked)} />{' '}
                Use SQL*Loader (Oracle only)
              </label>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
                Direct-path load via sqlldr subprocess. Fastest for Oracle bulk inserts.
                Known gap: "Attempt insert" dry-run testing isn't available on this path (sqlldr manages
                its own commits) — Test File still checks the file, header, and target columns.
              </span>
            </div>
          </div>
        </div>

        {/* Right: source config + advanced */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Source */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>Source files</div>

            <div className="field">
              <label htmlFor="bulk-source-dir">Source directory *</label>
              <input id="bulk-source-dir" className="input mono-input" value={sourceDir}
                onChange={e => { setSourceDir(e.target.value); if (fieldErrors.sourceDir) setFieldErrors(f => ({ ...f, sourceDir: '' })) }}
                placeholder="/data/incoming/" />
              {fieldErrors.sourceDir && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{fieldErrors.sourceDir}</span>}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div className="field">
                <label htmlFor="bulk-file-prefix">File prefix (optional)</label>
                <input id="bulk-file-prefix" className="input mono-input" value={filePrefix} onChange={e => setFilePrefix(e.target.value)} placeholder="SUBS_" />
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>Only load files starting with this.</span>
              </div>
              <div className="field">
                <label htmlFor="bulk-file-prefix-exclude">Exclude prefix (optional)</label>
                <input id="bulk-file-prefix-exclude" className="input mono-input" value={filePrefixExclude} onChange={e => setFilePrefixExclude(e.target.value)} placeholder="SUBS_OLD_" />
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>Skip files starting with this.</span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
              <div className="field">
                <label htmlFor="bulk-file-type">File type</label>
                <select id="bulk-file-type" className="input" value={fileType} onChange={e => setFileType(e.target.value)} style={{ height: 34 }}>
                  <option value="csv">CSV</option>
                  <option value="xlsx">Excel (.xlsx)</option>
                  <option value="txt">TXT</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="bulk-delimiter">Delimiter</label>
                <input id="bulk-delimiter" className="input mono-input" value={delimiter} onChange={e => setDelimiter(e.target.value)} maxLength={3} style={{ width: 70 }} />
              </div>
              <div className="field">
                <label htmlFor="bulk-on-no-files">On no files</label>
                <select id="bulk-on-no-files" className="input" value={onNoFiles} onChange={e => setOnNoFiles(e.target.value)} style={{ height: 34 }}>
                  <option value="skip">Skip (succeed)</option>
                  <option value="fail">Fail</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div className="field">
                <label htmlFor="bulk-header-rows">Header rows</label>
                <input id="bulk-header-rows" className="input" type="number" min={0} max={10} value={headerRows} onChange={e => setHeaderRows(Number.parseInt(e.target.value) || 0)} />
              </div>
              <div className="field">
                <label htmlFor="bulk-footer-rows">Footer rows</label>
                <input id="bulk-footer-rows" className="input" type="number" min={0} max={10} value={footerRows} onChange={e => setFooterRows(Number.parseInt(e.target.value) || 0)} />
              </div>
            </div>
          </div>

          {/* Test file results */}
          {testError && (
            <div style={{ padding: '8px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 7, fontSize: 12.5, color: 'var(--failure-text)' }}>
              {testError}
            </div>
          )}

          {preview && (
            <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderBottom: '1px solid var(--border)' }}>
                <span style={{ fontSize: 12, color: 'var(--text)', fontWeight: 600 }}>
                  Preview · <span className="mono">{preview.file_name}</span>
                </span>
                <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>
                  {preview.files_matched} file{preview.files_matched === 1 ? '' : 's'} matched · showing {preview.row_count_sampled} row{preview.row_count_sampled === 1 ? '' : 's'}
                </span>
              </div>

              {preview.warnings.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '10px 14px', background: 'rgba(234,179,8,0.06)', borderBottom: '1px solid var(--border)' }}>
                  {preview.warnings.map((w, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 7, fontSize: 12, color: 'var(--text-2)' }}>
                      <TriangleAlert size={13} style={{ color: '#EAB308', marginTop: 1, flexShrink: 0 }} />
                      {w}
                    </div>
                  ))}
                </div>
              )}

              {preview.insert_error_summary && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '10px 14px', background: 'rgba(239,68,68,0.06)', borderBottom: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 7, fontSize: 12, fontWeight: 600, color: 'var(--failure-text)' }}>
                    <TriangleAlert size={13} style={{ color: 'var(--failure)', marginTop: 1, flexShrink: 0 }} />
                    {preview.insert_error_summary} on insert
                  </div>
                  {errorGroups.map((g, i) => (
                    <div key={i} style={{ fontSize: 11.5, color: 'var(--text-2)', paddingLeft: 20 }}>
                      <span className="mono" style={{ color: 'var(--failure-text)' }}>{g.column ?? '(row)'}</span>
                      {' '}· {g.error_type.replace(/_/g, ' ')} · {formatRowNumbers(g.row_indices)}
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>{g.message}</div>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ overflow: 'auto', maxHeight: 320 }}>
                <table className="tbl">
                  <thead>
                    <tr>{preview.columns.map(c => <th key={c}>{c}</th>)}</tr>
                  </thead>
                  <tbody>
                    {preview.sample_rows.map((row, i) => (
                      <tr key={i} style={errorRowIndices.has(i) ? { background: 'rgba(239,68,68,0.07)' } : undefined}>
                        {(row as unknown[]).map((cell, j) => {
                          const isBadCell = errorCellKeys.has(`${i}:${preview.columns[j]}`)
                          return (
                            <td key={j} className="mono" style={{
                              fontSize: 12,
                              ...(isBadCell ? { background: 'rgba(239,68,68,0.16)', boxShadow: 'inset 0 0 0 1px rgba(239,68,68,0.4)' } : {}),
                            }}>
                              {String(cell ?? '')}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Archive + column mapping */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>Post-load</div>

            <div className="field">
              <label htmlFor="bulk-archive-dir">Archive directory (optional, supports variables)</label>
              <input id="bulk-archive-dir" className="input mono-input" value={archiveDir} onChange={e => setArchiveDir(e.target.value)} placeholder="/data/archive/{{ current_date }}/" />
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                <span style={{ fontSize: 10.5, color: 'var(--text-dim)' }}>Variables:</span>
                {VAR_HINTS.map(v => (
                  <button key={v} onClick={() => setArchiveDir(d => d + v)}
                    className="mono"
                    style={{ fontSize: 10.5, padding: '1px 6px', background: 'rgba(249,115,22,0.08)', color: 'var(--accent-h)', borderRadius: 3, border: '1px solid rgba(249,115,22,0.2)', cursor: 'pointer', fontFamily: 'var(--font-mono)' }}>
                    {v}
                  </button>
                ))}
              </div>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>Loaded files are moved here. Leave blank to leave files in place.</span>
            </div>

            <div className="field">
              <label htmlFor="bulk-col-mapping">Column mapping (JSON array) — optional</label>
              <textarea
                id="bulk-col-mapping"
                className="input mono-input"
                rows={5}
                value={colMapRaw}
                onChange={e => setColMapRaw(e.target.value)}
                placeholder={'[\n  { "source": "SOURCE_COL", "target": "target_col" }\n]'}
                style={{ height: 'auto', resize: 'vertical', fontSize: 12 }}
              />
              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
                Rename source columns to match the target table schema. Leave as <code style={{ color: 'var(--text-3)' }}>[]</code> to use source column names as-is.
              </span>
            </div>
          </div>

          {/* Output variable hint card */}
          <div className="card" style={{ background: 'rgba(251,146,60,0.04)', border: '1px solid rgba(251,146,60,0.15)' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-text)', marginBottom: 8 }}>Output variables</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12, color: 'var(--text-3)', lineHeight: 1.6 }}>
              <div>After this step runs, downstream steps can reference:</div>
              <code className="mono" style={{ fontSize: 11, color: 'var(--text-2)' }}>{'{{ steps.step_name.files_found }}'}</code>
              <code className="mono" style={{ fontSize: 11, color: 'var(--text-2)' }}>{'{{ steps.step_name.files_loaded }}'}</code>
              <code className="mono" style={{ fontSize: 11, color: 'var(--text-2)' }}>{'{{ steps.step_name.records_loaded }}'}</code>
              <code className="mono" style={{ fontSize: 11, color: 'var(--text-2)' }}>{'{{ steps.step_name.records_failed }}'}</code>
              <code className="mono" style={{ fontSize: 11, color: 'var(--text-2)' }}>{'{{ steps.step_name.duration_sec }}'}</code>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Use these in a follow-up email step to send a load summary.</div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
