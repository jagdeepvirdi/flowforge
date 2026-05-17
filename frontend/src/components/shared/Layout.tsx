import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, GitBranch, FileText, Mail, Database,
  Users, History, Settings, LogOut, Flame,
} from 'lucide-react'
import { useAuth } from '../../lib/auth'

const NAV = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/pipelines',   icon: GitBranch,       label: 'Pipelines' },
  { to: '/reports',     icon: FileText,        label: 'Reports' },
  { to: '/emails',      icon: Mail,            label: 'Email' },
  { to: '/connections', icon: Database,        label: 'Connections' },
  { to: '/recipients',  icon: Users,           label: 'Recipients' },
  { to: '/runs',        icon: History,         label: 'Run History' },
  { to: '/settings',    icon: Settings,        label: 'Settings' },
]

export default function Layout() {
  const { clearToken } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    clearToken()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-bg">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-surface border-r border-border flex flex-col">
        {/* Logo */}
        <div className="h-14 flex items-center gap-2 px-4 border-b border-border">
          <Flame size={22} className="text-accent" />
          <span className="font-semibold text-text-primary tracking-tight">FlowForge</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-input text-sm transition-colors ${
                  isActive
                    ? 'bg-accent/10 text-accent font-medium'
                    : 'text-text-muted hover:text-text-primary hover:bg-surface2'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Logout */}
        <div className="p-2 border-t border-border">
          <button onClick={handleLogout} className="btn-ghost w-full justify-start text-sm">
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
