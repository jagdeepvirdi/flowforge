import Field from './Field'
import type { MailForm } from './types'

// Gmail and Microsoft 365 — both OAuth2, sharing client_id/client_secret.
export default function MailFieldsOAuth({ form, setForm }: {
  form: MailForm
  setForm: React.Dispatch<React.SetStateAction<MailForm>>
}) {
  return (
    <>
      {form.provider_type === 'microsoft365' && (
        <Field label="Tenant ID">
          <input className="input" value={form.tenant_id} onChange={e => setForm(f => ({ ...f, tenant_id: e.target.value }))} placeholder="your-tenant-id" required />
        </Field>
      )}
      <Field label="Client ID">
        <input className="input" value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} required />
      </Field>
      <Field label="Client Secret">
        <input className="input" type="password" value={form.client_secret} onChange={e => setForm(f => ({ ...f, client_secret: e.target.value }))} required />
      </Field>
      {form.provider_type === 'gmail' && (
        <Field label="Refresh Token">
          <input className="input" type="password" value={form.refresh_token} onChange={e => setForm(f => ({ ...f, refresh_token: e.target.value }))}
            placeholder="Paste refresh token from OAuth2 setup" required />
          <span className="text-[11px] text-text-muted mt-[3px]">
            Run <code className="text-text-3">flowforge setup gmail</code> in the terminal to generate this token.
          </span>
        </Field>
      )}
    </>
  )
}
