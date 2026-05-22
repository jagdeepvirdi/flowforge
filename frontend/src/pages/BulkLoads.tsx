import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Pencil, Search } from 'lucide-react'
import { getPipelines } from '../lib/api'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import PageIntro from '../components/shared/PageIntro'

interface BulkLoadRow {
  pipelineId:   string
  pipelineName: string
  stepName:     string
  stepOrder:    number
  sourceDir:    string
  filePrefix:   string
  fileType:     string
  targetTable:  string
  loadMode:     string
  archiveDir:   string
  onNoFiles:    string
  useSqlLoader: boolean
  enabled:      boolean
}

export default function BulkLoads() {
  const [search, setSearch] = useState('')

  const { data: pipelines = [], isLoading } = useQuery({
    queryKey: ['pipelines'],
    queryFn: getPipelines,
  })

  const rows: BulkLoadRow[] = []
  for (const p of pipelines) {
    for (const s of p.steps) {
      if (s.step_type !== 'bulk_load') continue
      const cfg = s.config as Record<string, unknown>
      rows.push({
        pipelineId:   p.id,
        pipelineName: p.name,
        stepName:     s.name,
        stepOrder:    s.step_order,
        sourceDir:    String(cfg.source_directory ?? ''),
        filePrefix:   String(cfg.file_prefix ?? ''),
        fileType:     String(cfg.file_type ?? 'csv'),
        targetTable:  String(cfg.target_table ?? ''),
        loadMode:     String(cfg.load_mode ?? 'append'),
        archiveDir:   String(cfg.archive_directory ?? ''),
        onNoFiles:    String(cfg.on_no_files ?? 'skip'),
        useSqlLoader: Boolean(cfg.use_sqlloader),
        enabled:      s.enabled,
      })
    }
  }

  const filtered = rows.filter(r => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      r.stepName.toLowerCase().includes(q) ||
      r.pipelineName.toLowerCase().includes(q) ||
      r.sourceDir.toLowerCase().includes(q) ||
      r.targetTable.toLowerCase().includes(q)
    )
  })

  if (isLoading) return (
    <><TopBar crumbs={['Workspace', 'Bulk Loads']} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
  )

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Bulk Loads']}
        helpTopic="pipelines"
        actions={
          <Link to="/pipelines/new" className="btn btn-primary btn-sm">
            + New Pipeline
          </Link>
        }
      />

      <div className="scroll">
        <PageIntro page="pipelines" />

        <div className="page-h">
          <div>
            <h1>Bulk Loads</h1>
            <p>{rows.length} bulk load step{rows.length !== 1 ? 's' : ''} across {pipelines.length} pipeline{pipelines.length !== 1 ? 's' : ''}</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#1A1D27', border: '1px solid #2D3143', borderRadius: 8, padding: '0 12px', height: 34, flex: 1, maxWidth: 360 }}>
            <Search size={14} style={{ color: '#64748B' }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ background: 'transparent', border: 'none', outline: 'none', color: '#F1F5F9', fontSize: 13, fontFamily: 'inherit', flex: 1 }}
              placeholder="Filter by step, pipeline, table…"
            />
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="card ff-empty">
            <p className="msg">
              {search
                ? 'No bulk load steps match your filter.'
                : 'No bulk_load steps found. Add one to any pipeline via the Pipeline Builder.'}
            </p>
            {!search && (
              <Link to="/pipelines/new" className="btn btn-primary">Create a pipeline</Link>
            )}
          </div>
        ) : (
          <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Step</th>
                  <th>Pipeline</th>
                  <th>Source directory</th>
                  <th>Target table</th>
                  <th style={{ width: 80 }}>Type</th>
                  <th style={{ width: 80 }}>Mode</th>
                  <th style={{ width: 44 }} />
                </tr>
              </thead>
              <tbody>
                {filtered.map((r, i) => (
                  <tr key={i} style={{ opacity: r.enabled ? 1 : 0.5 }}>
                    <td>
                      <div style={{ fontWeight: 500, color: '#F1F5F9' }}>{r.stepName}</div>
                      {r.filePrefix && (
                        <div className="mono" style={{ fontSize: 11, color: '#64748B', marginTop: 2 }}>
                          prefix: {r.filePrefix}
                        </div>
                      )}
                    </td>
                    <td>
                      <Link
                        to={`/pipelines/${r.pipelineId}/edit`}
                        style={{ color: '#94A3B8', textDecoration: 'none', fontSize: 13 }}
                        onMouseEnter={e => (e.currentTarget.style.color = '#FB923C')}
                        onMouseLeave={e => (e.currentTarget.style.color = '#94A3B8')}
                      >
                        {r.pipelineName}
                      </Link>
                    </td>
                    <td className="mono" style={{ fontSize: 12, color: '#CBD5E1' }}>
                      {r.sourceDir || <span style={{ color: '#475569' }}>—</span>}
                    </td>
                    <td className="mono" style={{ fontSize: 12, color: '#CBD5E1' }}>
                      {r.targetTable || <span style={{ color: '#475569' }}>—</span>}
                    </td>
                    <td>
                      <span className="tbadge tbadge-bulk" style={{ fontSize: 10 }}>
                        {r.fileType.toUpperCase()}
                        {r.useSqlLoader ? ' · sqlldr' : ''}
                      </span>
                    </td>
                    <td style={{ color: '#94A3B8', fontSize: 12 }}>{r.loadMode}</td>
                    <td>
                      <Link
                        to={`/pipelines/${r.pipelineId}/edit`}
                        className="btn btn-sm btn-ghost btn-icon"
                        title="Edit pipeline"
                      >
                        <Pencil size={12} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
