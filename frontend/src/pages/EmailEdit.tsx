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

function ChipInput({ id, values, onChange, placeholder }: { id?: string; values: string[]; onChange: (v: string[]) => void; placeholder?: string }) {
  const [input, setInput] = useState('')
  const add = () => {
    const v = input.trim()
    if (v && !values.includes(v)) onChange([...values, v])
    setInput('')
  }
  return (
    <div className="input flex flex-wrap gap-1 min-h-9 h-auto py-1.5">
      {values.map(v => (
        <span key={v} className="chip">
          {v}
          <button type="button" className="x" onClick={() => onChange(values.filter(x => x !== v))}><X size={10}/></button>
        </span>
      ))}
      <input
        id={id}
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
})
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

  const { register, handleSubmit, control, watch, reset, setError: setFieldError, formState: { errors, isSubmitting } } = useForm<FormValues>({
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

  const selectedGroup = groups.find(g => g.id === groupId)
  const groupTo  = selectedGroup?.addresses ?? []
  const groupCc  = selectedGroup?.cc_addresses ?? []
  const groupBcc = selectedGroup?.bcc_addresses ?? []
  const showTo  = !(groupId && groupTo.length  > 0)
  const showCc  = !(groupId && groupCc.length  > 0)
  const showBcc = !(groupId && groupBcc.length > 0)
  const groupSuppliesAny = !!groupId && (groupTo.length > 0 || groupCc.length > 0 || groupBcc.length > 0)

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
    const group = groups.find(g => g.id === values.groupId)
    const groupSuppliesTo = !!(values.groupId && group?.addresses?.length)
    if (!groupSuppliesTo && values.to.length === 0) {
      setFieldError('to', { message: 'Add at least one recipient address or select a group that provides To addresses' })
      return
    }
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
        <div className="grid grid-cols-[1fr_360px] gap-4 items-start">
          <div className="flex flex-col gap-4">
            {[['Details', 4], ['Recipients', 2], ['Body template', 1]].map(([label, rows]) => (
              <div key={label as string} className="card flex flex-col gap-3">
                <Sk h={13} style={{ width: 70 }} />
                {Array.from({ length: rows as number }, (_, i) => i).map(n => (
                  <div key={'sk-row-' + n} className="field">
                    <Sk h={12} style={{ width: 80, marginBottom: 6 }} />
                    <Sk h={34} r={6} />
                  </div>
                ))}
              </div>
            ))}
          </div>
          <div className="flex flex-col gap-4">
            <div className="card flex flex-col gap-3">
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
          <div className="flex gap-2">
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
          <div className="mb-3.5 py-2 px-3 bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-[7px] text-[12.5px] text-failure-text">{error}</div>
        )}
        {previewError && (
          <div className="mb-3.5 py-2 px-3 bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-[7px] text-[12.5px] text-failure-text">Preview: {previewError}</div>
        )}

        <div className="grid grid-cols-[1fr_360px] gap-4 items-start">

          {/* Left: main form */}
          <div className="flex flex-col gap-4">

            {/* Details */}
            <div className="card flex flex-col gap-3">
              <div className="text-xs font-semibold text-text-primary">Details</div>
              <div className="grid grid-cols-2 gap-3">
                <div className="field">
                  <label htmlFor="ec-name">Name *</label>
                  <input id="ec-name" className="input" {...register('name')} />
                  {errors.name && <span className="text-[11.5px] text-failure">{errors.name.message}</span>}
                </div>
                <div className="field">
                  <label htmlFor="ec-provider">Provider</label>
                  <select id="ec-provider" className="input" {...register('providerId')}>
                    <option value="">Select provider…</option>
                    {providers.map(p => <option key={p.id} value={p.id}>{p.name} ({p.provider_type})</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="field">
                  <label htmlFor="ec-from-name">From name</label>
                  <input id="ec-from-name" className="input" {...register('fromName')} />
                </div>
                <div className="field">
                  <label htmlFor="ec-desc">Description</label>
                  <input id="ec-desc" className="input" {...register('desc')} />
                </div>
              </div>
              <div className="field">
                <label htmlFor="ec-subject" className="flex items-center gap-1">Subject<FieldTooltip field="variables" /></label>
                <input id="ec-subject" className="input" {...register('subject')} placeholder="Monthly Report — {{ current_month }}" />
                {errors.subject && <span className="text-[11.5px] text-failure">{errors.subject.message}</span>}
              </div>
              <div className="field">
                <label htmlFor="ec-header-text">Header text</label>
                <input id="ec-header-text" className="input" {...register('headerText')} placeholder="Banner shown at the top of the email" />
              </div>
            </div>

            {/* Recipients */}
            <div className="card flex flex-col gap-3">
              <div className="text-xs font-semibold text-text-primary">Recipients</div>
              <div className="field">
                <label htmlFor="email-recipient-group">Recipient group <span className="text-text-muted font-normal">(To/CC/BCC set on the group override the matching field below)</span></label>
                <select id="email-recipient-group" className="input" {...register('groupId')}>
                  <option value="">Use direct addresses</option>
                  {groups.map(g => <option key={g.id} value={g.id}>{g.name} ({g.addresses.length + g.cc_addresses.length + g.bcc_addresses.length} recipients)</option>)}
                </select>
              </div>
              {groupSuppliesAny && (
                <p className="text-[11.5px] text-text-muted m-0">
                  From group: {[
                    groupTo.length  ? `To (${groupTo.length})`   : null,
                    groupCc.length  ? `CC (${groupCc.length})`   : null,
                    groupBcc.length ? `BCC (${groupBcc.length})` : null,
                  ].filter(Boolean).join(', ')}
                </p>
              )}
              {showTo && (
                <div className="field">
                  <label htmlFor="email-to-addresses">To addresses <span className="text-text-muted font-normal">(Enter or comma to add)</span></label>
                  <Controller
                    control={control}
                    name="to"
                    render={({ field }) => (
                      <ChipInput id="email-to-addresses" values={field.value} onChange={field.onChange} placeholder="recipient@example.com" />
                    )}
                  />
                  {errors.to && <span className="text-[11.5px] text-failure">{errors.to.message}</span>}
                </div>
              )}
              {showCc && (
                <div className="field">
                  <label htmlFor="ec-cc">CC</label>
                  <Controller
                    control={control}
                    name="cc"
                    render={({ field }) => <ChipInput id="ec-cc" values={field.value} onChange={field.onChange} placeholder="cc@example.com" />}
                  />
                </div>
              )}
              {showBcc && (
                <div className="field">
                  <label htmlFor="ec-bcc">BCC</label>
                  <Controller
                    control={control}
                    name="bcc"
                    render={({ field }) => <ChipInput id="ec-bcc" values={field.value} onChange={field.onChange} placeholder="bcc@example.com" />}
                  />
                </div>
              )}
              {!showTo && !showCc && !showBcc && (
                <p className="text-[11.5px] text-text-muted m-0">All recipients (To, CC, and BCC) come from the selected group.</p>
              )}
            </div>

            {/* Body */}
            <div className="card flex flex-col gap-3">
              <div className="text-xs font-semibold text-text-primary flex items-center gap-1.5">Body template <span className="text-text-muted font-normal font-mono text-[11px]">HTML + Jinja2</span><FieldTooltip field="body_template" /></div>
              <textarea
                className="input mono-input resize-y text-[12.5px] leading-[1.6] min-h-[420px]"
                rows={28}
                {...register('body')}
                placeholder={"<p>Hi {{ name }},</p>\n<p>Please find the attached report.</p>"}
              />
            </div>
          </div>

          {/* Right rail */}
          <div className="flex flex-col gap-4">

            {/* Smart attachment */}
            <div className="card flex flex-col gap-3">
              <div className="text-xs font-semibold text-text-primary">Smart Attachments</div>
              <p className="text-xs text-text-muted m-0 leading-[1.5]">
                Files over the size limit are uploaded to Google Drive and a link is sent instead.
              </p>
              <div className="field">
                <label className="flex justify-between">
                  <span className="flex items-center gap-1">Max attachment size<FieldTooltip field="attachment_max_mb" /></span>
                  <span className="font-mono text-accent">{maxMb} MB</span>
                </label>
                <input
                  type="range" min={1} max={50}
                  {...register('maxMb', { valueAsNumber: true })}
                  className="w-full accent-[var(--accent)] cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-text-dim mt-0.5">
                  <span>1 MB</span><span>50 MB</span>
                </div>
              </div>
              <div className="field">
                <label className="flex items-center gap-1">Google Drive folder ID<FieldTooltip field="drive_folder_id" /></label>
                <input className="input" {...register('folderId')} placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs" />
              </div>
              <div className="field">
                <label htmlFor="ec-drive-msg">Drive share message template</label>
                <textarea
                  id="ec-drive-msg"
                  className="input mono-input resize-y text-[11.5px]"
                  rows={5}
                  {...register('driveMsg')}
                  placeholder={"{% for link in drive_links %}\n• {{ link.filename }} — {{ link.url }}\n{% endfor %}"}
                />
              </div>
            </div>

            {/* Variable reference */}
            <div className="card flex flex-col gap-2.5">
              <div className="text-xs font-semibold text-text-primary">Available variables</div>
              <p className="text-[11.5px] text-text-muted m-0">Use in subject, header text, and body template.</p>
              <div className="flex flex-col gap-1">
                {TEMPLATE_VARS.map(v => (
                  <code key={v} className="mono text-[11px] text-text-3 bg-surface2 border border-border rounded py-[3px] px-2 block">
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
          role="button"
          tabIndex={0}
          aria-label="Close preview"
          className="fixed inset-0 bg-[rgba(0,0,0,0.65)] z-[1000] flex items-center justify-center p-6"
          onClick={e => { if (e.target === e.currentTarget) setPreviewOpen(false) }}
          onKeyDown={e => { if (e.key === 'Escape') setPreviewOpen(false) }}
        >
          <div className="bg-surface border border-border rounded-[10px] w-full max-w-[760px] max-h-[90vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between py-3 px-4 border-b border-border shrink-0">
              <div className="flex flex-col gap-0.5">
                <span className="text-xs font-semibold text-text-primary">Email Preview</span>
                <span className="text-[11.5px] text-text-muted font-mono">Subject: {previewData.subject}</span>
              </div>
              <button className="btn btn-sm py-1 px-2" onClick={() => setPreviewOpen(false)}>
                <X size={12} />
              </button>
            </div>
            <iframe
              title="Email preview"
              srcDoc={previewData.html}
              className="flex-1 border-none bg-white min-h-[400px]"
              sandbox="allow-same-origin"
            />
          </div>
        </div>
      )}
    </>
  )
}
