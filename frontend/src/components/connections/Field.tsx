export default function Field({ label, children, tooltip }: { label: string; children: React.ReactNode; tooltip?: React.ReactNode }) {
  return (
    <div className="field">
      <label className="flex items-center gap-1">{label}{tooltip}</label>
      {children}
    </div>
  )
}
