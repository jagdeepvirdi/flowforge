import Field from './Field'
import type { MailForm } from './types'

export default function MailFieldsSendgrid({ form, setForm }: {
  form: MailForm
  setForm: React.Dispatch<React.SetStateAction<MailForm>>
}) {
  return (
    <>
      <Field label="API Key">
        <input className="input" type="password" value={form.api_key} onChange={e => setForm(f => ({ ...f, api_key: e.target.value }))} required />
      </Field>
      <Field label="From Email">
        <input className="input" type="email" value={form.from_email} onChange={e => setForm(f => ({ ...f, from_email: e.target.value }))} required />
      </Field>
      <Field label="From Name (optional)">
        <input className="input" value={form.from_name} onChange={e => setForm(f => ({ ...f, from_name: e.target.value }))} />
      </Field>
    </>
  )
}
