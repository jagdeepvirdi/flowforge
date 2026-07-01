import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Plus, Trash2, X } from 'lucide-react'
import { getUsers, createUser, updateUser, deleteUser, exportUserData, purgeUserData } from '../lib/api'
import { useCurrentUser } from '../lib/auth'
import type { User, Role } from '../lib/types'
import TopBar from '../components/shared/TopBar'
import Sk from '../components/shared/Skeleton'

const ROLES: Role[] = ['admin', 'editor', 'viewer']

const ROLE_STYLE: Record<Role, { bg: string; color: string }> = {
  admin:  { bg: 'rgba(249,115,22,0.12)', color: 'var(--accent-text)' },
  editor: { bg: 'rgba(59,130,246,0.12)', color: '#60A5FA' },
  viewer: { bg: 'rgba(107,114,128,0.12)', color: 'var(--text-muted)' },
}

function RoleBadge({ role }: { role: Role }) {
  const s = ROLE_STYLE[role]
  return (
    <span style={{
      display: 'inline-block', fontSize: 11, fontWeight: 600,
      padding: '2px 8px', borderRadius: 4,
      background: s.bg, color: s.color,
      textTransform: 'uppercase', letterSpacing: '0.06em',
    }}>
      {role}
    </span>
  )
}

type AddForm = { username: string; password: string; role: Role; email: string }
const emptyForm = (): AddForm => ({ username: '', password: '', role: 'editor', email: '' })

export default function Users() {
  const navigate   = useNavigate()
  const me         = useCurrentUser()
  const qc         = useQueryClient()
  const [showAdd, setShowAdd]   = useState(false)
  const [form, setForm]         = useState<AddForm>(emptyForm())
  const [formError, setFormError] = useState('')

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
  })

  const createMut = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setShowAdd(false)
      setForm(emptyForm())
      setFormError('')
    },
    onError: (e: Error) => setFormError(e.message),
  })

  const roleMut = useMutation({
    mutationFn: ({ id, role }: { id: string; role: Role }) => updateUser(id, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  const deleteMut = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  // Admin guard — hooks above, safe to return early here
  if (me && me.role !== 'admin') {
    navigate('/dashboard', { replace: true })
    return null
  }

  const usersTableContent = isLoading ? (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
      {[1, 2, 3].map(i => <Sk key={i} style={{ height: 36 }} />)}
    </div>
  ) : users.length === 0 ? (
    <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
      No users yet.
    </div>
  ) : (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr style={{ borderBottom: '1px solid var(--border)' }}>
          {['Username', 'Email', 'Role', 'Created', 'MFA', ''].map(h => (
            <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {users.map((user, i) => (
          <tr key={user.id} style={{ borderBottom: i < users.length - 1 ? '1px solid var(--border)' : 'none' }}>
            <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text)', fontWeight: 500 }}>
              {user.username}
              {user.id === me?.id && (
                <span style={{ marginLeft: 6, fontSize: 10.5, color: 'var(--text-muted)', fontWeight: 400 }}>(you)</span>
              )}
            </td>
            <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)' }}>
              {user.email
                ? <span className="mono">{user.email}</span>
                : <span style={{ color: 'var(--text-dim)', fontStyle: 'italic' }}>not set</span>}
            </td>
            <td style={{ padding: '12px 16px' }}>
              {user.id === me?.id ? (
                <RoleBadge role={user.role} />
              ) : (
                <select
                  className="input"
                  value={user.role}
                  style={{ fontSize: 12, padding: '3px 8px', width: 'auto' }}
                  disabled={roleMut.isPending}
                  onChange={e => roleMut.mutate({ id: user.id, role: e.target.value as Role })}
                >
                  {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              )}
            </td>
            <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
            </td>
            <td style={{ padding: '12px 16px' }}>
              <span style={{
                fontSize: 10.5, fontWeight: 600, padding: '2px 6px', borderRadius: 3,
                background: user.mfa_enabled ? 'rgba(34,197,94,0.12)' : 'rgba(107,114,128,0.1)',
                color: user.mfa_enabled ? 'var(--success-text)' : 'var(--text-dim)',
              }}>
                {user.mfa_enabled ? 'ON' : 'OFF'}
              </span>
            </td>
            <td style={{ padding: '12px 16px', textAlign: 'right' }}>
              <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                <button
                  className="btn"
                  style={{ padding: '4px 8px', fontSize: 11 }}
                  onClick={() => handleExport(user)}
                  title="GDPR export — download all personal data as JSON"
                >
                  <Download size={12} />
                </button>
                {user.id !== me?.id && (
                  <>
                    <button
                      className="btn"
                      style={{ padding: '4px 8px', color: 'var(--failure-text)', fontSize: 11 }}
                      disabled={deleteMut.isPending}
                      onClick={() => handleDelete(user)}
                      title="Delete user"
                    >
                      <Trash2 size={12} />
                    </button>
                    <button
                      className="btn"
                      style={{ padding: '4px 8px', color: 'var(--failure-text)', fontSize: 10 }}
                      onClick={() => handlePurge(user)}
                      title="GDPR purge — delete user and anonymise audit log"
                    >
                      GDPR
                    </button>
                  </>
                )}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )

  function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setFormError('')
    if (!form.username.trim()) { setFormError('Username is required'); return }
    if (form.password.length < 8) { setFormError('Password must be at least 8 characters'); return }
    createMut.mutate({ username: form.username, password: form.password, role: form.role, email: form.email || undefined })
  }

  function handleDelete(user: User) {
    if (!globalThis.confirm(`Delete user "${user.username}"? This cannot be undone.`)) return
    deleteMut.mutate(user.id)
  }

  function handleExport(user: User) {
    exportUserData(user.id).then(data => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `flowforge-gdpr-export-${user.username}.json`
      a.click()
      URL.revokeObjectURL(url)
    }).catch((e: Error) => globalThis.alert(`Export failed: ${e.message}`))
  }

  function handlePurge(user: User) {
    if (!globalThis.confirm(
      `GDPR purge: delete "${user.username}" and anonymise all their audit log entries?\n\nThis cannot be undone.`
    )) return
    purgeUserData(user.id)
      .then(() => qc.invalidateQueries({ queryKey: ['users'] }))
      .catch((e: Error) => globalThis.alert(`Purge failed: ${e.message}`))
  }

  return (
    <>
      <TopBar crumbs={['System', 'Users']} helpTopic="settings" />
      <div className="scroll" style={{ maxWidth: 780 }}>
        <div className="page-h">
          <h1>Users</h1>
          <button className="btn btn-primary" onClick={() => { setShowAdd(true); setFormError('') }}>
            <Plus size={14} /> Add User
          </button>
        </div>

        {/* Add User modal */}
        {showAdd && (
          <div style={{
            position: 'fixed', inset: 0, zIndex: 50,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
          }}>
            <div className="card" style={{ width: '100%', maxWidth: 420, padding: 24, position: 'relative' }}>
              <button
                onClick={() => { setShowAdd(false); setForm(emptyForm()); setFormError('') }}
                style={{ position: 'absolute', top: 16, right: 16, background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={16} />
              </button>
              <h3 style={{ margin: '0 0 18px', fontSize: 14, fontWeight: 600 }}>Add User</h3>
              <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div className="field">
                  <label htmlFor="user-form-username">Username</label>
                  <input
                    id="user-form-username"
                    className="input"
                    value={form.username}
                    onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                    autoFocus
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="user-form-password">Password</label>
                  <input
                    id="user-form-password"
                    className="input"
                    type="password"
                    value={form.password}
                    onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="user-form-role">Role</label>
                  <select
                    id="user-form-role"
                    className="input"
                    value={form.role}
                    onChange={e => setForm(f => ({ ...f, role: e.target.value as Role }))}
                  >
                    {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="user-form-email">Email <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>(optional — for password reset)</span></label>
                  <input
                    id="user-form-email"
                    className="input"
                    type="email"
                    value={form.email}
                    onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                    placeholder="user@example.com"
                  />
                </div>
                {formError && (
                  <div style={{ fontSize: 12.5, color: 'var(--failure-text)', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: '8px 12px' }}>
                    {formError}
                  </div>
                )}
                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                  <button type="button" className="btn" onClick={() => { setShowAdd(false); setForm(emptyForm()) }}>Cancel</button>
                  <button type="submit" className="btn btn-primary" disabled={createMut.isPending}>
                    {createMut.isPending ? 'Creating…' : 'Create User'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Users table */}
        <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
          {usersTableContent}
        </div>
      </div>
    </>
  )
}
