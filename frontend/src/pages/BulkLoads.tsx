import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { getBulkLoadConfigs, deleteBulkLoadConfig, validateBulkLoadConfig, type BulkLoadPreview } from '../lib/api'
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

  const [testStatuses, setTestStatuses] = useState<Record<string, 'testing' | 'ok' | 'warn' | 'fail'>>({})
  const [testErrors, setTestErrors]     = useState<Record<string, string>>({})
  const [testResults, setTestResults]   = useState<Record<string, BulkLoadPreview>>({})

  const testConfig = (id: string) => {
    setTestStatuses(s => ({ ...s, [id]: 'testing' }))
    setTestErrors(e => ({ ...e, [id]: '' }))
    validateBulkLoadConfig(id)
      .then(result => {
        setTestResults(r => ({ ...r, [id]: result }))
        setTestStatuses(s => ({ ...s, [id]: result.warnings.length > 0 ? 'warn' : 'ok' }))
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Sk h={28} r={6} style={{ width: 140 }} />
            <Sk h={14} style={{ width: 180 }} />
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[0, 1, 2].map(i => (
            <div key={i} className="card" style={{ padding: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <Sk h={40} r={9} style={{ width: 40, flexShrink: 0 }} />
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <Sk h={14} style={{ width: 160 }} />
                    <Sk h={14} r={4} style={{ width: 50 }} />
                  </div>
                  <Sk h={11} style={{ width: 220 }} />
                </div>
                <div style={{ display: 'flex', gap: 24, flexShrink: 0 }}>
                  {[50, 40].map(w => (
                    <div key={w} style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 70 }}>
                      <Sk h={10} style={{ width: 40 }} />
                      <Sk h={12} style={{ width: w }} />
                    </div>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
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
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '0 0 14px' }}>
              A bulk load config defines the source directory, file pattern, and target table.
              Once created, reference it in a pipeline's Bulk Load step.
            </p>
            <button className="btn btn-primary" onClick={() => navigate('/bulk-loads/new')}>Create first bulk load config</button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {configs.map(c => (
              <BulkLoadRow
                key={c.id}
                config={c}
                testStatus={testStatuses[c.id]}
                testError={testErrors[c.id]}
                testResult={testResults[c.id]}
                onTest={() => testConfig(c.id)}
                onEdit={() => navigate(`/bulk-loads/${c.id}/edit`)}
                onDelete={() => globalThis.confirm(`Delete "${c.name}"?`) && remove(c.id)}
              />
            ))}
          </div>
        )}
      </div>
    </>
  )
}
