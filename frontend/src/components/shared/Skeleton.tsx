export default function Sk({ h = '1rem', r = 4, style, className }: {
  h?: string | number
  r?: number
  style?: React.CSSProperties
  className?: string
}) {
  return (
    <div
      className={`animate-pulse w-full bg-border${className ? ` ${className}` : ''}`}
      style={{ height: h, borderRadius: r, ...style }}
    />
  )
}
