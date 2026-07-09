import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, Link as LinkIcon, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { createWebhookToken, getWebhookTokens, revokeWebhookToken } from '../../lib/api'
import type { WebhookToken } from '../../lib/types'

export default function WebhookCard({ pipelineId, bare = false }: {
  pipelineId: string
  /** Render just the body, without the card wrapper/title — for embedding in TriggersCard. */
  bare?: boolean
}) {
  const qc = useQueryClient()
  const [newLabel, setNewLabel] = useState('')
  const [creating, setCreating] = useState(false)
  const [justCreated, setJustCreated] = useState<WebhookToken | null>(null)
  const [copied, setCopied] = useState(false)

  const { data: tokens = [], isLoading } = useQuery({
    queryKey: ['webhook-tokens', pipelineId],
    queryFn: () => getWebhookTokens(pipelineId),
  })

  const baseUrl = window.location.origin
  const triggerUrl = justCreated
    ? `${baseUrl}/api/pipelines/${pipelineId}/trigger?token=${justCreated.token}`
    : ''

  const handleCreate = async () => {
    setCreating(true)
    try {
      const created = await createWebhookToken(pipelineId, newLabel.trim())
      setJustCreated(created)
      setNewLabel('')
      qc.invalidateQueries({ queryKey: ['webhook-tokens', pipelineId] })
    } finally {
      setCreating(false)
    }
  }

  const handleRevoke = async (tokenId: string) => {
    if (!confirm('Revoke this token? Any integrations using it will stop working.')) return
    await revokeWebhookToken(pipelineId, tokenId)
    qc.invalidateQueries({ queryKey: ['webhook-tokens', pipelineId] })
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(triggerUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const body = (
    <>
      <p className="text-[11.5px] text-[var(--text-muted)] mb-3 mt-0">
        Trigger this pipeline from external systems using{' '}
        <code className="text-[11px] bg-[var(--surface)] p-[1px_5px] rounded-[3px]">
          POST /api/pipelines/{pipelineId.slice(0, 8)}…/trigger?token=&lt;token&gt;
        </code>
      </p>

      {/* New token after creation — show URL once */}
      {justCreated && (
        <div className="mb-3 p-[10px_12px] bg-[rgba(34,197,94,0.06)] border border-[rgba(34,197,94,0.2)] rounded-md">
          <div className="text-[11.5px] text-[var(--success-text)] font-semibold mb-1.5">
            Token created — copy the URL now. It will not be shown again.
          </div>
          <div className="flex gap-1.5 items-center">
            <input
              readOnly
              value={triggerUrl}
              className="flex-1 bg-[var(--bg)] border border-[var(--border)] rounded-[5px] p-[5px_8px] text-[11px] font-mono text-[var(--text)] outline-none"
            />
            <button className="btn btn-sm" onClick={handleCopy} title="Copy URL">
              <Copy size={11} /> {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              className="btn btn-sm text-[var(--text-muted)]"
              onClick={() => setJustCreated(null)}
              title="Dismiss"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Token list */}
      {isLoading ? (
        <p className="text-[11.5px] text-[var(--text-muted)]">Loading…</p>
      ) : tokens.length === 0 && !justCreated ? (
        <p className="text-[11.5px] text-[var(--text-muted)] mb-3">No tokens yet. Generate one below to enable API triggers.</p>
      ) : (
        <div className="mb-3">
          {tokens.map(t => (
            <div key={t.id} className="flex items-center gap-2 py-1.5 border-b border-[var(--border)]">
              <span className="flex-1 text-xs text-[var(--text)]">{t.label || <em className="text-[var(--text-muted)]">unlabelled</em>}</span>
              <span className="text-[10.5px] text-[var(--text-muted)] font-mono">
                {t.last_used_at ? `last used ${new Date(t.last_used_at).toLocaleDateString()}` : 'never used'}
              </span>
              <button
                className="btn btn-sm text-[var(--failure-text)]"
                onClick={() => handleRevoke(t.id)}
                title="Revoke token"
              >
                <Trash2 size={11} /> Revoke
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Create new token */}
      <div className="flex gap-1.5 items-center">
        <input
          className="input h-8 text-xs flex-1"
          placeholder="Label (e.g. GitHub Actions, Zapier)"
          value={newLabel}
          onChange={e => setNewLabel(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !creating && handleCreate()}
        />
        <button
          className="btn btn-sm btn-primary"
          onClick={handleCreate}
          disabled={creating}
          title="Generate a new webhook token"
        >
          {creating ? <RefreshCw size={11} /> : <Plus size={11} />} Generate token
        </button>
      </div>
    </>
  )

  if (bare) return body

  return (
    <div className="card mb-4">
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <LinkIcon size={13} className="text-[var(--text-muted)]" />
          <span className="text-xs font-semibold text-[var(--text)]">Webhook / API Trigger</span>
        </div>
      </div>
      {body}
    </div>
  )
}
