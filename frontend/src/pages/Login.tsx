import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../lib/api'
import { useAuth } from '../lib/auth'

export default function Login() {
  const { setToken } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { token } = await login(username, password)
      setToken(token)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0F1117', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div style={{ width: '100%', maxWidth: 360 }}>
        {/* Brand */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <defs>
                <linearGradient id="flame-login" x1="16" y1="32" x2="16" y2="0" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#EA580C" />
                  <stop offset="60%" stopColor="#F97316" />
                  <stop offset="100%" stopColor="#FCD34D" />
                </linearGradient>
              </defs>
              <path d="M16 2C16 2 10 8 10 14C10 17.3 12 19.5 12 19.5C12 19.5 11 17 13 15C13 15 12 20 16 22C20 20 19 15 19 15C21 17 20 19.5 20 19.5C20 19.5 22 17.3 22 14C22 8 16 2 16 2Z" fill="url(#flame-login)" />
              <path d="M16 18C14.5 17 14 15.5 14 14.5C14 14.5 14.5 16 16 16.5C17.5 16 18 14.5 18 14.5C18 15.5 17.5 17 16 18Z" fill="#FEF3C7" opacity="0.8" />
            </svg>
            <span style={{ fontSize: 22, fontWeight: 600, color: '#F1F5F9', fontFamily: 'Inter, sans-serif', letterSpacing: '-0.01em' }}>FlowForge</span>
          </div>
        </div>

        <div className="card" style={{ padding: '28px 24px' }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: '#F1F5F9', marginBottom: 20, marginTop: 0 }}>Sign in</h2>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="field">
              <label>Username</label>
              <input
                className="input"
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                autoFocus
                required
              />
            </div>

            <div className="field">
              <label>Password</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <div style={{ fontSize: 12.5, color: '#F87171', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: '8px 12px' }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

        <p style={{ textAlign: 'center', marginTop: 20, fontSize: 12, color: '#475569' }}>
          FlowForge — database-driven pipeline orchestrator
        </p>
      </div>
    </div>
  )
}
