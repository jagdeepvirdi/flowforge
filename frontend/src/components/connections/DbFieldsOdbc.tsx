import FieldTooltip from '../shared/FieldTooltip'
import Field from './Field'
import type { DbForm } from './types'

export default function DbFieldsOdbc({ form, setForm }: {
  form: DbForm
  setForm: React.Dispatch<React.SetStateAction<DbForm>>
}) {
  return (
    <>
      <Field label="DSN (Data Source Name)" tooltip={<FieldTooltip field="db_host_port" />}>
        <input className="input" value={form.dsn}
          onChange={e => setForm(f => ({ ...f, dsn: e.target.value }))}
          placeholder="my_dsn  (leave blank to use connection string)" />
      </Field>
      <Field label="Connection String">
        <input className="input" value={form.connection_string}
          onChange={e => setForm(f => ({ ...f, connection_string: e.target.value }))}
          placeholder='Driver={...};Server=...;Database=...;UID=...;PWD=...' />
        <span className="text-[11px] text-text-muted mt-[3px]">
          DSN takes precedence if both are set.
        </span>
      </Field>
    </>
  )
}
