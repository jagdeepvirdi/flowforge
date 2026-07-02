export default function Field({ label, children, tooltip }: { label: string; children: React.ReactNode; tooltip?: React.ReactNode }) {
  return (
    <div className="field">
      <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>{label}{tooltip}</label>
      {children}
    </div>
  )
}
