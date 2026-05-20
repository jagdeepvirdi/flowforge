import { useEffect, useState } from 'react'
import { Search, Bell, ChevronRight, HelpCircle, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useHelp } from '../../lib/useHelp'

interface Props {
  crumbs: string[]
  actions?: React.ReactNode
  helpTopic?: string
  queryKeys?: string[][]
}

export default function TopBar({ crumbs, actions, helpTopic, queryKeys }: Props) {
  const { openHelp, closeHelp, open } = useHelp()
  const qc = useQueryClient()
  const [helpSeen, setHelpSeen] = useState(() => !!localStorage.getItem('ff_help_seen'))

  /* Global `?` key toggle */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '?' && !['INPUT','TEXTAREA','SELECT'].includes((e.target as Element).tagName)) {
        open ? closeHelp() : openHelp(helpTopic)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, helpTopic, openHelp, closeHelp])

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
      <div className="tb-search">
        <Search size={13} />
        <span>Search…</span>
        <kbd>⌘K</kbd>
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
