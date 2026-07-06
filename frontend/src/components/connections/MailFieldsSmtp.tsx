import Field from './Field'
import type { MailForm } from './types'

type Encryption = 'starttls' | 'ssl' | 'none'

function encryptionOf(form: MailForm): Encryption {
  if (form.use_ssl) return 'ssl'
  if (form.use_tls) return 'starttls'
  return 'none'
}

const ENCRYPTION_OPTIONS: { value: Encryption; label: string; hint: string }[] = [
  { value: 'starttls', label: 'STARTTLS',  hint: 'port 587' },
  { value: 'ssl',       label: 'SSL/TLS',  hint: 'port 465' },
  { value: 'none',      label: 'None',     hint: 'unencrypted' },
]

export default function MailFieldsSmtp({ form, setForm }: {
  form: MailForm
  setForm: React.Dispatch<React.SetStateAction<MailForm>>
}) {
  const encryption = encryptionOf(form)

  function setEncryption(value: Encryption) {
    setForm(f => ({ ...f, use_tls: value === 'starttls', use_ssl: value === 'ssl' }))
  }

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
      <Field label="Encryption">
        <div style={{ display: 'flex', gap: 14 }}>
          {ENCRYPTION_OPTIONS.map(opt => (
            <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-3)', cursor: 'pointer' }}>
              <input
                type="radio"
                name="smtp-encryption"
                checked={encryption === opt.value}
                onChange={() => setEncryption(opt.value)}
              />
              {opt.label} <span style={{ color: 'var(--text-muted)' }}>({opt.hint})</span>
            </label>
          ))}
        </div>
      </Field>
    </>
  )
}
