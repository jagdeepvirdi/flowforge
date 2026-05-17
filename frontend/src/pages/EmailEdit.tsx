import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Save, ArrowLeft, X } from 'lucide-react'
import { getEmailConfig, createEmailConfig, updateEmailConfig, getEmailProviders, getRecipientGroups } from '../lib/api'
import PageHeader from '../components/shared/PageHeader'
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

  if (!isNew && isLoading) return <div className="p-8 flex justify-center"><Spinner /></div>

  return (
    <div className="p-8 max-w-3xl">
      <PageHeader title={isNew ? 'New Email Config' : 'Edit Email Config'}
        action={
          <div className="flex gap-2">
            <Link to="/emails" className="btn-secondary"><ArrowLeft size={14}/> Back</Link>
            <button className="btn-primary" onClick={handleSave} disabled={saving}>{saving ? <Spinner size={14}/> : <Save size={14}/>} Save</button>
          </div>
        }
      />

      {error && <div className="mb-4 text-danger text-sm bg-danger/10 border border-danger/20 rounded-input px-3 py-2">{error}</div>}

      <div className="card mb-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div><label className="label">Name *</label><input className="input" value={name} onChange={e => setName(e.target.value)}/></div>
          <div><label className="label">Provider</label>
            <select className="input" value={providerId} onChange={e => setProviderId(e.target.value)}>
              <option value="">Select provider…</option>
              {providers.map(p => <option key={p.id} value={p.id}>{p.name} ({p.provider_type})</option>)}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div><label className="label">From name</label><input className="input" value={fromName} onChange={e => setFromName(e.target.value)}/></div>
          <div><label className="label">Description</label><input className="input" value={desc} onChange={e => setDesc(e.target.value)}/></div>
        </div>
        <div><label className="label">Subject (supports {`{{ variables }}`})</label><input className="input" value={subject} onChange={e => setSubject(e.target.value)}/></div>
        <div><label className="label">Header text</label><input className="input" value={headerText} onChange={e => setHeaderText(e.target.value)}/></div>

        <div><label className="label">Recipient group (overrides To addresses)</label>
          <select className="input" value={groupId} onChange={e => setGroupId(e.target.value)}>
            <option value="">Use direct addresses</option>
            {groups.map(g => <option key={g.id} value={g.id}>{g.name} ({g.addresses.length} recipients)</option>)}
          </select>
        </div>

        {!groupId && (
          <div><label className="label">To addresses (press Enter or comma to add)</label>
            <ChipInput values={to} onChange={setTo} placeholder="recipient@example.com" />
          </div>
        )}
        <div><label className="label">CC</label><ChipInput values={cc} onChange={setCc} placeholder="cc@example.com"/></div>
        <div><label className="label">BCC</label><ChipInput values={bcc} onChange={setBcc} placeholder="bcc@example.com"/></div>

        <div><label className="label">Body template (HTML + Jinja2)</label>
          <textarea className="input font-mono text-sm resize-none" rows={8} value={body} onChange={e => setBody(e.target.value)} placeholder="Hi {{ name }}, ..."/>
        </div>
      </div>

      <div className="card space-y-4">
        <h3 className="text-sm font-medium text-text-primary">Smart Attachment Settings</h3>
        <div className="flex items-center gap-4">
          <label className="label mb-0 whitespace-nowrap">Max attachment size: {maxMb}MB</label>
          <input type="range" min={1} max={50} value={maxMb} onChange={e => setMaxMb(+e.target.value)} className="flex-1 accent-accent"/>
        </div>
        <div><label className="label">Google Drive folder ID</label><input className="input" value={folderId} onChange={e => setFolderId(e.target.value)}/></div>
        <div><label className="label">Drive share message template</label>
          <textarea className="input font-mono text-sm resize-none" rows={4} value={driveMsg} onChange={e => setDriveMsg(e.target.value)}
            placeholder="{% for link in drive_links %}• {{ link.filename }} — {{ link.url }}&#10;{% endfor %}"/>
        </div>
      </div>
    </div>
  )
}
