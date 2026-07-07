import { useEffect, useState, useRef } from 'react'
import { Search, Bell, ChevronRight, HelpCircle, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useHelp } from '../../lib/useHelp'
import type { Pipeline, ReportConfig, EmailConfig } from '../../lib/types'
import ProjectSwitcher from './ProjectSwitcher'

type Props = Readonly<{
  crumbs: string[]
  actions?: React.ReactNode
  helpTopic?: string
  queryKeys?: string[][]
}>

interface SearchResult {
  id: string
  label: string
  sub: string
  href: string
}

export default function TopBar({ crumbs, actions, helpTopic, queryKeys }: Props) {
  const { openHelp, closeHelp, open } = useHelp()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [helpSeen, setHelpSeen] = useState(() => !!localStorage.getItem('ff_help_seen'))
  const [query, setQuery] = useState('')
  const [focused, setFocused] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  /* Global `?` key toggle and ⌘K / Ctrl+K to focus search */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '?' && !['INPUT','TEXTAREA','SELECT'].includes((e.target as Element).tagName)) {
        open ? closeHelp() : openHelp(helpTopic)
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    globalThis.addEventListener('keydown', handler)
    return () => globalThis.removeEventListener('keydown', handler)
  }, [open, helpTopic, openHelp, closeHelp])

  const pipelines: Pipeline[] = qc.getQueryData(['pipelines']) ?? []
  const reports: ReportConfig[] = qc.getQueryData(['report-configs']) ?? []
  const emails: EmailConfig[] = qc.getQueryData(['email-configs']) ?? []

  const results: SearchResult[] = (() => {
    if (!query.trim()) return []
    const q = query.toLowerCase()
    const items: SearchResult[] = []

    pipelines.forEach(p => {
      if (p.name.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q))
        items.push({ id: p.id, label: p.name, sub: 'Pipeline', href: `/pipelines/${p.id}/edit` })
    })
    reports.forEach(r => {
      if (r.name.toLowerCase().includes(q) || r.description?.toLowerCase().includes(q))
        items.push({ id: r.id, label: r.name, sub: `Report · ${r.format.toUpperCase()}`, href: `/reports/${r.id}/edit` })
    })
    emails.forEach(e => {
      if (e.name.toLowerCase().includes(q) || e.description?.toLowerCase().includes(q))
        items.push({ id: e.id, label: e.name, sub: 'Email template', href: `/emails/${e.id}/edit` })
    })

    return items.slice(0, 8)
  })()

  const allCachesEmpty = pipelines.length === 0 && reports.length === 0 && emails.length === 0
  const showDropdown = focused && query.trim().length > 0

  const handleHelpClick = () => {
    if (!helpSeen) {
      localStorage.setItem('ff_help_seen', '1')
      setHelpSeen(true)
    }
    open ? closeHelp() : openHelp(helpTopic)
  }

  const handleRefresh = () => {
    if (queryKeys && queryKeys.length > 0) {
      queryKeys.forEach(key => qc.invalidateQueries({ queryKey: key }))
    } else {
      qc.invalidateQueries()
    }
  }

  return (
    <div className="topbar">
      <ProjectSwitcher compact />
      <span className="w-px h-4 bg-border mx-2.5 shrink-0" />
      <div className="crumb">
        {crumbs.map((c, i) => ({ c, i })).map(({ c, i }) => (
          <span key={`crumb-${i}`} className="flex items-center gap-1.5">
            {i > 0 && <span className="sep"><ChevronRight size={12} /></span>}
            <span className={i === crumbs.length - 1 ? 'here' : ''}>{c}</span>
          </span>
        ))}
      </div>
      <div className="tb-grow" />

      {/* Search */}
      <div ref={containerRef} className="relative">
        <div className="tb-search cursor-text">
          <Search size={13} className="shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={e => {
              if (!containerRef.current?.contains(e.relatedTarget as Node)) {
                setFocused(false)
              }
            }}
            onKeyDown={e => {
              if (e.key === 'Escape') { setQuery(''); inputRef.current?.blur() }
              if (e.key === 'Enter' && results.length > 0) {
                navigate(results[0].href); setQuery(''); inputRef.current?.blur()
              }
            }}
            placeholder="Search…"
            className="bg-transparent border-none outline-none text-text-primary text-[12.5px] font-[inherit] flex-1 min-w-0"
          />
          {!query && (
            <kbd className="ml-auto font-mono text-[10px] bg-surface2 border border-border rounded py-px px-[5px] text-text-muted shrink-0">⌘K</kbd>
          )}
        </div>

        {showDropdown && (
          <div className="absolute top-[calc(100%+6px)] left-0 right-0 bg-surface border border-border rounded-r shadow-[0_8px_24px_rgba(0,0,0,0.4)] z-[9999] overflow-hidden">
            {results.length === 0 ? (
              <div className="py-2.5 px-3.5 text-[12.5px] text-text-muted">
                {allCachesEmpty
                  ? 'Visit Pipelines and Reports pages first to populate search'
                  : 'No results'}
              </div>
            ) : results.map(r => (
              <div
                key={r.id}
                role="option"
                aria-selected={false}
                onMouseDown={() => { navigate(r.href); setQuery('') }}
                onKeyDown={e => { if (e.key === 'Enter') { navigate(r.href); setQuery('') } }}
                tabIndex={0}
                className="py-[9px] px-3.5 cursor-pointer flex items-center gap-2.5 border-b border-border hover:bg-surface2"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] text-text-primary font-medium overflow-hidden text-ellipsis whitespace-nowrap">{r.label}</div>
                  <div className="text-[11px] text-text-muted mt-px">{r.sub}</div>
                </div>
                <ChevronRight size={12} className="text-text-muted shrink-0" />
              </div>
            ))}
          </div>
        )}
      </div>
      <button className="tb-icon-btn" title="Notifications (coming soon)" onClick={() => {}}><Bell size={16} /></button>
      <button className="tb-icon-btn" title="Refresh" onClick={handleRefresh}><RefreshCw size={15} /></button>
      <button
        className={`tb-icon-btn relative ${open ? 'text-accent' : ''}`}
        title="Help  (?)"
        onClick={handleHelpClick}
      >
        <HelpCircle size={16} />
        {!helpSeen && <span className="ff-help-dot" />}
      </button>
      {actions}
      <div className="tb-avatar">JD</div>
    </div>
  )
}
