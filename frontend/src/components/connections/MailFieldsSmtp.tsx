import Field from './Field'
import type { MailForm } from './types'

export default function MailFieldsSmtp({ form, setForm }: {
  form: MailForm
  setForm: React.Dispatch<React.SetStateAction<MailForm>>
}) {
  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 10 }}>
        <Field label="SMTP Host">
          <input className="input" value={form.host} onChange={e => setForm(f => ({ ...f, host: e.target.value }))} placeholder="smtp.gmail.com" required />
        </Field>
        <Field label="Port">
          <input className="input" type="number" value={form.port} onChange={e => setForm(f => ({ ...f, port: e.target.value }))} required />
        </Field>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Field label="Username">
          <input className="input" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
        </Field>
        <Field label="Password">
          <input className="input" type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
        </Field>
      </div>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-3)', cursor: 'pointer' }}>
        <input type="checkbox" checked={form.use_tls} onChange={e => setForm(f => ({ ...f, use_tls: e.target.checked }))} />{' '}
        Use TLS
      </label>
    </>
  )
}
