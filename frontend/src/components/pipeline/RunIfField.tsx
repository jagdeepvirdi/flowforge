type Props = Readonly<{
  value: string
  onChange: (value: string) => void
}>

/** Optional `run_if` condition — the step is skipped when the expression is false. */
export default function RunIfField({ value, onChange }: Props) {
  return (
    <div
      className="field"
      title="Jinja2 expression. The step is skipped when it is false, e.g. steps.check.rows_affected > 0"
    >
      <label>Run only if</label>
      <input
        className="input mono-input"
        placeholder="always — e.g. steps.check.rows_affected > 0"
        value={value}
        onChange={e => onChange(e.target.value)}
        data-testid="run-if"
      />
    </div>
  )
}
