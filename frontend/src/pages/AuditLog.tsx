import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Filter, ChevronLeft, ChevronRight, User, Hash, Clock, Server, Download } from 'lucide-react'
import { getAuditLogs, exportAuditLogs } from '../lib/api'
import TopBar from '../components/shared/TopBar'
import PageIntro from '../components/shared/PageIntro'
import Sk from '../components/shared/Skeleton'

export default function AuditLog() {
  const [page, setPage] = useState(1)
  const [actionFilter, setActionFilter] = useState('')
  const [userFilter, setUserFilter] = useState('')
  const [exporting, setExporting] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['audit-logs', page, actionFilter, userFilter],
    queryFn: () => getAuditLogs({ page, action: actionFilter || undefined, username: userFilter || undefined }),
    staleTime: 10_000,
  })

  async function handleExport() {
    setExporting(true)
    try {
      await exportAuditLogs({ action: actionFilter || undefined, username: userFilter || undefined })
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Export failed')
    } finally {
      setExporting(false)
    }
  }

  return (
    <>
      <TopBar crumbs={['Workspace', 'Audit Log']} helpTopic="audit" />
      <div className="scroll">
        <PageIntro page="audit" />
        <div className="page-h">
          <div>
            <h1>Audit Log</h1>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>System-wide compliance and security events.</div>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div className="input-wrap">
              <Filter size={13} style={{ color: 'var(--text-muted)' }} />
              <input
                className="input input-sm"
                placeholder="Filter by action…"
                value={actionFilter}
                onChange={e => { setActionFilter(e.target.value); setPage(1) }}
                style={{ width: 140 }}
              />
            </div>
            <div className="input-wrap">
              <User size={13} style={{ color: 'var(--text-muted)' }} />
              <input
                className="input input-sm"
                placeholder="Filter by user…"
                value={userFilter}
                onChange={e => { setUserFilter(e.target.value); setPage(1) }}
                style={{ width: 140 }}
              />
            </div>
            <button className="btn btn-sm btn-ghost" onClick={handleExport} disabled={exporting}>
              <Download size={13} /> {exporting ? 'Exporting…' : 'Export to CSV'}
            </button>
          </div>
        </div>

        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {error ? (
            <div style={{ padding: 20, color: 'var(--failure)', textAlign: 'center', fontSize: 13 }}>Failed to load audit logs.</div>
          ) : isLoading ? (
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ paddingLeft: 20, width: 160 }}><Clock size={11} style={{ display: 'inline', marginRight: 4 }} /> Timestamp</th>
                  <th style={{ width: 140 }}><Hash size={11} style={{ display: 'inline', marginRight: 4 }} /> Action</th>
                  <th style={{ width: 120 }}><User size={11} style={{ display: 'inline', marginRight: 4 }} /> User</th>
                  <th style={{ width: 140 }}><Server size={11} style={{ display: 'inline', marginRight: 4 }} /> IP Address</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 10 }, (_, i) => i).map(n => (
                  <tr key={'sk-' + n}>
                    <td style={{ paddingLeft: 20 }}><Sk h={12} style={{ width: 130 }} /></td>
                    <td><Sk h={18} r={4} style={{ width: 90 }} /></td>
                    <td><Sk h={12} style={{ width: 80 }} /></td>
                    <td><Sk h={12} style={{ width: 100 }} /></td>
                    <td><Sk h={12} style={{ width: '70%' }} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : data?.logs.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>No audit events found.</div>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ paddingLeft: 20, width: 160 }}><Clock size={11} style={{ display: 'inline', marginRight: 4 }} /> Timestamp</th>
                  <th style={{ width: 140 }}><Hash size={11} style={{ display: 'inline', marginRight: 4 }} /> Action</th>
                  <th style={{ width: 120 }}><User size={11} style={{ display: 'inline', marginRight: 4 }} /> User</th>
                  <th style={{ width: 140 }}><Server size={11} style={{ display: 'inline', marginRight: 4 }} /> IP Address</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {data?.logs.map(log => {
                  const ts = log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A'
                  return (
                    <tr key={log.id}>
                      <td style={{ paddingLeft: 20, fontSize: 11.5, color: 'var(--text-2)' }} className="mono">{ts}</td>
                      <td>
                        <span style={{
                          background: 'var(--surface-2)', padding: '2px 6px', borderRadius: 4,
                          fontSize: 10.5, fontWeight: 600, color: 'var(--text-2)'
                        }} className="mono">
                          {log.action}
                        </span>
                      </td>
                      <td style={{ fontWeight: 500 }}>{log.username}</td>
                      <td className="mono" style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{log.ip_address || '—'}</td>
                      <td className="mono" style={{ fontSize: 11, color: 'var(--text-3)', wordBreak: 'break-all' }}>
                        {Object.keys(log.details).length > 0 ? JSON.stringify(log.details) : ''}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
          {data && data.pages > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', borderTop: '1px solid var(--border)' }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Page {data.page} of {data.pages} ({data.total} records)
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  className="btn btn-sm"
                  disabled={page <= 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  <ChevronLeft size={14} /> Prev
                </button>
                <button
                  className="btn btn-sm"
                  disabled={page >= data.pages}
                  onClick={() => setPage(p => p + 1)}
                >
                  Next <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
