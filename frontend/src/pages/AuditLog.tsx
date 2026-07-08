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
            <div className="text-[13px] text-text-muted mt-1">System-wide compliance and security events.</div>
          </div>
          <div className="flex gap-2.5 items-center">
            <div className="flex items-center gap-1.5 bg-surface border border-border rounded-r px-3 h-[34px] w-[140px]">
              <Filter size={13} className="text-text-muted shrink-0" />
              <input
                className="bg-transparent border-none outline-none text-text-primary text-[13px] font-[inherit] flex-1 min-w-0"
                placeholder="Filter by action…"
                value={actionFilter}
                onChange={e => { setActionFilter(e.target.value); setPage(1) }}
              />
            </div>
            <div className="flex items-center gap-1.5 bg-surface border border-border rounded-r px-3 h-[34px] w-[140px]">
              <User size={13} className="text-text-muted shrink-0" />
              <input
                className="bg-transparent border-none outline-none text-text-primary text-[13px] font-[inherit] flex-1 min-w-0"
                placeholder="Filter by user…"
                value={userFilter}
                onChange={e => { setUserFilter(e.target.value); setPage(1) }}
              />
            </div>
            <button className="btn btn-sm btn-ghost" onClick={handleExport} disabled={exporting}>
              <Download size={13} /> {exporting ? 'Exporting…' : 'Export to CSV'}
            </button>
          </div>
        </div>

        <div className="card p-0 overflow-hidden">
          {error ? (
            <div className="p-5 text-failure text-center text-[13px]">Failed to load audit logs.</div>
          ) : isLoading ? (
            <table className="tbl">
              <thead>
                <tr>
                  <th className="pl-5 w-[160px]"><Clock size={11} className="inline mr-1" /> Timestamp</th>
                  <th className="w-[140px]"><Hash size={11} className="inline mr-1" /> Action</th>
                  <th className="w-[120px]"><User size={11} className="inline mr-1" /> User</th>
                  <th className="w-[140px]"><Server size={11} className="inline mr-1" /> IP Address</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 10 }, (_, i) => i).map(n => (
                  <tr key={'sk-' + n}>
                    <td className="pl-5"><Sk h={12} style={{ width: 130 }} /></td>
                    <td><Sk h={18} r={4} style={{ width: 90 }} /></td>
                    <td><Sk h={12} style={{ width: 80 }} /></td>
                    <td><Sk h={12} style={{ width: 100 }} /></td>
                    <td><Sk h={12} style={{ width: '70%' }} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : data?.logs.length === 0 ? (
            <div className="p-10 text-center text-text-muted">No audit events found.</div>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th className="pl-5 w-[160px]"><Clock size={11} className="inline mr-1" /> Timestamp</th>
                  <th className="w-[140px]"><Hash size={11} className="inline mr-1" /> Action</th>
                  <th className="w-[120px]"><User size={11} className="inline mr-1" /> User</th>
                  <th className="w-[140px]"><Server size={11} className="inline mr-1" /> IP Address</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {data?.logs.map(log => {
                  const ts = log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A'
                  return (
                    <tr key={log.id}>
                      <td className="mono pl-5 text-[11.5px]">{ts}</td>
                      <td>
                        <span className="mono bg-surface2 py-0.5 px-1.5 rounded text-[10.5px] font-semibold text-text-2">
                          {log.action}
                        </span>
                      </td>
                      <td className="font-medium">{log.username}</td>
                      <td className="mono text-[11.5px] text-text-muted">{log.ip_address || '—'}</td>
                      <td className="mono text-[11px] text-text-3 break-all">
                        {Object.keys(log.details).length > 0 ? JSON.stringify(log.details) : ''}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-between py-3 px-5 border-t border-border">
              <div className="text-xs text-text-muted">
                Page {data.page} of {data.pages} ({data.total} records)
              </div>
              <div className="flex gap-1.5">
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
