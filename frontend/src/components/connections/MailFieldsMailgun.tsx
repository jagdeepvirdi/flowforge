import Field from './Field'
import type { MailForm } from './types'

export default function MailFieldsMailgun({ form, setForm }: {
  form: MailForm
  setForm: React.Dispatch<React.SetStateAction<MailForm>>
}) {
  return (
    <>
      <Field label="API Key">
        <input className="input" type="password" value={form.api_key} onChange={e => setForm(f => ({ ...f, api_key: e.target.value }))} required />
      </Field>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 10 }}>
        <Field label="Domain">
          <input className="input mono-input" value={form.domain} onChange={e => setForm(f => ({ ...f, domain: e.target.value }))} placeholder="mg.yourdomain.com" required />
        </Field>
        <Field label="Region">
          <select className="input" value={form.region} onChange={e => setForm(f => ({ ...f, region: e.target.value }))} style={{ height: 34 }}>
            <option value="us">US</option>
            <option value="eu">EU</option>
          </select>
        </Field>
      </div>
      <Field label="From Email">
        <input className="input" type="email" value={form.from_email} onChange={e => setForm(f => ({ ...f, from_email: e.target.value }))} required />
      </Field>
      <Field label="From Name (optional)">
        <input className="input" value={form.from_name} onChange={e => setForm(f => ({ ...f, from_name: e.target.value }))} />
      </Field>
    </>
  )
}
