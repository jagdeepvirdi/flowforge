import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Save, ArrowLeft, X, Eye } from 'lucide-react'
import { getEmailConfig, createEmailConfig, updateEmailConfig, getEmailProviders, getRecipientGroups, previewEmailConfig } from '../lib/api'
import { useProjectStore } from '../lib/store'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'
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
          <button type="button" onClick={() => onChange(values.filter(x => x !== v))}><X size={10}/></button>
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

const schema = z.object({
  name:       z.string().min(1, 'Name is required'),
  desc:       z.string(),
  providerId: z.string(),
  fromName:   z.string(),
  subject:    z.string().min(1, 'Subject is required'),
  headerText: z.string(),
  body:       z.string(),
  groupId:    z.string(),
  to:         z.array(z.string()),
  cc:         z.array(z.string()),
  bcc:        z.array(z.string()),
  maxMb:      z.number().min(1).max(50),
  folderId:   z.string(),
  driveMsg:   z.string(),
}).refine(
  data => data.groupId !== '' || data.to.length > 0,
  { message: 'Add at least one recipient address or select a group', path: ['to'] }
)
type FormValues = z.infer<typeof schema>

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

  const { register, handleSubmit, control, watch, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '', desc: '', providerId: '', fromName: '',
      subject: '', headerText: '', body: '',
      groupId: '', to: [], cc: [], bcc: [],
      maxMb: 10, folderId: '', driveMsg: '',
    },
  })

  const [error, setError]             = useState('')
  const [previewing, setPreviewing]   = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewData, setPreviewData] = useState<{ subject: string; html: string } | null>(null)
  const [previewError, setPreviewError] = useState('')

  const maxMb  = watch('maxMb')
  const groupId = watch('groupId')

  useEffect(() => {
    if (existing) reset({
      name:       existing.name,
      desc:       existing.description ?? '',
      providerId: existing.provider_id ?? '',
      fromName:   existing.from_name ?? '',
      subject:    existing.subject,
      headerText: existing.header_text ?? '',
      body:       existing.body_template,
      groupId:    existing.recipient_group_id ?? '',
      to:         existing.to_addresses,
      cc:         existing.cc_addresses,
      bcc:        existing.bcc_addresses,
      maxMb:      existing.attachment_max_mb,
      folderId:   existing.drive_folder_id ?? '',
      driveMsg:   existing.drive_share_message ?? '',
    })
  }, [existing, reset])

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

  const onSubmit = async (values: FormValues) => {
    setError('')
    try {
      const payload = {
        name: values.name, description: values.desc,
        provider_id: values.providerId || null,
        from_name: values.fromName || null,
        subject: values.subject,
        header_text: values.headerText || null,
        body_template: values.body,
        recipient_group_id: values.groupId || null,
        to_addresses: values.to, cc_addresses: values.cc, bcc_addresses: values.bcc,
        attachment_max_mb: values.maxMb,
        drive_folder_id: values.folderId || null,
        drive_share_message: values.driveMsg || null,
        ...(isNew && activeProjectId ? { project_id: activeProjectId } : {}),
      }
      isNew ? await createEmailConfig(payload) : await updateEmailConfig(id!, payload)
      qc.invalidateQueries({ queryKey: ['email-configs'] })
      navigate('/emails')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    }
  }

  const crumbs = isNew
    ? ['Workspace', 'Email Templates', 'New Email Config']
    : ['Workspace', 'Email Templates', watch('name') || 'Edit Email Config']

  if (!isNew && isLoading) return (
    <>
      <TopBar crumbs={crumbs} />
      <div className="scroll">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16, alignItems: 'start' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {[['Details', 4], ['Recipients', 2], ['Body template', 1]].map(([label, rows]) => (
              <div key={label as string} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <Sk h={13} style={{ width: 70 }} />
                {Array.from({ length: rows as number }).map((_, i) => (
                  <div key={i} className="field">
                    <Sk h={12} style={{ width: 80, marginBottom: 6 }} />
                    <Sk h={34} r={6} />
                  </div>
                ))}
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <Sk h={13} style={{ width: 120 }} />
              {[0,1,2].map(i => (
                <div key={i} className="field">
                  <Sk h={12} style={{ width: 90, marginBottom: 6 }} />
                  <Sk h={34} r={6} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  )

  return (
    <>
      <TopBar
        crumbs={crumbs}
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
            <Link to="/emails" className="btn btn-sm"><ArrowLeft size={12} /> Back</Link>
            {!isNew && (
              <button className="btn btn-sm" type="button" onClick={handlePreview} disabled={previewing} title="Preview rendered email">
                {previewing ? <Spinner size={12} /> : <Eye size={12} />} Preview
              </button>
            )}
            <button className="btn btn-primary btn-sm" type="button" onClick={handleSubmit(onSubmit)} disabled={isSubmitting}>
              {isSubmitting ? <Spinner size={12} /> : <Save size={12} />} Save
            </button>
          </div>
        }
      />

      <div className="scroll">
        {error && (
          <div style={{ marginBottom: 14, padding: '8px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 7, fontSize: 12.5, color: 'var(--failure-text)' }}>{error}</div>
        )}
        {previewError && (
          <div style={{ marginBottom: 14, padding: '8px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 7, fontSize: 12.5, color: 'var(--failure-text)' }}>Preview: {previewError}</div>
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
                  <input className="input" {...register('name')} />
                  {errors.name && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{errors.name.message}</span>}
                </div>
                <div className="field">
                  <label>Provider</label>
                  <select className="input" {...register('providerId')}>
                    <option value="">Select provider…</option>
                    {providers.map(p => <option key={p.id} value={p.id}>{p.name} ({p.provider_type})</option>)}
                  </select>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="field">
                  <label>From name</label>
                  <input className="input" {...register('fromName')} />
                </div>
                <div className="field">
                  <label>Description</label>
                  <input className="input" {...register('desc')} />
                </div>
              </div>
              <div className="field">
                <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>Subject<FieldTooltip field="variables" /></label>
                <input className="input" {...register('subject')} placeholder="Monthly Report — {{ current_month }}" />
                {errors.subject && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{errors.subject.message}</span>}
              </div>
              <div className="field">
                <label>Header text</label>
                <input className="input" {...register('headerText')} placeholder="Banner shown at the top of the email" />
              </div>
            </div>

            {/* Recipients */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Recipients</div>
              <div className="field">
                <label>Recipient group <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(overrides To addresses)</span></label>
                <select className="input" {...register('groupId')}>
                  <option value="">Use direct addresses</option>
                  {groups.map(g => <option key={g.id} value={g.id}>{g.name} ({g.addresses.length} recipients)</option>)}
                </select>
              </div>
              {!groupId && (
                <div className="field">
                  <label>To addresses <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Enter or comma to add)</span></label>
                  <Controller
                    control={control}
                    name="to"
                    render={({ field }) => (
                      <ChipInput values={field.value} onChange={field.onChange} placeholder="recipient@example.com" />
                    )}
                  />
                  {errors.to && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{errors.to.message}</span>}
                </div>
              )}
              <div className="field">
                <label>CC</label>
                <Controller
                  control={control}
                  name="cc"
                  render={({ field }) => <ChipInput values={field.value} onChange={field.onChange} placeholder="cc@example.com" />}
                />
              </div>
              <div className="field">
                <label>BCC</label>
                <Controller
                  control={control}
                  name="bcc"
                  render={({ field }) => <ChipInput values={field.value} onChange={field.onChange} placeholder="bcc@example.com" />}
                />
              </div>
            </div>

            {/* Body */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 6 }}>Body template <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>HTML + Jinja2</span><FieldTooltip field="body_template" /></div>
              <textarea
                className="input mono-input"
                rows={28}
                {...register('body')}
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
                  type="range" min={1} max={50}
                  {...register('maxMb', { valueAsNumber: true })}
                  style={{ width: '100%', accentColor: 'var(--accent)', cursor: 'pointer' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>
                  <span>1 MB</span><span>50 MB</span>
                </div>
              </div>
              <div className="field">
                <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>Google Drive folder ID<FieldTooltip field="drive_folder_id" /></label>
                <input className="input" {...register('folderId')} placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs" />
              </div>
              <div className="field">
                <label>Drive share message template</label>
                <textarea
                  className="input mono-input"
                  rows={5}
                  {...register('driveMsg')}
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
                  <code key={v} className="mono" style={{ fontSize: 11, color: 'var(--text-3)', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 4, padding: '3px 8px', display: 'block' }}>
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
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Email Preview</span>
                <span style={{ fontSize: 11.5, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Subject: {previewData.subject}</span>
              </div>
              <button className="btn btn-sm" onClick={() => setPreviewOpen(false)} style={{ padding: '4px 8px' }}>
                <X size={12} />
              </button>
            </div>
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
