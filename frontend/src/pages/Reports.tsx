import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { getReportConfigs, deleteReportConfig } from '../lib/api'
import PageHeader from '../components/shared/PageHeader'
import EmptyState from '../components/shared/EmptyState'
import Spinner from '../components/shared/Spinner'

const FORMAT_BADGES: Record<string, string> = {
  excel: 'badge-success',
  csv:   'badge-accent',
  pdf:   'badge-running',
}

export default function Reports() {
  const qc = useQueryClient()
  const { data: configs = [], isLoading } = useQuery({ queryKey: ['report-configs'], queryFn: getReportConfigs })
  const { mutate: remove } = useMutation({
    mutationFn: deleteReportConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['report-configs'] }),
  })

  if (isLoading) return <div className="p-8 flex justify-center"><Spinner /></div>

  return (
    <div className="p-8">
      <PageHeader title="Report Configs" subtitle={`${configs.length} configured`}
        action={<Link to="/reports/new" className="btn-primary"><Plus size={15}/> New Report</Link>} />

      {configs.length === 0 ? (
        <EmptyState message="No report configs yet." action={<Link to="/reports/new" className="btn-primary">Create report config</Link>} />
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-border">
              <tr className="text-xs text-text-muted">
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Format</th>
                <th className="text-left px-4 py-3">Output filename</th>
                <th className="px-4 py-3"/>
              </tr>
            </thead>
            <tbody>
              {configs.map(c => (
                <tr key={c.id} className="border-b border-border/50 last:border-0 hover:bg-surface2/50">
                  <td className="px-4 py-3">
                    <Link to={`/reports/${c.id}/edit`} className="font-medium text-text-primary hover:text-accent">{c.name}</Link>
                    {c.description && <div className="text-xs text-text-muted">{c.description}</div>}
                  </td>
                  <td className="px-4 py-3"><span className={FORMAT_BADGES[c.format] ?? 'badge-muted'}>{c.format.toUpperCase()}</span></td>
                  <td className="px-4 py-3 font-mono text-xs text-text-muted">{c.output_filename}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 justify-end">
                      <Link to={`/reports/${c.id}/edit`} className="btn-ghost p-1.5"><Pencil size={14}/></Link>
                      <button className="btn-ghost p-1.5 hover:text-danger" onClick={() => window.confirm(`Delete "${c.name}"?`) && remove(c.id)}><Trash2 size={14}/></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
