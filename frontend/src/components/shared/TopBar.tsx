import { Search, Bell, ChevronRight } from 'lucide-react'

interface Props {
  crumbs: string[]
  actions?: React.ReactNode
}

export default function TopBar({ crumbs, actions }: Props) {
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
      {actions}
      <div className="tb-avatar">JD</div>
    </div>
  )
}
