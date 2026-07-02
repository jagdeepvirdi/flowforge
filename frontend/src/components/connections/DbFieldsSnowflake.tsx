import Field from './Field'
import type { DbForm } from './types'

export default function DbFieldsSnowflake({ form, setForm }: {
  form: DbForm
  setForm: React.Dispatch<React.SetStateAction<DbForm>>
}) {
  return (
    <>
      <Field label="Account Identifier">
        <input className="input" value={form.account} onChange={e => setForm(f => ({ ...f, account: e.target.value }))}
          placeholder="xy12345.us-east-1" required />
      </Field>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Field label="Username">
          <input className="input" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} required />
        </Field>
        <Field label="Password">
          <input className="input" type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
        </Field>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Field label="Warehouse">
          <input className="input" value={form.warehouse} onChange={e => setForm(f => ({ ...f, warehouse: e.target.value }))} placeholder="COMPUTE_WH" />
        </Field>
        <Field label="Database">
          <input className="input" value={form.database} onChange={e => setForm(f => ({ ...f, database: e.target.value }))} placeholder="MY_DB" />
        </Field>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Field label="Schema">
          <input className="input" value={form.schema_name} onChange={e => setForm(f => ({ ...f, schema_name: e.target.value }))} placeholder="PUBLIC" />
        </Field>
        <Field label="Role (optional)">
          <input className="input" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))} placeholder="SYSADMIN" />
        </Field>
      </div>
    </>
  )
}
