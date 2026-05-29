import {
  AreaChart, Area,
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie, Cell, Legend,
  ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

export type ChartType = 'bar' | 'line' | 'area' | 'pie' | 'scatter'

export interface ChartConfig {
  type: ChartType
  x: string
  y: string
  title: string
  available_columns: string[]
}

type Props = Readonly<{
  columns: string[]
  rows: unknown[][]
  config: ChartConfig
  onConfigChange: (c: ChartConfig) => void
}>

const PALETTE = ['#F97316', '#3B82F6', '#22C55E', '#A855F7', '#F59E0B', '#EC4899', '#14B8A6', '#6366F1']
const CHART_TYPES: ChartType[] = ['bar', 'line', 'area', 'pie', 'scatter']

const toRecharts = (columns: string[], rows: unknown[][]) =>
  rows.map(row => Object.fromEntries(columns.map((col, i) => [col, row[i]])))

const axisStyle = { fontSize: 11, fill: '#64748B' }
const gridStroke = 'rgba(255,255,255,0.06)'
const tipStyle = {
  contentStyle: {
    background: '#1A1D27',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 6,
    fontSize: 12,
  },
  labelStyle: { color: '#F1F5F9', fontWeight: 600 },
  itemStyle: { color: '#94A3B8' },
}

function ChartBody({ config, data }: { config: ChartConfig; data: Record<string, unknown>[] }) {
  const accent = '#F97316'
  const margins = { top: 4, right: 16, left: 0, bottom: 4 }

  if (config.type === 'bar') return (
    <BarChart data={data} margin={margins}>
      <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
      <XAxis dataKey={config.x} tick={axisStyle} axisLine={false} tickLine={false} />
      <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={50} />
      <Tooltip {...tipStyle} />
      <Bar dataKey={config.y} fill={accent} radius={[3, 3, 0, 0]} maxBarSize={52} />
    </BarChart>
  )

  if (config.type === 'line') return (
    <LineChart data={data} margin={margins}>
      <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
      <XAxis dataKey={config.x} tick={axisStyle} axisLine={false} tickLine={false} />
      <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={50} />
      <Tooltip {...tipStyle} />
      <Line dataKey={config.y} stroke={accent} strokeWidth={2} dot={false} activeDot={{ r: 4, fill: accent }} />
    </LineChart>
  )

  if (config.type === 'area') return (
    <AreaChart data={data} margin={margins}>
      <defs>
        <linearGradient id="ffAreaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%"  stopColor={accent} stopOpacity={0.28} />
          <stop offset="95%" stopColor={accent} stopOpacity={0} />
        </linearGradient>
      </defs>
      <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
      <XAxis dataKey={config.x} tick={axisStyle} axisLine={false} tickLine={false} />
      <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={50} />
      <Tooltip {...tipStyle} />
      <Area dataKey={config.y} stroke={accent} strokeWidth={2} fill="url(#ffAreaGrad)" dot={false} />
    </AreaChart>
  )

  if (config.type === 'pie') {
    const pieData = data.map(row => ({
      name:  String(row[config.x] ?? ''),
      value: Number(row[config.y] ?? 0),
    }))
    return (
      <PieChart>
        <Pie
          data={pieData}
          dataKey="value"
          nameKey="name"
          cx="50%" cy="50%"
          outerRadius={110}
          innerRadius={42}
        >
          {pieData.map((entry, i) => <Cell key={entry.name} fill={PALETTE[i % PALETTE.length]} />)}
        </Pie>
        <Tooltip {...tipStyle} />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 11, color: '#94A3B8' }} />
      </PieChart>
    )
  }

  // scatter — coerce to numbers
  const scatterData = data.map(row => ({
    ...row,
    [config.x]: Number(row[config.x]),
    [config.y]: Number(row[config.y]),
  }))
  return (
    <ScatterChart margin={margins}>
      <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
      <XAxis dataKey={config.x} type="number" name={config.x} tick={axisStyle} axisLine={false} tickLine={false} width={50} />
      <YAxis dataKey={config.y} type="number" name={config.y} tick={axisStyle} axisLine={false} tickLine={false} width={50} />
      <Tooltip cursor={{ strokeDasharray: '3 3' }} {...tipStyle} />
      <Scatter data={scatterData} fill={accent} />
    </ScatterChart>
  )
}

const selectStyle: React.CSSProperties = {
  fontSize: 11, padding: '1px 5px', borderRadius: 3,
  border: '1px solid var(--border)', background: 'var(--surface-2)',
  color: 'var(--text)', height: 22,
}

export default function ChartPreview({ columns, rows, config, onConfigChange }: Props) {
  const data = toRecharts(columns, rows)
  const set = (patch: Partial<ChartConfig>) => onConfigChange({ ...config, ...patch })
  const isPie = config.type === 'pie'

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
        padding: '9px 14px', borderBottom: '1px solid var(--border)',
      }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {config.title || 'AI Chart'}
        </span>

        {/* Chart type pills */}
        <div style={{ display: 'flex', gap: 3 }}>
          {CHART_TYPES.map(t => (
            <button
              key={t}
              onClick={() => set({ type: t })}
              style={{
                fontSize: 10.5, padding: '2px 7px', borderRadius: 3,
                background: config.type === t ? 'rgba(249,115,22,0.12)' : 'transparent',
                border: `1px solid ${config.type === t ? 'rgba(249,115,22,0.45)' : 'var(--border)'}`,
                color: config.type === t ? '#F97316' : 'var(--text-3)',
                cursor: 'pointer', fontFamily: 'inherit', fontWeight: 500,
                textTransform: 'capitalize',
              }}
            >
              {t}
            </button>
          ))}
        </div>

        {/* X axis */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 10.5, color: 'var(--text-muted)', fontWeight: 500 }}>
            {isPie ? 'Label' : 'X'}
          </span>
          <select style={selectStyle} value={config.x} onChange={e => set({ x: e.target.value })}>
            {columns.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {/* Y axis */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 10.5, color: 'var(--text-muted)', fontWeight: 500 }}>
            {isPie ? 'Value' : 'Y'}
          </span>
          <select style={selectStyle} value={config.y} onChange={e => set({ y: e.target.value })}>
            {columns.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>

      {/* Chart */}
      <div style={{ padding: '20px 8px 12px', height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ChartBody config={config} data={data} />
        </ResponsiveContainer>
      </div>
    </div>
  )
}
