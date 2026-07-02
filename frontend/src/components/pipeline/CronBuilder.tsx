import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCronNext } from '../../lib/api'

type Freq = 'none' | 'minutely' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'custom'
interface CronState { n: number; minute: number; hour: number; weekday: number; monthDay: number }
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

function detectFreq(cron: string): Freq {
  if (!cron) return 'none'
  const p = cron.trim().split(/\s+/)
  if (p.length !== 5) return 'custom'
  const [min, hr, dom, mon, dow] = p
  if (/^\*\/\d+$/.test(min) && hr==='*' && dom==='*' && mon==='*' && dow==='*') return 'minutely'
  if (/^\d+$/.test(min) && hr==='*' && dom==='*' && mon==='*' && dow==='*') return 'hourly'
  if (/^\d+$/.test(min) && /^\d+$/.test(hr) && dom==='*' && mon==='*' && dow==='*') return 'daily'
  if (/^\d+$/.test(min) && /^\d+$/.test(hr) && dom==='*' && mon==='*' && /^\d+$/.test(dow)) return 'weekly'
  if (/^\d+$/.test(min) && /^\d+$/.test(hr) && /^\d+$/.test(dom) && mon==='*' && dow==='*') return 'monthly'
  return 'custom'
}

function parseCronState(cron: string): CronState {
  const p = cron.trim().split(/\s+/)
  if (p.length !== 5) return { n: 5, minute: 0, hour: 8, weekday: 1, monthDay: 1 }
  const [min, hr, dom, , dow] = p
  return {
    n:        Number.parseInt(min.replace('*/', '')) || 5,
    minute:   Number.parseInt(min) || 0,
    hour:     Number.parseInt(hr) || 8,
    weekday:  Number.parseInt(dow) || 1,
    monthDay: Number.parseInt(dom) || 1,
  }
}

function buildCronStr(freq: Freq, s: CronState): string {
  switch (freq) {
    case 'minutely': return `*/${s.n} * * * *`
    case 'hourly':   return `${s.minute} * * * *`
    case 'daily':    return `${s.minute} ${s.hour} * * *`
    case 'weekly':   return `${s.minute} ${s.hour} * * ${s.weekday}`
    case 'monthly':  return `${s.minute} ${s.hour} ${s.monthDay} * *`
    default:         return ''
  }
}

export default function CronBuilder({ defaultValue, onChange }: { defaultValue: string; onChange: (v: string) => void }) {
  const [freq, setFreq]       = useState<Freq>(() => detectFreq(defaultValue))
  const [state, setCronState] = useState<CronState>(() => parseCronState(defaultValue))
  const [rawCron, setRawCron] = useState(defaultValue)
  const mounted = useRef(false)

  const currentCron = (() => {
    if (freq === 'custom') return rawCron
    if (freq === 'none') return ''
    return buildCronStr(freq, state)
  })()

  useEffect(() => {
    if (!mounted.current) { mounted.current = true; return }
    onChange(currentCron)
    // CronBuilder is only ever passed a useState setter as onChange (stable reference),
    // so including it here doesn't change when this effect re-runs
  }, [currentCron, onChange])

  const { data: nextData } = useQuery({
    queryKey: ['cron-next', currentCron],
    queryFn:  () => getCronNext(currentCron),
    enabled:  !!currentCron && currentCron.trim().split(/\s+/).length === 5,
    staleTime: 60_000,
    retry: false,
  })

  const upd = (key: keyof CronState, val: number) => setCronState(s => ({ ...s, [key]: val }))

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 flex-wrap">
        <select className="input !h-[34px] !w-40" value={freq} onChange={e => setFreq(e.target.value as Freq)}>
          <option value="none">No schedule</option>
          <option value="minutely">Every N minutes</option>
          <option value="hourly">Hourly</option>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="custom">Custom (raw cron)</option>
        </select>

        {freq === 'minutely' && (<>
          <span className="text-[12.5px] text-[var(--text-3)]">every</span>
          <input className="input !w-16 !h-[34px]" type="number" min={1} max={59} value={state.n} onChange={e => upd('n', +e.target.value)} />
          <span className="text-[12.5px] text-[var(--text-3)]">minutes</span>
        </>)}

        {freq === 'hourly' && (<>
          <span className="text-[12.5px] text-[var(--text-3)]">at</span>
          <span className="text-[12.5px] text-[var(--text-3)] font-mono">:</span>
          <input className="input !w-16 !h-[34px]" type="number" min={0} max={59} value={state.minute} onChange={e => upd('minute', +e.target.value)} title="Minute past the hour (0–59)" />
          <span className="text-[12.5px] text-[var(--text-3)]">each hour</span>
        </>)}

        {(freq === 'daily' || freq === 'weekly' || freq === 'monthly') && (<>
          <span className="text-[12.5px] text-[var(--text-3)]">at</span>
          <select className="input !h-[34px] !w-20" value={state.hour} onChange={e => upd('hour', +e.target.value)}>
            {Array.from({length: 24}, (_, i) => i).map(h => <option key={h} value={h}>{String(h).padStart(2,'0')}:00</option>)}
          </select>
          <input className="input !w-14 !h-[34px]" type="number" min={0} max={59} value={state.minute} onChange={e => upd('minute', +e.target.value)} title="Minute (0–59)" />
        </>)}

        {freq === 'weekly' && (<>
          <span className="text-[12.5px] text-[var(--text-3)]">on</span>
          <select className="input !h-[34px] !w-[110px]" value={state.weekday} onChange={e => upd('weekday', +e.target.value)}>
            {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
          </select>
        </>)}

        {freq === 'monthly' && (<>
          <span className="text-[12.5px] text-[var(--text-3)]">on day</span>
          <input className="input !w-16 !h-[34px]" type="number" min={1} max={31} value={state.monthDay} onChange={e => upd('monthDay', +e.target.value)} />
        </>)}

        {freq === 'custom' && (
          <input className="input mono-input !w-40 !h-[34px]" value={rawCron} onChange={e => setRawCron(e.target.value)} placeholder="0 8 * * 1-5" />
        )}
      </div>

      {currentCron && freq !== 'custom' && (
        <div className="font-mono text-[11px] text-[var(--text-dim)]">
          {currentCron}
        </div>
      )}

      {nextData?.next_runs && nextData.next_runs.length > 0 && (
        <div className="text-[11.5px] text-[var(--text-muted)] flex flex-wrap gap-[4px_14px]">
          <span className="text-[var(--text-dim)] font-medium mr-1">Next runs:</span>
          {nextData.next_runs.map((t) => (
            <span key={t} className="font-mono">
              {new Date(t).toLocaleString('en-US', { weekday:'short', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit', timeZoneName:'short' })}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
