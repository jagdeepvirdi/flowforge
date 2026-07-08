import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { getMe } from './lib/api'
import { useAuth } from './lib/auth'
import Layout from './components/shared/Layout'
import RouteFallback from './components/shared/RouteFallback'

const Login = lazy(() => import('./pages/Login'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Pipelines = lazy(() => import('./pages/Pipelines'))
const PipelineEdit = lazy(() => import('./pages/PipelineEdit'))
const Reports = lazy(() => import('./pages/Reports'))
const ReportEdit = lazy(() => import('./pages/ReportEdit'))
const Emails = lazy(() => import('./pages/Emails'))
const EmailEdit = lazy(() => import('./pages/EmailEdit'))
const Connections = lazy(() => import('./pages/Connections'))
const Recipients = lazy(() => import('./pages/Recipients'))
const RunHistory = lazy(() => import('./pages/RunHistory'))
const RunDetail = lazy(() => import('./pages/RunDetail'))
const Settings = lazy(() => import('./pages/Settings'))
const BulkLoads = lazy(() => import('./pages/BulkLoads'))
const BulkLoadEdit = lazy(() => import('./pages/BulkLoadEdit'))
const Projects = lazy(() => import('./pages/Projects'))
const Users = lazy(() => import('./pages/Users'))
const AuditLog = lazy(() => import('./pages/AuditLog'))

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />
}

function AppBootstrap({ children }: { children: React.ReactNode }) {
  const token = useAuth((s) => s.token)
  const setUser = useAuth((s) => s.setUser)
  const clearToken = useAuth((s) => s.clearToken)

  useEffect(() => {
    if (!token) return
    getMe().then(setUser).catch(() => clearToken())
    // setUser/clearToken are stable Zustand store actions (see lib/auth.ts) — adding
    // them here doesn't change when this effect re-runs (still only on token change)
  }, [token, setUser, clearToken])

  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <AppBootstrap>
      <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="pipelines" element={<Pipelines />} />
          <Route path="pipelines/new" element={<PipelineEdit />} />
          <Route path="pipelines/:id/edit" element={<PipelineEdit />} />
          <Route path="reports" element={<Reports />} />
          <Route path="reports/new" element={<ReportEdit />} />
          <Route path="reports/:id/edit" element={<ReportEdit />} />
          <Route path="emails" element={<Emails />} />
          <Route path="emails/new" element={<EmailEdit />} />
          <Route path="emails/:id/edit" element={<EmailEdit />} />
          <Route path="projects" element={<Projects />} />
          <Route path="connections" element={<Connections />} />
          <Route path="recipients" element={<Recipients />} />
          <Route path="bulk-loads" element={<BulkLoads />} />
          <Route path="bulk-loads/new" element={<BulkLoadEdit />} />
          <Route path="bulk-loads/:id/edit" element={<BulkLoadEdit />} />
          <Route path="runs" element={<RunHistory />} />
          <Route path="runs/:id" element={<RunDetail />} />
          <Route path="settings" element={<Settings />} />
          <Route path="settings/users" element={<Users />} />
          <Route path="settings/audit" element={<AuditLog />} />
        </Route>
      </Routes>
      </Suspense>
      </AppBootstrap>
    </BrowserRouter>
  )
}
