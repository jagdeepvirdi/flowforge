import Field from './Field'
import type { DbForm } from './types'

export default function DbFieldsBigQuery({ form, setForm }: {
  form: DbForm
  setForm: React.Dispatch<React.SetStateAction<DbForm>>
}) {
  return (
    <>
      <Field label="Project ID">
        <input className="input" value={form.project_id} onChange={e => setForm(f => ({ ...f, project_id: e.target.value }))}
          placeholder="my-gcp-project" required />
      </Field>
      <Field label="Dataset (optional)">
        <input className="input" value={form.dataset} onChange={e => setForm(f => ({ ...f, dataset: e.target.value }))} placeholder="my_dataset" />
      </Field>
      <Field label="Service Account Key (JSON)">
        <textarea className="input mono-input !h-auto !resize-none" rows={5} value={form.credentials_json}
          onChange={e => setForm(f => ({ ...f, credentials_json: e.target.value }))}
          placeholder='{"type": "service_account", ...}  (leave blank to use Application Default Credentials)' />
      </Field>
    </>
  )
}
