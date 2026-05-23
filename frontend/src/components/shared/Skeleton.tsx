export default function Sk({ h = '1rem', r = 4, style }: {
  h?: string | number
  r?: number
  style?: React.CSSProperties
}) {
  return (
    <div
      className="animate-pulse"
      style={{ height: h, borderRadius: r, background: 'var(--border)', width: '100%', ...style }}
    />
  )
}
