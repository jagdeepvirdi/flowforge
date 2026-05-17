import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2, Play, Calendar } from 'lucide-react'
import { getPipelines, deletePipeline, runPipeline } from '../lib/api'
import PageHeader from '../components/shared/PageHeader'
import EmptyState from '../components/shared/EmptyState'
import Spinner from '../components/shared/Spinner'

export default function Pipelines() {
  const qc = useQueryClient()
  const { data: pipelines = [], isLoading } = useQuery({
    queryKey: ['pipelines'],
    queryFn: getPipelines,
  })

  const { mutate: remove } = useMutation({
    mutationFn: deletePipeline,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })
  const { mutate: trigger } = useMutation({
    mutationFn: runPipeline,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })

  if (isLoading) return <div className="p-8 flex justify-center"><Spinner /></div>

  return (
    <div className="p-8">
      <PageHeader
        title="Pipelines"
        subtitle={`${pipelines.length} pipeline${pipelines.length !== 1 ? 's' : ''}`}
        action={
          <Link to="/pipelines/new" className="btn-primary">
            <Plus size={15} /> New Pipeline
          </Link>
        }
      />

      {pipelines.length === 0 ? (
        <EmptyState
          message="No pipelines yet."
          action={<Link to="/pipelines/new" className="btn-primary">Create your first pipeline</Link>}
        />
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-border">
              <tr className="text-xs text-text-muted">
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Schedule</th>
                <th className="text-left px-4 py-3">Steps</th>
                <th className="text-left px-4 py-3">Enabled</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {pipelines.map(p => (
                <tr key={p.id} className="border-b border-border/50 last:border-0 hover:bg-surface2/50">
                  <td className="px-4 py-3">
                    <Link to={`/pipelines/${p.id}/edit`} className="font-medium text-text-primary hover:text-accent">
                      {p.name}
                    </Link>
                    {p.description && <div className="text-xs text-text-muted">{p.description}</div>}
                  </td>
                  <td className="px-4 py-3">
                    {p.schedule
                      ? <span className="font-mono text-xs bg-surface2 px-2 py-0.5 rounded flex items-center gap-1 w-fit"><Calendar size={10}/>{p.schedule}</span>
                      : <span className="text-text-muted">—</span>}
                  </td>
                  <td className="px-4 py-3 text-text-muted">{p.steps.length}</td>
                  <td className="px-4 py-3">
                    <span className={p.enabled ? 'text-success text-xs' : 'text-text-muted text-xs'}>
                      {p.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <button
                        className="btn-ghost p-1.5"
                        onClick={() => trigger(p.id)}
                        title="Run now"
                        disabled={!p.enabled}
                      >
                        <Play size={14} />
                      </button>
                      <Link to={`/pipelines/${p.id}/edit`} className="btn-ghost p-1.5" title="Edit">
                        <Pencil size={14} />
                      </Link>
                      <button
                        className="btn-ghost p-1.5 hover:text-danger"
                        onClick={() => window.confirm(`Delete "${p.name}"?`) && remove(p.id)}
                        title="Delete"
                      >
                        <Trash2 size={14} />
                      </button>
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
