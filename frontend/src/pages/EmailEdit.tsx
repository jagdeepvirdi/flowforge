import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Save, ArrowLeft, X, Eye } from 'lucide-react'
import { getEmailConfig, createEmailConfig, updateEmailConfig, getEmailProviders, getRecipientGroups, previewEmailConfig } from '../lib/api'
import { useProjectStore } from '../lib/store'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import FieldTooltip from '../components/shared/FieldTooltip'

function ChipInput({ values, onChange, placeholder }: { values: string[]; onChange: (v: string[]) => void; placeholder?: string }) {
  const [input, setInput] = useState('')
  const add = () => {
    const v = input.trim()
    if (v && !values.includes(v)) onChange([...values, v])
    setInput('')
  }
  return (
    <div className="input flex flex-wrap gap-1 min-h-9 h-auto py-1.5">
      {values.map(v => (
        <span key={v} className="badge-muted flex items-center gap-1">
          {v}
          <button onClick={() => onChange(values.filter(x => x !== v))}><X size={10}/></button>
        </span>
      ))}
      <input
        className="flex-1 bg-transparent outline-none text-sm min-w-24"
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add() } }}
        onBlur={add}
        placeholder={values.length === 0 ? placeholder : ''}
      />
    </div>
  )
}

const TEMPLATE_VARS = [
  '{{ current_month }}', '{{ current_date }}', '{{ current_year }}',
  '{{ yesterday }}', '{{ run_id }}', '{{ pipeline_name }}',
  '{{ steps.step_name.output_path }}', '{{ steps.step_name.drive_url }}',
  '{{ steps.step_name.table_html }}', '{{ steps.step_name.kv_html }}',
  '{% for row in steps.step_name.rows %}{{ row.col }}{% endfor %}',
]

export default function EmailEdit() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { activeProjectId } = useProjectStore()

  const { data: existing, isLoading } = useQuery({ queryKey: ['email-config', id], queryFn: () => getEmailConfig(id!), enabled: !isNew })
  const { data: providers = [] } = useQuery({ queryKey: ['email-providers'], queryFn: getEmailProviders })
  const { data: groups = [] }    = useQuery({
    queryKey: ['recipient-groups', activeProjectId],
    queryFn: () => getRecipientGroups(activeProjectId ? { project_id: activeProjectId } : undefined),
  })

  const [name, setName]               = useState('')
  const [desc, setDesc]               = useState('')
  const [providerId, setProviderId]   = useState('')
  const [fromName, setFromName]       = useState('')
  const [subject, setSubject]         = useState('')
  const [headerText, setHeaderText]   = useState('')
  const [body, setBody]               = useState('')
  const [groupId, setGroupId]         = useState('')
  const [to, setTo]                   = useState<string[]>([])
  const [cc, setCc]                   = useState<string[]>([])
  const [bcc, setBcc]                 = useState<string[]>([])
  const [maxMb, setMaxMb]             = useState(10)
  const [folderId, setFolderId]       = useState('')
  const [driveMsg, setDriveMsg]       = useState('')
  const [saving, setSaving]           = useState(false)
  const [error, setError]             = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [previewing, setPreviewing]   = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewData, setPreviewData] = useState<{ subject: string; html: string } | null>(null)
  const [previewError, setPreviewError] = useState('')

  useEffect(() => {
    if (existing) {
      setName(existing.name); setDesc(existing.description ?? '')
      setProviderId(existing.provider_id ?? ''); setFromName(existing.from_name ?? '')
      setSubject(existing.subject); setHeaderText(existing.header_text ?? '')
      setBody(existing.body_template); setGroupId(existing.recipient_group_id ?? '')
      setTo(existing.to_addresses); setCc(existing.cc_addresses); setBcc(existing.bcc_addresses)
      setMaxMb(existing.attachment_max_mb); setFolderId(existing.drive_folder_id ?? '')
      setDriveMsg(existing.drive_share_message ?? '')
    }
  }, [existing])

  const handlePreview = async () => {
    if (!id) return
    setPreviewing(true); setPreviewError('')
    try {
      const data = await previewEmailConfig(id)
      setPreviewData(data)
      setPreviewOpen(true)
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : 'Preview failed')
    } finally {
      setPreviewing(false)
    }
  }

  const handleSave = async () => {
    const errs: Record<string, string> = {}
    if (!name.trim()) errs.name = 'Name is required'
    if (!subject.trim()) errs.subject = 'Subject is required'
    if (!groupId && to.length === 0) errs.recipients = 'Add at least one recipient address or select a group'
    if (Object.keys(errs).length) { setFieldErrors(errs); return }
    setFieldErrors({})
    setSaving(true); setError('')
    try {
      const payload = {
        name, description: desc, provider_id: providerId || null,
        from_name: fromName || null, subject, header_text: headerText || null,
        body_template: body, recipient_group_id: groupId || null,
        to_addresses: to, cc_addresses: cc, bcc_addresses: bcc,
        attachment_max_mb: maxMb, drive_folder_id: folderId || null,
        drive_share_message: driveMsg || null,
        ...(isNew && activeProjectId ? { project_id: activeProjectId } : {}),
      }
      isNew ? await createEmailConfig(payload) : await updateEmailConfig(id!, payload)
      qc.invalidateQueries({ queryKey: ['email-configs'] })
      navigate('/emails')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const crumbs = isNew
    ? ['Workspace', 'Email Templates', 'New Email Config']
    : ['Workspace', 'Email Templates', name || 'Edit Email Config']

  if (!isNew && isLoading) return (
    <><TopBar crumbs={crumbs} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
  )

  return (
    <>
      <TopBar
        crumbs={crumbs}
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
            <Link to="/emails" className="btn btn-sm"><ArrowLeft size={12} /> Back</Link>
            {!isNew && (
              <button className="btn btn-sm" onClick={handlePreview} disabled={previewing} title="Preview rendered email">
                {previewing ? <Spinner size={12} /> : <Eye size={12} />} Preview
              </button>
            )}
            <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
              {saving ? <Spinner size={12} /> : <Save size={12} />} Save
            </button>
          </div>
        }
      />

      <div className="scroll">
        {error && (
          <div style={{ marginBottom: 14, padding: '8px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 7, fontSize: 12.5, color: '#F87171' }}>{error}</div>
        )}
        {previewError && (
          <div style={{ marginBottom: 14, padding: '8px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 7, fontSize: 12.5, color: '#F87171' }}>Preview: {previewError}</div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16, alignItems: 'start' }}>

          {/* Left: main form */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Details */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Details</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="field">
                  <label>Name *</label>
                  <input className="input" value={name} onChange={e => { setName(e.target.value); if (fieldErrors.name) setFieldErrors(f => ({ ...f, name: '' })) }} />
                  {fieldErrors.name && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{fieldErrors.name}</span>}
                </div>
                <div className="field">
                  <label>Provider</label>
                  <select className="input" value={providerId} onChange={e => setProviderId(e.target.value)}>
                    <option value="">Select provider…</option>
                    {providers.map(p => <option key={p.id} value={p.id}>{p.name} ({p.provider_type})</option>)}
                  </select>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="field">
                  <label>From name</label>
                  <input className="input" value={fromName} onChange={e => setFromName(e.target.value)} />
                </div>
                <div className="field">
                  <label>Description</label>
                  <input className="input" value={desc} onChange={e => setDesc(e.target.value)} />
                </div>
              </div>
              <div className="field">
                <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>Subject<FieldTooltip field="variables" /></label>
                <input className="input" value={subject} onChange={e => { setSubject(e.target.value); if (fieldErrors.subject) setFieldErrors(f => ({ ...f, subject: '' })) }} placeholder="Monthly Report — {{ current_month }}" />
                {fieldErrors.subject && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{fieldErrors.subject}</span>}
              </div>
              <div className="field">
                <label>Header text</label>
                <input className="input" value={headerText} onChange={e => setHeaderText(e.target.value)} placeholder="Banner shown at the top of the email" />
              </div>
            </div>

            {/* Recipients */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Recipients</div>
              <div className="field">
                <label>Recipient group <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(overrides To addresses)</span></label>
                <select className="input" value={groupId} onChange={e => setGroupId(e.target.value)}>
                  <option value="">Use direct addresses</option>
                  {groups.map(g => <option key={g.id} value={g.id}>{g.name} ({g.addresses.length} recipients)</option>)}
                </select>
              </div>
              {!groupId && (
                <div className="field">
                  <label>To addresses <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Enter or comma to add)</span></label>
                  <ChipInput values={to} onChange={v => { setTo(v); if (fieldErrors.recipients) setFieldErrors(f => ({ ...f, recipients: '' })) }} placeholder="recipient@example.com" />
                  {fieldErrors.recipients && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{fieldErrors.recipients}</span>}
                </div>
              )}
              <div className="field">
                <label>CC</label>
                <ChipInput values={cc} onChange={setCc} placeholder="cc@example.com" />
              </div>
              <div className="field">
                <label>BCC</label>
                <ChipInput values={bcc} onChange={setBcc} placeholder="bcc@example.com" />
              </div>
            </div>

            {/* Body */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 6 }}>Body template <span style={{ color: '#64748B', fontWeight: 400, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>HTML + Jinja2</span><FieldTooltip field="body_template" /></div>
              <textarea
                className="input mono-input"
                rows={28}
                value={body}
                onChange={e => setBody(e.target.value)}
                placeholder={"<p>Hi {{ name }},</p>\n<p>Please find the attached report.</p>"}
                style={{ resize: 'vertical', fontSize: 12.5, lineHeight: 1.6, minHeight: 420 }}
              />
            </div>
          </div>

          {/* Right rail */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Smart attachment */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Smart Attachments</div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0, lineHeight: 1.5 }}>
                Files over the size limit are uploaded to Google Drive and a link is sent instead.
              </p>
              <div className="field">
                <label style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>Max attachment size<FieldTooltip field="attachment_max_mb" /></span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>{maxMb} MB</span>
                </label>
                <input
                  type="range" min={1} max={50} value={maxMb}
                  onChange={e => setMaxMb(+e.target.value)}
                  style={{ width: '100%', accentColor: 'var(--accent)', cursor: 'pointer' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#475569', marginTop: 2 }}>
                  <span>1 MB</span><span>50 MB</span>
                </div>
              </div>
              <div className="field">
                <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>Google Drive folder ID<FieldTooltip field="drive_folder_id" /></label>
                <input className="input" value={folderId} onChange={e => setFolderId(e.target.value)} placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs" />
              </div>
              <div className="field">
                <label>Drive share message template</label>
                <textarea
                  className="input mono-input"
                  rows={5}
                  value={driveMsg}
                  onChange={e => setDriveMsg(e.target.value)}
                  placeholder={"{% for link in drive_links %}\n• {{ link.filename }} — {{ link.url }}\n{% endfor %}"}
                  style={{ resize: 'vertical', fontSize: 11.5 }}
                />
              </div>
            </div>

            {/* Variable reference */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Available variables</div>
              <p style={{ fontSize: 11.5, color: 'var(--text-muted)', margin: 0 }}>Use in subject, header text, and body template.</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {TEMPLATE_VARS.map(v => (
                  <code key={v} className="mono" style={{ fontSize: 11, color: '#94A3B8', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 4, padding: '3px 8px', display: 'block' }}>
                    {v}
                  </code>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {previewOpen && previewData && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}
          onClick={e => { if (e.target === e.currentTarget) setPreviewOpen(false) }}
        >
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, width: '100%', maxWidth: 760, maxHeight: '90vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Modal header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Email Preview</span>
                <span style={{ fontSize: 11.5, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Subject: {previewData.subject}</span>
              </div>
              <button className="btn btn-sm" onClick={() => setPreviewOpen(false)} style={{ padding: '4px 8px' }}>
                <X size={12} />
              </button>
            </div>
            {/* Rendered email in an iframe for style isolation */}
            <iframe
              title="Email preview"
              srcDoc={previewData.html}
              style={{ flex: 1, border: 'none', background: '#ffffff', minHeight: 400 }}
              sandbox="allow-same-origin"
            />
          </div>
        </div>
      )}
    </>
  )
}
