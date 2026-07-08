import { Trash2 } from 'lucide-react'
import type { Pipeline, PipelineDep } from '../../lib/types'

export default function DependenciesCard({
  upstreamDeps, setUpstreamDeps, allPipelines, thisPipelineId,
}: {
  upstreamDeps: PipelineDep[]
  setUpstreamDeps: React.Dispatch<React.SetStateAction<PipelineDep[]>>
  allPipelines: Pipeline[]
  thisPipelineId: string | undefined
}) {
  const available = allPipelines.filter(
    p => p.id !== thisPipelineId && !upstreamDeps.some(d => d.pipeline_id === p.id)
  )

  function addDep(pipelineId: string) {
    const p = allPipelines.find(x => x.id === pipelineId)
    if (!p) return
    setUpstreamDeps(prev => [...prev, { dep_id: `_new_${Date.now()}`, pipeline_id: p.id, pipeline_name: p.name }])
  }

  return (
    <div className="card mb-4">
      <div className="flex items-center justify-between mb-2.5">
        <div>
          <span className="text-xs font-semibold text-[var(--text)]">Upstream Dependencies</span>
          <span className="text-[11px] text-[var(--text-muted)] ml-2">
            this pipeline runs automatically when all listed pipelines succeed
          </span>
        </div>
      </div>

      {upstreamDeps.length === 0 ? (
        <p className="text-xs text-[var(--text-muted)] m-0">
          No dependencies. This pipeline runs on its own schedule or when triggered manually.
        </p>
      ) : (
        <div className="flex flex-col gap-1.5 mb-2.5">
          {upstreamDeps.map(dep => (
            <div key={dep.dep_id} className="flex items-center gap-2">
              <span className="text-xs text-text-2 flex-1 py-1 px-2 bg-surface2 rounded-[5px] border border-border">
                {dep.pipeline_name}
              </span>
              <button
                type="button"
                onClick={() => setUpstreamDeps(prev => prev.filter(d => d.dep_id !== dep.dep_id))}
                className="bg-transparent border-none cursor-pointer text-failure py-0.5 px-1"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {available.length > 0 && (
        <select
          className="input !text-xs max-w-[320px]"
          value=""
          onChange={e => { if (e.target.value) addDep(e.target.value) }}
        >
          <option value="">+ Add upstream dependency…</option>
          {available.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      )}
    </div>
  )
}
