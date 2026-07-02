export default function Field({ label, children, tooltip, htmlFor }: { label: string; children: React.ReactNode; tooltip?: React.ReactNode; htmlFor?: string }) {
  return (
    <div className="field">
      <label htmlFor={htmlFor} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {label}
        {tooltip}
      </label>
      {children}
    </div>
  )
}
