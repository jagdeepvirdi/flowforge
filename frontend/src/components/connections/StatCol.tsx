export default function StatCol({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col min-w-[70px]">
      <span className="text-[10px] text-text-muted uppercase tracking-[0.04em] font-semibold mb-[3px]">{label}</span>
      <span className="mono text-xs text-text-2 font-medium">{value}</span>
    </div>
  )
}
