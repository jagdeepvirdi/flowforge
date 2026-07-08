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

const ROLE_CLS: Record<Role, string> = {
  admin:  'bg-[rgba(249,115,22,0.12)] text-accent-text',
  editor: 'bg-[rgba(59,130,246,0.12)] text-blue-400',
  viewer: 'bg-[rgba(107,114,128,0.12)] text-text-muted',
}

function RoleBadge({ role }: { role: Role }) {
  return (
    <span className={`inline-block text-[11px] font-semibold py-0.5 px-2 rounded uppercase tracking-[0.06em] ${ROLE_CLS[role]}`}>
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
    <div className="p-6 flex flex-col gap-3">
      {[1, 2, 3].map(i => <Sk key={i} style={{ height: 36 }} />)}
    </div>
  ) : users.length === 0 ? (
    <div className="p-8 text-center text-text-muted text-[13px]">
      No users yet.
    </div>
  ) : (
    <table className="w-full border-collapse">
      <thead>
        <tr className="border-b border-border">
          {['Username', 'Email', 'Role', 'Created', 'MFA', ''].map(h => (
            <th key={h} className="py-2.5 px-4 text-left text-[11px] font-semibold text-text-muted uppercase tracking-[0.05em]">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {users.map((user, i) => (
          <tr key={user.id} className={i < users.length - 1 ? 'border-b border-border' : ''}>
            <td className="py-3 px-4 text-[13px] text-text-primary font-medium">
              {user.username}
              {user.id === me?.id && (
                <span className="ml-1.5 text-[10.5px] text-text-muted font-normal">(you)</span>
              )}
            </td>
            <td className="py-3 px-4 text-xs text-text-muted">
              {user.email
                ? <span className="mono">{user.email}</span>
                : <span className="text-text-dim italic">not set</span>}
            </td>
            <td className="py-3 px-4">
              {user.id === me?.id ? (
                <RoleBadge role={user.role} />
              ) : (
                <select
                  className="input text-xs py-[3px] px-2 w-auto"
                  value={user.role}
                  disabled={roleMut.isPending}
                  onChange={e => roleMut.mutate({ id: user.id, role: e.target.value as Role })}
                >
                  {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              )}
            </td>
            <td className="py-3 px-4 text-xs text-text-muted font-mono">
              {user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
            </td>
            <td className="py-3 px-4">
              <span className={`text-[10.5px] font-semibold py-0.5 px-1.5 rounded-[3px] ${user.mfa_enabled ? 'bg-[rgba(34,197,94,0.12)] text-success-text' : 'bg-[rgba(107,114,128,0.1)] text-text-dim'}`}>
                {user.mfa_enabled ? 'ON' : 'OFF'}
              </span>
            </td>
            <td className="py-3 px-4 text-right">
              <div className="flex gap-1 justify-end">
                <button
                  className="btn py-1 px-2 text-[11px]"
                  onClick={() => handleExport(user)}
                  title="GDPR export — download all personal data as JSON"
                >
                  <Download size={12} />
                </button>
                {user.id !== me?.id && (
                  <>
                    <button
                      className="btn py-1 px-2 text-failure-text text-[11px]"
                      disabled={deleteMut.isPending}
                      onClick={() => handleDelete(user)}
                      title="Delete user"
                    >
                      <Trash2 size={12} />
                    </button>
                    <button
                      className="btn py-1 px-2 text-failure-text text-[10px]"
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
      <div className="scroll max-w-[780px]">
        <div className="page-h">
          <h1>Users</h1>
          <button className="btn btn-primary" onClick={() => { setShowAdd(true); setFormError('') }}>
            <Plus size={14} /> Add User
          </button>
        </div>

        {/* Add User modal */}
        {showAdd && (
          <div className="fixed inset-0 z-50 bg-[rgba(0,0,0,0.5)] flex items-center justify-center p-4">
            <div className="card w-full max-w-[420px] p-6 relative">
              <button
                onClick={() => { setShowAdd(false); setForm(emptyForm()); setFormError('') }}
                className="absolute top-4 right-4 bg-transparent border-none cursor-pointer text-text-muted"
              >
                <X size={16} />
              </button>
              <h3 className="m-0 mb-[18px] text-sm font-semibold">Add User</h3>
              <form onSubmit={handleAdd} className="flex flex-col gap-3.5">
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
                  <label htmlFor="user-form-email">Email <span className="text-[11px] text-text-muted font-normal">(optional — for password reset)</span></label>
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
                  <div className="text-[12.5px] text-failure-text bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-r-sm py-2 px-3">
                    {formError}
                  </div>
                )}
                <div className="flex gap-2 justify-end">
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
        <div className="card overflow-hidden p-0">
          {usersTableContent}
        </div>
      </div>
    </>
  )
}
