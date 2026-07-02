import FieldTooltip from '../shared/FieldTooltip'
import Field from './Field'
import type { DbForm } from './types'

// PostgreSQL, Oracle, MySQL, MSSQL, Redshift — standard host/port/database/user/pass shape.
export default function DbFieldsGeneric({ form, setForm }: {
  form: DbForm
  setForm: React.Dispatch<React.SetStateAction<DbForm>>
}) {
  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 10 }}>
        <Field label="Host" tooltip={<FieldTooltip field={form.db_type === 'oracle' ? 'oracle_connection' : 'db_host_port'} />}>
          <input className="input" value={form.host} onChange={e => setForm(f => ({ ...f, host: e.target.value }))} placeholder="localhost" required />
        </Field>
        <Field label="Port">
          <input className="input" type="number" value={form.port} onChange={e => setForm(f => ({ ...f, port: e.target.value }))} required />
        </Field>
      </div>

      <Field label={form.db_type === 'oracle' ? 'Service Name' : 'Database'}>
        <input className="input" value={form.database} onChange={e => setForm(f => ({ ...f, database: e.target.value }))}
          placeholder={form.db_type === 'oracle' ? 'ORCL' : 'mydb'} required />
      </Field>

      {form.db_type === 'mssql' && (
        <Field label="ODBC Driver">
          <input className="input" value={form.driver}
            onChange={e => setForm(f => ({ ...f, driver: e.target.value }))}
            placeholder="ODBC Driver 17 for SQL Server" />
          <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
            Install: <code style={{ color: 'var(--text-3)' }}>msodbcsql17</code> or <code style={{ color: 'var(--text-3)' }}>msodbcsql18</code>
          </span>
        </Field>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Field label="Username">
          <input className="input" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} required />
        </Field>
        <Field label="Password">
          <input className="input" type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
        </Field>
      </div>
    </>
  )
}
