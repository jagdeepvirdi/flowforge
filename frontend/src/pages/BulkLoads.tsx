import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { getBulkLoadConfigs, deleteBulkLoadConfig, cloneBulkLoadConfig, validateBulkLoadConfig, type BulkLoadPreview } from '../lib/api'
import TopBar from '../components/shared/TopBar'
import Sk from '../components/shared/Skeleton'
import PageIntro from '../components/shared/PageIntro'
import BulkLoadRow from '../components/bulkloads/BulkLoadRow'

export default function BulkLoads() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { data: configs = [], isLoading } = useQuery({
    queryKey: ['bulk-load-configs'],
    queryFn: getBulkLoadConfigs,
  })
  const { mutate: remove } = useMutation({
    mutationFn: deleteBulkLoadConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bulk-load-configs'] }),
  })
  const { mutate: clone } = useMutation({
    mutationFn: cloneBulkLoadConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bulk-load-configs'] }),
  })

  const [testStatuses, setTestStatuses] = useState<Record<string, 'testing' | 'ok' | 'warn' | 'fail'>>({})
  const [testErrors, setTestErrors]     = useState<Record<string, string>>({})
  const [testResults, setTestResults]   = useState<Record<string, BulkLoadPreview>>({})

  const testConfig = (id: string) => {
    setTestStatuses(s => ({ ...s, [id]: 'testing' }))
    setTestErrors(e => ({ ...e, [id]: '' }))
    validateBulkLoadConfig(id)
      .then(result => {
        setTestResults(r => ({ ...r, [id]: result }))
        const hasIssues = result.warnings.length > 0 || (result.error_groups?.length ?? 0) > 0
        setTestStatuses(s => ({ ...s, [id]: hasIssues ? 'warn' : 'ok' }))
      })
      .catch((err: Error) => {
        console.error('Bulk load test failed:', err.message)
        setTestStatuses(s => ({ ...s, [id]: 'fail' }))
        setTestErrors(e => ({ ...e, [id]: err.message }))
      })
  }

  if (isLoading) return (
    <>
      <TopBar crumbs={['Workspace', 'Bulk Loads']} />
      <div className="scroll">
        <div className="page-h">
          <div className="flex flex-col gap-2">
            <Sk h={28} r={6} style={{ width: 140 }} />
            <Sk h={14} style={{ width: 180 }} />
          </div>
        </div>
        <div className="flex flex-col gap-2.5">
          {[0, 1, 2].map(i => (
            <div key={i} className="card">
              <div className="flex items-center gap-3.5">
                <Sk h={40} r={9} style={{ width: 40, flexShrink: 0 }} />
                <div className="flex-1 flex flex-col gap-1.5">
                  <div className="flex gap-2.5 items-center">
                    <Sk h={14} style={{ width: 160 }} />
                    <Sk h={14} r={4} style={{ width: 50 }} />
                  </div>
                  <Sk h={11} style={{ width: 220 }} />
                </div>
                <div className="flex gap-6 shrink-0">
                  {[50, 40].map(w => (
                    <div key={w} className="flex flex-col gap-1 min-w-[70px]">
                      <Sk h={10} style={{ width: 40 }} />
                      <Sk h={12} style={{ width: w }} />
                    </div>
                  ))}
                </div>
                <div className="flex gap-1.5 shrink-0">
                  <Sk h={28} r={6} style={{ width: 62 }} />
                  <Sk h={28} r={6} style={{ width: 30 }} />
                  <Sk h={28} r={6} style={{ width: 30 }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  )

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Bulk Loads']}
        helpTopic="pipelines"
        actions={
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/bulk-loads/new')}>
            <Plus size={13} /> New Bulk Load
          </button>
        }
      />

      <div className="scroll">
        <PageIntro page="pipelines" />

        <div className="page-h">
          <div>
            <h1>Bulk Loads</h1>
            <p>{configs.length} bulk load config{configs.length === 1 ? '' : 's'} · click Test to preview the current matching file</p>
          </div>
        </div>

        {configs.length === 0 ? (
          <div className="card ff-empty">
            <p className="msg">No bulk load configs yet.</p>
            <p className="text-[12.5px] text-text-muted m-0 mb-3.5">
              A bulk load config defines the source directory, file pattern, and target table.
              Once created, reference it in a pipeline's Bulk Load step.
            </p>
            <button className="btn btn-primary" onClick={() => navigate('/bulk-loads/new')}>Create first bulk load config</button>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {configs.map(c => (
              <BulkLoadRow
                key={c.id}
                config={c}
                testStatus={testStatuses[c.id]}
                testError={testErrors[c.id]}
                testResult={testResults[c.id]}
                onTest={() => testConfig(c.id)}
                onEdit={() => navigate(`/bulk-loads/${c.id}/edit`)}
                onClone={() => clone(c.id)}
                onDelete={() => globalThis.confirm(`Delete "${c.name}"?`) && remove(c.id)}
              />
            ))}
          </div>
        )}
      </div>
    </>
  )
}
