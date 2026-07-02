import Field from './Field'
import type { MailForm } from './types'

export default function MailFieldsSes({ form, setForm }: {
  form: MailForm
  setForm: React.Dispatch<React.SetStateAction<MailForm>>
}) {
  return (
    <>
      <Field label="AWS Access Key ID">
        <input className="input mono-input" value={form.aws_access_key_id} onChange={e => setForm(f => ({ ...f, aws_access_key_id: e.target.value }))} required />
      </Field>
      <Field label="AWS Secret Access Key">
        <input className="input" type="password" value={form.aws_secret_access_key} onChange={e => setForm(f => ({ ...f, aws_secret_access_key: e.target.value }))} required />
      </Field>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Field label="AWS Region">
          <input className="input mono-input" value={form.aws_region} onChange={e => setForm(f => ({ ...f, aws_region: e.target.value }))} placeholder="us-east-1" required />
        </Field>
        <Field label="From Email">
          <input className="input" type="email" value={form.from_email} onChange={e => setForm(f => ({ ...f, from_email: e.target.value }))} required />
        </Field>
      </div>
      <Field label="From Name (optional)">
        <input className="input" value={form.from_name} onChange={e => setForm(f => ({ ...f, from_name: e.target.value }))} />
      </Field>
    </>
  )
}
