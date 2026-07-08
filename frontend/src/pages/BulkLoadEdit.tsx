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
import Sk from '../components/shared/Skeleton'

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
    <>
      <TopBar crumbs={crumbs} />
      <div className="scroll grid grid-cols-[300px_1fr] gap-5 items-start">
        <div className="flex flex-col gap-3.5">
          {[['Details', 2], ['Target database', 4]].map(([label, rows]) => (
            <div key={label as string} className="card flex flex-col gap-3">
              <Sk h={12} style={{ width: 70 }} />
              {Array.from({ length: rows as number }, (_, i) => i).map(n => (
                <div key={'sk-' + n} className="field">
                  <Sk h={11} style={{ width: 80, marginBottom: 6 }} />
                  <Sk h={34} r={6} />
                </div>
              ))}
            </div>
          ))}
        </div>
        <div className="flex flex-col gap-3.5">
          {[['Source files', 4], ['Post-load', 2]].map(([label, rows]) => (
            <div key={label as string} className="card flex flex-col gap-3">
              <Sk h={12} style={{ width: 90 }} />
              {Array.from({ length: rows as number }, (_, i) => i).map(n => (
                <div key={'sk-' + n} className="field">
                  <Sk h={11} style={{ width: 100, marginBottom: 6 }} />
                  <Sk h={34} r={6} />
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </>
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
          <div className="flex gap-3 items-center">
            <label className="flex items-center gap-1.5 text-[11.5px] text-text-muted cursor-pointer">
              <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} />
              Attempt insert (rolled back)
            </label>
            <div className="flex gap-2">
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

      <div className="scroll grid grid-cols-[300px_1fr] gap-5 items-start">
        {/* Left: details + source */}
        <div className="flex flex-col gap-3.5">
          <div>
            <h1 className="text-xl font-semibold tracking-[-0.02em] m-0 mb-1 text-text-primary">{name || 'New Bulk Load'}</h1>
            {desc && <p className="text-text-muted text-[12.5px] m-0">{desc}</p>}
          </div>

          {error && (
            <div className="py-2 px-3 bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-[7px] text-[12.5px] text-failure-text">
              {error}
            </div>
          )}

          {/* Details */}
          <div className="card flex flex-col gap-3">
            <div className="text-xs font-semibold mb-0.5">Details</div>
            <div className="field">
              <label htmlFor="bulk-name">Name *</label>
              <input id="bulk-name" className="input" value={name} onChange={e => { setName(e.target.value); if (fieldErrors.name) setFieldErrors(f => ({ ...f, name: '' })) }} placeholder="Daily subscriber load" />
              {fieldErrors.name && <span className="text-[11.5px] text-failure">{fieldErrors.name}</span>}
            </div>
            <div className="field">
              <label htmlFor="bulk-desc">Description</label>
              <input id="bulk-desc" className="input" value={desc} onChange={e => setDesc(e.target.value)} />
            </div>
          </div>

          {/* Connection */}
          <div className="card flex flex-col gap-3">
            <div className="text-xs font-semibold mb-0.5">Target database</div>
            <div className="field">
              <label htmlFor="bulk-connection">Connection</label>
              <select id="bulk-connection" className="input" value={connId} onChange={e => setConnId(e.target.value)}>
                <option value="">Select connection…</option>
                {dbConns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="bulk-target-table">Target table *</label>
              <input id="bulk-target-table" className="input mono-input" value={targetTable}
                onChange={e => { setTargetTable(e.target.value); if (fieldErrors.targetTable) setFieldErrors(f => ({ ...f, targetTable: '' })) }}
                placeholder="STAGING.SUBSCRIPTIONS" />
              {fieldErrors.targetTable && <span className="text-[11.5px] text-failure">{fieldErrors.targetTable}</span>}
            </div>
            <div className="field">
              <label htmlFor="bulk-load-mode">Load mode</label>
              <select id="bulk-load-mode" className="input" value={loadMode} onChange={e => setLoadMode(e.target.value)}>
                <option value="append">Append — insert rows without touching existing data</option>
                <option value="replace">Replace — truncate table then insert</option>
              </select>
            </div>
            <div className="field">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={useSqlLoader} onChange={e => setUseSqlLoader(e.target.checked)} />{' '}
                Use SQL*Loader (Oracle only)
              </label>
              <span className="text-[11px] text-text-muted mt-[3px]">
                Direct-path load via sqlldr subprocess. Fastest for Oracle bulk inserts.
                Known gap: "Attempt insert" dry-run testing isn't available on this path (sqlldr manages
                its own commits) — Test File still checks the file, header, and target columns.
              </span>
            </div>
          </div>
        </div>

        {/* Right: source config + advanced */}
        <div className="flex flex-col gap-3.5">
          {/* Source */}
          <div className="card flex flex-col gap-3">
            <div className="text-xs font-semibold mb-0.5">Source files</div>

            <div className="field">
              <label htmlFor="bulk-source-dir">Source directory *</label>
              <input id="bulk-source-dir" className="input mono-input" value={sourceDir}
                onChange={e => { setSourceDir(e.target.value); if (fieldErrors.sourceDir) setFieldErrors(f => ({ ...f, sourceDir: '' })) }}
                placeholder="/data/incoming/" />
              {fieldErrors.sourceDir && <span className="text-[11.5px] text-failure">{fieldErrors.sourceDir}</span>}
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div className="field">
                <label htmlFor="bulk-file-prefix">File prefix (optional)</label>
                <input id="bulk-file-prefix" className="input mono-input" value={filePrefix} onChange={e => setFilePrefix(e.target.value)} placeholder="SUBS_" />
                <span className="text-[11px] text-text-muted mt-[3px]">Only load files starting with this.</span>
              </div>
              <div className="field">
                <label htmlFor="bulk-file-prefix-exclude">Exclude prefix (optional)</label>
                <input id="bulk-file-prefix-exclude" className="input mono-input" value={filePrefixExclude} onChange={e => setFilePrefixExclude(e.target.value)} placeholder="SUBS_OLD_" />
                <span className="text-[11px] text-text-muted mt-[3px]">Skip files starting with this.</span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2.5">
              <div className="field">
                <label htmlFor="bulk-file-type">File type</label>
                <select id="bulk-file-type" className="input" value={fileType} onChange={e => setFileType(e.target.value)}>
                  <option value="csv">CSV</option>
                  <option value="xlsx">Excel (.xlsx)</option>
                  <option value="txt">TXT</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="bulk-delimiter">Delimiter</label>
                <input id="bulk-delimiter" className="input mono-input !w-[70px]" value={delimiter} onChange={e => setDelimiter(e.target.value)} maxLength={3} />
              </div>
              <div className="field">
                <label htmlFor="bulk-on-no-files">On no files</label>
                <select id="bulk-on-no-files" className="input" value={onNoFiles} onChange={e => setOnNoFiles(e.target.value)}>
                  <option value="skip">Skip (succeed)</option>
                  <option value="fail">Fail</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
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
            <div className="py-2 px-3 bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-[7px] text-[12.5px] text-failure-text">
              {testError}
            </div>
          )}

          {preview && (
            <div className="card overflow-hidden !p-0">
              <div className="flex items-center justify-between py-2.5 px-3.5 border-b border-border">
                <span className="text-xs text-text-primary font-semibold">
                  Preview · <span className="mono">{preview.file_name}</span>
                </span>
                <span className="text-[10.5px] text-text-muted">
                  {preview.files_matched} file{preview.files_matched === 1 ? '' : 's'} matched · showing {preview.row_count_sampled} row{preview.row_count_sampled === 1 ? '' : 's'}
                </span>
              </div>

              {preview.warnings.length > 0 && (
                <div className="flex flex-col gap-1.5 py-2.5 px-3.5 bg-[rgba(234,179,8,0.06)] border-b border-border">
                  {preview.warnings.map((w, i) => (
                    <div key={i} className="flex items-start gap-[7px] text-xs text-text-2">
                      <TriangleAlert size={13} className="text-yellow-500 mt-px shrink-0" />
                      {w}
                    </div>
                  ))}
                </div>
              )}

              {preview.insert_error_summary && (
                <div className="flex flex-col gap-2 py-2.5 px-3.5 bg-[rgba(239,68,68,0.06)] border-b border-border">
                  <div className="flex items-start gap-[7px] text-xs font-semibold text-failure-text">
                    <TriangleAlert size={13} className="text-failure mt-px shrink-0" />
                    {preview.insert_error_summary} on insert
                  </div>
                  {errorGroups.map((g, i) => (
                    <div key={i} className="text-[11.5px] text-text-2 pl-5">
                      <span className="mono text-failure-text">{g.column ?? '(row)'}</span>
                      {' '}· {g.error_type.replace(/_/g, ' ')} · {formatRowNumbers(g.row_indices)}
                      <div className="text-[11px] text-text-muted mt-px">{g.message}</div>
                    </div>
                  ))}
                </div>
              )}

              <div className="overflow-auto max-h-80">
                <table className="tbl">
                  <thead>
                    <tr>{preview.columns.map(c => <th key={c}>{c}</th>)}</tr>
                  </thead>
                  <tbody>
                    {preview.sample_rows.map((row, i) => (
                      <tr key={i} className={errorRowIndices.has(i) ? 'bg-[rgba(239,68,68,0.07)]' : undefined}>
                        {(row as unknown[]).map((cell, j) => {
                          const isBadCell = errorCellKeys.has(`${i}:${preview.columns[j]}`)
                          return (
                            <td key={j} className={`mono text-xs${isBadCell ? ' bg-[rgba(239,68,68,0.16)] shadow-[inset_0_0_0_1px_rgba(239,68,68,0.4)]' : ''}`}>
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
          <div className="card flex flex-col gap-3">
            <div className="text-xs font-semibold mb-0.5">Post-load</div>

            <div className="field">
              <label htmlFor="bulk-archive-dir">Archive directory (optional, supports variables)</label>
              <input id="bulk-archive-dir" className="input mono-input" value={archiveDir} onChange={e => setArchiveDir(e.target.value)} placeholder="/data/archive/{{ current_date }}/" />
              <div className="flex flex-wrap gap-1 mt-1.5">
                <span className="text-[10.5px] text-text-dim">Variables:</span>
                {VAR_HINTS.map(v => (
                  <button key={v} onClick={() => setArchiveDir(d => d + v)}
                    className="mono text-[10.5px] py-px px-1.5 bg-[rgba(249,115,22,0.08)] text-accent-hover rounded-[3px] border border-[rgba(249,115,22,0.2)] cursor-pointer font-mono">
                    {v}
                  </button>
                ))}
              </div>
              <span className="text-[11px] text-text-muted mt-[3px]">Loaded files are moved here. Leave blank to leave files in place.</span>
            </div>

            <div className="field">
              <label htmlFor="bulk-col-mapping">Column mapping (JSON array) — optional</label>
              <textarea
                id="bulk-col-mapping"
                className="input mono-input !h-auto !resize-y !text-xs"
                rows={5}
                value={colMapRaw}
                onChange={e => setColMapRaw(e.target.value)}
                placeholder={'[\n  { "source": "SOURCE_COL", "target": "target_col" }\n]'}
              />
              <span className="text-[11px] text-text-muted mt-[3px]">
                Rename source columns to match the target table schema. Leave as <code className="text-text-3">[]</code> to use source column names as-is.
              </span>
            </div>
          </div>

          {/* Output variable hint card */}
          <div className="card !bg-[rgba(251,146,60,0.04)] !border-[rgba(251,146,60,0.15)]">
            <div className="text-xs font-semibold text-accent-text mb-2">Output variables</div>
            <div className="flex flex-col gap-1 text-xs text-text-3 leading-[1.6]">
              <div>After this step runs, downstream steps can reference:</div>
              <code className="mono text-[11px] text-text-2">{'{{ steps.step_name.files_found }}'}</code>
              <code className="mono text-[11px] text-text-2">{'{{ steps.step_name.files_loaded }}'}</code>
              <code className="mono text-[11px] text-text-2">{'{{ steps.step_name.records_loaded }}'}</code>
              <code className="mono text-[11px] text-text-2">{'{{ steps.step_name.records_failed }}'}</code>
              <code className="mono text-[11px] text-text-2">{'{{ steps.step_name.duration_sec }}'}</code>
              <div className="text-[11px] text-text-muted mt-1">Use these in a follow-up email step to send a load summary.</div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
