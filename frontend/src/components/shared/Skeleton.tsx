export default function Sk({ h = '1rem', r = 4, style, className }: {
  h?: string | number
  r?: number
  style?: React.CSSProperties
  className?: string
}) {
  return (
    <div
      className={`animate-pulse${className ? ` ${className}` : ''}`}
      style={{ height: h, borderRadius: r, background: 'var(--border)', width: '100%', ...style }}
    />
  )
}
