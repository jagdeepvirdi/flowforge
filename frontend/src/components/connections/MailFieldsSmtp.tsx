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
      <div className="grid grid-cols-[1fr_100px] gap-2.5">
        <Field label="SMTP Host">
          <input className="input" value={form.host} onChange={e => setForm(f => ({ ...f, host: e.target.value }))} placeholder="smtp.gmail.com" required />
        </Field>
        <Field label="Port">
          <input className="input" type="number" value={form.port} onChange={e => setForm(f => ({ ...f, port: e.target.value }))} required />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        <Field label="Username">
          <input className="input" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
        </Field>
        <Field label="Password">
          <input className="input" type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
        </Field>
      </div>
      <Field label="Encryption">
        <div className="flex gap-3.5">
          {ENCRYPTION_OPTIONS.map(opt => (
            <label key={opt.value} className="flex items-center gap-1.5 text-[13px] text-text-3 cursor-pointer">
              <input
                type="radio"
                name="smtp-encryption"
                checked={encryption === opt.value}
                onChange={() => setEncryption(opt.value)}
              />
              {opt.label} <span className="text-text-muted">({opt.hint})</span>
            </label>
          ))}
        </div>
      </Field>
    </>
  )
}
