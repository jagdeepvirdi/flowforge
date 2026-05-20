import { useEffect, useState, useRef } from 'react'
import { Search, Bell, ChevronRight, HelpCircle, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useHelp } from '../../lib/useHelp'

interface Props {
  crumbs: string[]
  actions?: React.ReactNode
  helpTopic?: string
  queryKeys?: string[][]
}

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
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, helpTopic, openHelp, closeHelp])

  const results: SearchResult[] = (() => {
    if (!query.trim()) return []
    const q = query.toLowerCase()
    const items: SearchResult[] = []

    const pipelines: any[] = qc.getQueryData(['pipelines']) ?? []
    pipelines.forEach(p => {
      if (p.name.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q))
        items.push({ id: p.id, label: p.name, sub: 'Pipeline', href: `/pipelines/${p.id}/edit` })
    })

    const reports: any[] = qc.getQueryData(['report-configs']) ?? []
    reports.forEach(r => {
      if (r.name.toLowerCase().includes(q) || r.description?.toLowerCase().includes(q))
        items.push({ id: r.id, label: r.name, sub: `Report · ${r.format.toUpperCase()}`, href: `/reports/${r.id}/edit` })
    })

    const emails: any[] = qc.getQueryData(['email-configs']) ?? []
    emails.forEach(e => {
      if (e.name.toLowerCase().includes(q) || e.description?.toLowerCase().includes(q))
        items.push({ id: e.id, label: e.name, sub: 'Email template', href: `/emails/${e.id}/edit` })
    })

    return items.slice(0, 8)
  })()

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
      <div className="crumb">
        {crumbs.map((c, i) => (
          <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {i > 0 && <span className="sep"><ChevronRight size={12} /></span>}
            <span className={i === crumbs.length - 1 ? 'here' : ''}>{c}</span>
          </span>
        ))}
      </div>
      <div className="tb-grow" />

      {/* Search */}
      <div style={{ position: 'relative' }}>
        <div className="tb-search" style={{ cursor: 'text' }}>
          <Search size={13} style={{ flexShrink: 0 }} />
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => setFocused(false), 150)}
            onKeyDown={e => {
              if (e.key === 'Escape') { setQuery(''); inputRef.current?.blur() }
              if (e.key === 'Enter' && results.length > 0) {
                navigate(results[0].href); setQuery(''); inputRef.current?.blur()
              }
            }}
            placeholder="Search…"
            style={{
              background: 'transparent', border: 'none', outline: 'none',
              color: '#F1F5F9', fontSize: 12.5, fontFamily: 'inherit', flex: 1, minWidth: 0,
            }}
          />
          {!query && (
            <kbd style={{
              marginLeft: 'auto', fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
              background: '#21252F', border: '1px solid #2D3143', borderRadius: 4,
              padding: '1px 5px', color: '#64748B', flexShrink: 0,
            }}>⌘K</kbd>
          )}
        </div>

        {showDropdown && (
          <div style={{
            position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0,
            background: '#1A1D27', border: '1px solid #2D3143', borderRadius: 8,
            boxShadow: '0 8px 24px rgba(0,0,0,0.4)', zIndex: 9999, overflow: 'hidden',
          }}>
            {results.length === 0 ? (
              <div style={{ padding: '10px 14px', fontSize: 12.5, color: '#64748B' }}>No results</div>
            ) : results.map(r => (
              <div
                key={r.id}
                onMouseDown={() => { navigate(r.href); setQuery('') }}
                style={{
                  padding: '9px 14px', cursor: 'pointer', display: 'flex',
                  alignItems: 'center', gap: 10, borderBottom: '1px solid #2D3143',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = '#21252F')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, color: '#F1F5F9', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.label}</div>
                  <div style={{ fontSize: 11, color: '#64748B', marginTop: 1 }}>{r.sub}</div>
                </div>
                <ChevronRight size={12} style={{ color: '#64748B', flexShrink: 0 }} />
              </div>
            ))}
          </div>
        )}
      </div>
      <button className="tb-icon-btn" title="Notifications (coming soon)" onClick={() => {}}><Bell size={16} /></button>
      <button className="tb-icon-btn" title="Refresh" onClick={handleRefresh}><RefreshCw size={15} /></button>
      <button
        className="tb-icon-btn"
        title="Help  (?)"
        onClick={handleHelpClick}
        style={{ position: 'relative', color: open ? '#F97316' : undefined }}
      >
        <HelpCircle size={16} />
        {!helpSeen && <span className="ff-help-dot" />}
      </button>
      {actions}
      <div className="tb-avatar">JD</div>
    </div>
  )
}
