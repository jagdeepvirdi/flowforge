export default function StatCol({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minWidth: 70 }}>
      <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600, marginBottom: 3 }}>{label}</span>
      <span className="mono" style={{ fontSize: 12, color: 'var(--text-2)', fontWeight: 500 }}>{value}</span>
    </div>
  )
}
