import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Save, ArrowLeft, X } from 'lucide-react'
import { getEmailConfig, createEmailConfig, updateEmailConfig, getEmailProviders, getRecipientGroups } from '../lib/api'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'

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
]

export default function EmailEdit() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: existing, isLoading } = useQuery({ queryKey: ['email-config', id], queryFn: () => getEmailConfig(id!), enabled: !isNew })
  const { data: providers = [] } = useQuery({ queryKey: ['email-providers'], queryFn: getEmailProviders })
  const { data: groups = [] }    = useQuery({ queryKey: ['recipient-groups'], queryFn: getRecipientGroups })

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

  const handleSave = async () => {
    if (!name.trim()) { setError('Name is required'); return }
    if (!subject.trim()) { setError('Subject is required'); return }
    setSaving(true); setError('')
    try {
      const payload = {
        name, description: desc, provider_id: providerId || null,
        from_name: fromName || null, subject, header_text: headerText || null,
        body_template: body, recipient_group_id: groupId || null,
        to_addresses: to, cc_addresses: cc, bcc_addresses: bcc,
        attachment_max_mb: maxMb, drive_folder_id: folderId || null,
        drive_share_message: driveMsg || null,
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

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16, alignItems: 'start' }}>

          {/* Left: main form */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Details */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#F1F5F9' }}>Details</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="field">
                  <label>Name *</label>
                  <input className="input" value={name} onChange={e => setName(e.target.value)} />
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
                <label>Subject</label>
                <input className="input" value={subject} onChange={e => setSubject(e.target.value)} placeholder="Monthly Report — {{ current_month }}" />
              </div>
              <div className="field">
                <label>Header text</label>
                <input className="input" value={headerText} onChange={e => setHeaderText(e.target.value)} placeholder="Banner shown at the top of the email" />
              </div>
            </div>

            {/* Recipients */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#F1F5F9' }}>Recipients</div>
              <div className="field">
                <label>Recipient group <span style={{ color: '#64748B', fontWeight: 400 }}>(overrides To addresses)</span></label>
                <select className="input" value={groupId} onChange={e => setGroupId(e.target.value)}>
                  <option value="">Use direct addresses</option>
                  {groups.map(g => <option key={g.id} value={g.id}>{g.name} ({g.addresses.length} recipients)</option>)}
                </select>
              </div>
              {!groupId && (
                <div className="field">
                  <label>To addresses <span style={{ color: '#64748B', fontWeight: 400 }}>(Enter or comma to add)</span></label>
                  <ChipInput values={to} onChange={setTo} placeholder="recipient@example.com" />
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
              <div style={{ fontSize: 12, fontWeight: 600, color: '#F1F5F9' }}>Body template <span style={{ color: '#64748B', fontWeight: 400, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>HTML + Jinja2</span></div>
              <textarea
                className="input mono-input"
                rows={14}
                value={body}
                onChange={e => setBody(e.target.value)}
                placeholder={"<p>Hi {{ name }},</p>\n<p>Please find the attached report.</p>"}
                style={{ resize: 'vertical', fontSize: 12.5, lineHeight: 1.6 }}
              />
            </div>
          </div>

          {/* Right rail */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Smart attachment */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#F1F5F9' }}>Smart Attachments</div>
              <p style={{ fontSize: 12, color: '#64748B', margin: 0, lineHeight: 1.5 }}>
                Files over the size limit are uploaded to Google Drive and a link is sent instead.
              </p>
              <div className="field">
                <label style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Max attachment size</span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', color: '#F97316' }}>{maxMb} MB</span>
                </label>
                <input
                  type="range" min={1} max={50} value={maxMb}
                  onChange={e => setMaxMb(+e.target.value)}
                  style={{ width: '100%', accentColor: '#F97316', cursor: 'pointer' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#475569', marginTop: 2 }}>
                  <span>1 MB</span><span>50 MB</span>
                </div>
              </div>
              <div className="field">
                <label>Google Drive folder ID</label>
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
              <div style={{ fontSize: 12, fontWeight: 600, color: '#F1F5F9' }}>Available variables</div>
              <p style={{ fontSize: 11.5, color: '#64748B', margin: 0 }}>Use in subject, header text, and body template.</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {TEMPLATE_VARS.map(v => (
                  <code key={v} className="mono" style={{ fontSize: 11, color: '#94A3B8', background: '#21252F', border: '1px solid #2D3143', borderRadius: 4, padding: '3px 8px', display: 'block' }}>
                    {v}
                  </code>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
