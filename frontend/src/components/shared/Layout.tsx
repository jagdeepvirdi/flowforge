import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../lib/auth'
import { getRuns, logout as apiLogout } from '../../lib/api'
import HelpDrawer from './HelpDrawer'
import RouteErrorBoundary from './RouteErrorBoundary'

const NAV_MAIN = [
  { to: '/dashboard',   label: 'Dashboard',       icon: 'dashboard' },
  { to: '/pipelines',   label: 'Pipelines',        icon: 'pipeline' },
  { to: '/reports',     label: 'Reports',          icon: 'report' },
  { to: '/emails',      label: 'Email Templates',  icon: 'mail' },
  { to: '/bulk-loads',  label: 'Bulk Loads',       icon: 'bulk' },
  { to: '/runs',        label: 'Run History',      icon: 'history' },
]
const NAV_SYSTEM = [
  { to: '/projects',    label: 'Projects',         icon: 'projects' },
  { to: '/connections', label: 'Connections',      icon: 'plug' },
  { to: '/recipients',  label: 'Recipients',       icon: 'users' },
  { to: '/settings',    label: 'Settings',         icon: 'cog' },
]

function NavIcon({ name }: { name: string }) {
  const stroke = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }
  const paths: Record<string, React.ReactNode> = {
    dashboard: <><rect x="3" y="3" width="7" height="9" rx="1.2" {...stroke}/><rect x="14" y="3" width="7" height="5" rx="1.2" {...stroke}/><rect x="14" y="11" width="7" height="10" rx="1.2" {...stroke}/><rect x="3" y="15" width="7" height="6" rx="1.2" {...stroke}/></>,
    pipeline:  <><circle cx="5" cy="6" r="2" {...stroke}/><circle cx="19" cy="6" r="2" {...stroke}/><circle cx="12" cy="18" r="2" {...stroke}/><path d="M7 6h10M5 8v3a3 3 0 003 3h2M19 8v3a3 3 0 01-3 3h-2" {...stroke}/></>,
    report:    <><path d="M5 3h10l4 4v14H5z" {...stroke}/><path d="M14 3v5h5M8 13h8M8 17h6" {...stroke}/></>,
    mail:      <><rect x="3" y="5" width="18" height="14" rx="2" {...stroke}/><path d="M3 7l9 6 9-6" {...stroke}/></>,
    history:   <><path d="M3 12a9 9 0 109-9 9 9 0 00-7.7 4.3M3 4v4h4M12 7v5l3 2" {...stroke}/></>,
    bulk:      <><path d="M4 6h16M4 10h16M4 14h10" {...stroke}/><path d="M16 16l3 3 3-3M19 19v-6" {...stroke}/></>,
    projects:  <><path d="M3 7h18M3 12h18M3 17h12" {...stroke}/><circle cx="19" cy="17" r="2" {...stroke}/></>,
    plug:      <><path d="M9 2v4M15 2v4M7 6h10v5a5 5 0 11-10 0V6zM12 16v4" {...stroke}/></>,
    users:     <><circle cx="9" cy="7" r="4" {...stroke}/><path d="M3 21v-2a4 4 0 014-4h4a4 4 0 014 4v2M16 3.13a4 4 0 010 7.75M21 21v-2a4 4 0 00-3-3.87" {...stroke}/></>,
    cog:       <><circle cx="12" cy="12" r="3" {...stroke}/><path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8L4.2 7a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1A2 2 0 0119.8 7l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z" {...stroke}/></>,
  }
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" aria-hidden="true">
      {paths[name]}
    </svg>
  )
}

const SPARKS = [8, 6, 9, 5, 12, 10, 14, 9, 11, 16, 13, 18, 15, 19]

export default function Layout() {
  const { clearToken } = useAuth()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const { data: todayRuns = [] } = useQuery({
    queryKey: ['runs-today'],
    queryFn: () => getRuns({ limit: 200 }),
    refetchInterval: 30000,
    select: runs => runs.filter(r => new Date(r.started_at).toDateString() === new Date().toDateString()),
  })
  const runsCount    = todayRuns.length
  const successCount = todayRuns.filter(r => r.status === 'success').length
  const sparkMax     = Math.max(...SPARKS, 1)
  const sparkNorm    = SPARKS.map(h => Math.round((h / sparkMax) * 22))

  return (
    <div className="ff-app">
      {/* Sidebar Overlay (Mobile) */}
      {sidebarOpen && (
        <div className="ff-sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`ff-sidebar ${sidebarOpen ? 'open' : ''}`}>
        {/* Mobile Close Button */}
        <button
          className="lg:hidden absolute top-4 right-4 text-text-muted hover:text-text"
          onClick={() => setSidebarOpen(false)}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', display: 'none' }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>

        {/* Brand */}
        <div className="flex items-center gap-2.5 p-[4px_8px_6px]">
          <div className="ff-logo">
            <svg width="18" height="20" viewBox="0 0 24 26" aria-hidden="true">
              <defs>
                <linearGradient id="ff-flame" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#FDBA74" />
                  <stop offset="55%"  stopColor="var(--accent)" />
                  <stop offset="100%" stopColor="#C2410C" />
                </linearGradient>
              </defs>
              <path d="M12 1c1.6 4 4.5 4.6 4.5 8.5 0 2-1 3.8-2.6 4.8.6-1.6.2-3.2-1.1-4.5-.4 2.5-2.3 3.8-2.3 6 0 1.5 1 2.7 2.2 3-3.4.2-6-2-6-5.3 0-4.7 5-5.8 5.3-12.5z" fill="url(#ff-flame)" />
              <path d="M12 9c.4 1.5-.2 2.6-.9 3.5-.6.8-.6 1.8 0 2.5.4.5.9.8 1.5 1-1.5-.2-2.4-1.3-2.4-2.6 0-1.5 1.4-2.4 1.8-4.4z" fill="#FED7AA" opacity="0.7" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="text-[14px] font-bold text-[var(--text)] tracking-tight leading-tight">FlowForge</span>
            <span className="text-[10.5px] text-[var(--text-muted)] font-mono flex items-center gap-1.5 mt-0.5">
              <span className="w-1.25 h-1.25 rounded-full bg-[var(--success)] shadow-[0_0_6px_var(--success)]" />
              production
            </span>
          </div>
        </div>

        {/* Nav */}
        <nav className="ff-nav">
          <div className="ff-nav-section">
            {NAV_MAIN.map(({ to, label, icon }) => (
              <NavLink key={to} to={to} className={({ isActive }) => `ff-nav-item${isActive ? ' active' : ''}`} onClick={() => setSidebarOpen(false)}>
                {({ isActive }) => (
                  <>
                    <span className="flex items-center gap-2.5">
                      <span className={isActive ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}><NavIcon name={icon} /></span>
                      {label}
                    </span>
                    {isActive && <span className="ff-active-bar" />}
                  </>
                )}
              </NavLink>
            ))}
          </div>

          <div className="ff-nav-label">System</div>

          <div className="ff-nav-section">
            {NAV_SYSTEM.map(({ to, label, icon }) => (
              <NavLink key={to} to={to} className={({ isActive }) => `ff-nav-item${isActive ? ' active' : ''}`} onClick={() => setSidebarOpen(false)}>
                {({ isActive }) => (
                  <>
                    <span className="flex items-center gap-2.5">
                      <span className={isActive ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}><NavIcon name={icon} /></span>
                      {label}
                    </span>
                    {isActive && <span className="ff-active-bar" />}
                  </>
                )}
              </NavLink>
            ))}
            <button
              onClick={() => { apiLogout().catch(() => {}).finally(() => { clearToken(); navigate('/login') }) }}
              className="ff-nav-item border-none bg-transparent w-full text-left cursor-pointer text-[13px] text-[var(--text-muted)]"
            >
              <span className="flex items-center gap-2.5">
                <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
                </svg>
                Sign out
              </span>
            </button>
          </div>
        </nav>

        {/* Footer stat card */}
        <div className="ff-stat-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider font-semibold">Today</span>
            {runsCount > 0 && (
              <span className="text-[10.5px] text-[var(--success-text)] font-semibold">
                {successCount}/{runsCount} ok
              </span>
            )}
          </div>
          <div className="flex items-baseline gap-1 mb-2">
            <span className="text-[22px] font-semibold font-mono tracking-tight text-[var(--text)]">{runsCount}</span>
            <span className="text-[11px] text-[var(--text-muted)]">run{runsCount !== 1 ? 's' : ''}</span>
          </div>
          <div className="sparkbars h-[22px]">
            {sparkNorm.map((h, i) => (
              <span key={i} className={`w-1 rounded-[1px] ${i === sparkNorm.length - 1 ? 'bg-[var(--accent)]' : 'bg-[var(--border)]'}`} style={{ height: h }} />
            ))}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="ff-main">
        {/* Mobile Hamburger */}
        <div style={{ display: 'flex', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid var(--border)', background: 'var(--bg)', gap: 12 }} className="lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text)', padding: 0 }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>FlowForge</span>
        </div>

        <RouteErrorBoundary>
          <Outlet />
        </RouteErrorBoundary>
      </main>

      <HelpDrawer />
    </div>
  )
}
