import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './lib/auth'
import Layout from './components/shared/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Pipelines from './pages/Pipelines'
import PipelineEdit from './pages/PipelineEdit'
import Reports from './pages/Reports'
import ReportEdit from './pages/ReportEdit'
import Emails from './pages/Emails'
import EmailEdit from './pages/EmailEdit'
import Connections from './pages/Connections'
import Recipients from './pages/Recipients'
import RunHistory from './pages/RunHistory'
import RunDetail from './pages/RunDetail'
import Settings from './pages/Settings'
import BulkLoads from './pages/BulkLoads'
import BulkLoadEdit from './pages/BulkLoadEdit'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
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
          <Route path="connections" element={<Connections />} />
          <Route path="recipients" element={<Recipients />} />
          <Route path="bulk-loads" element={<BulkLoads />} />
          <Route path="bulk-loads/new" element={<BulkLoadEdit />} />
          <Route path="bulk-loads/:id/edit" element={<BulkLoadEdit />} />
          <Route path="runs" element={<RunHistory />} />
          <Route path="runs/:id" element={<RunDetail />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
