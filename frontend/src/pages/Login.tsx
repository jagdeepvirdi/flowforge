import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, getMe, mfaVerify, mfaUseBackup, getSsoProviders, requestPasswordReset, confirmPasswordReset, validateResetToken } from '../lib/api'
import { useAuth } from '../lib/auth'

type LoginStep = 'credentials' | 'mfa-code' | 'mfa-backup' | 'forgot-password' | 'forgot-sent' | 'reset-password' | 'reset-done'

export default function Login() {
  const { setToken, setUser } = useAuth()
  const navigate = useNavigate()

  const [step, setStep]         = useState<LoginStep>('credentials')
  const [mfaToken, setMfaToken] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [mfaCode, setMfaCode]   = useState('')
  const [backupCode, setBackupCode] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [ssoProviders, setSsoProviders] = useState<{ google: boolean; microsoft: boolean } | null>(null)

  // Handle SSO token delivered via URL hash (#sso_token=...)
  useEffect(() => {
    const hash = globalThis.location.hash
    const ssoMatch = hash.match(/sso_token=([^&]+)/)
    const errMatch  = hash.match(/sso_error=([^&]+)/)

    if (ssoMatch) {
      const token = decodeURIComponent(ssoMatch[1])
      setToken(token)
      getMe().then(user => {
        setUser(user)
        navigate('/dashboard', { replace: true })
      }).catch(() => setError('SSO login failed — token invalid'))
      globalThis.history.replaceState(null, '', globalThis.location.pathname)
      return
    }

    if (errMatch) {
      setError(`SSO error: ${decodeURIComponent(errMatch[1]).replace(/\+/g, ' ')}`)
      globalThis.history.replaceState(null, '', globalThis.location.pathname)
    }

    // Handle password reset token from email link
    const resetMatch = hash.match(/reset_token=([^&]+)/)
    if (resetMatch) {
      const tok = decodeURIComponent(resetMatch[1])
      globalThis.history.replaceState(null, '', globalThis.location.pathname)
      validateResetToken(tok)
        .then(({ valid }) => {
          if (valid) { setResetToken(tok); setStep('reset-password') }
          else setError('This password reset link has expired or already been used.')
        })
        .catch(() => setError('Could not validate reset link.'))
    }
  }, [])

  // Load SSO provider availability (no auth required)
  useEffect(() => {
    getSsoProviders()
      .then(setSsoProviders)
      .catch(() => setSsoProviders({ google: false, microsoft: false }))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const result = await login(username, password)
      if ('mfa_required' in result && result.mfa_required) {
        setMfaToken(result.mfa_token)
        setStep('mfa-code')
      } else if ('token' in result) {
        setToken(result.token)
        const user = await getMe()
        setUser(user)
        navigate('/dashboard')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleMfaVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { token } = await mfaVerify(mfaToken, mfaCode)
      setToken(token)
      const user = await getMe()
      setUser(user)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid code')
    } finally {
      setLoading(false)
    }
  }

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await requestPasswordReset(username)
      setStep('forgot-sent')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (newPassword.length < 8) { setError('Password must be at least 8 characters'); return }
    if (newPassword !== confirmPassword) { setError('Passwords do not match'); return }
    setLoading(true)
    try {
      await confirmPasswordReset(resetToken, newPassword)
      setStep('reset-done')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed')
    } finally {
      setLoading(false)
    }
  }

  const handleMfaBackup = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { token } = await mfaUseBackup(mfaToken, backupCode)
      setToken(token)
      const user = await getMe()
      setUser(user)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid backup code')
    } finally {
      setLoading(false)
    }
  }

  const anySso = ssoProviders && (ssoProviders.google || ssoProviders.microsoft)

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div style={{ width: '100%', maxWidth: 360 }}>
        {/* Brand */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <defs>
                <linearGradient id="flame-login" x1="16" y1="32" x2="16" y2="0" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#EA580C" />
                  <stop offset="60%" stopColor="var(--accent)" />
                  <stop offset="100%" stopColor="#FCD34D" />
                </linearGradient>
              </defs>
              <path d="M16 2C16 2 10 8 10 14C10 17.3 12 19.5 12 19.5C12 19.5 11 17 13 15C13 15 12 20 16 22C20 20 19 15 19 15C21 17 20 19.5 20 19.5C20 19.5 22 17.3 22 14C22 8 16 2 16 2Z" fill="url(#flame-login)" />
              <path d="M16 18C14.5 17 14 15.5 14 14.5C14 14.5 14.5 16 16 16.5C17.5 16 18 14.5 18 14.5C18 15.5 17.5 17 16 18Z" fill="#FEF3C7" opacity="0.8" />
            </svg>
            <span style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)', fontFamily: 'Inter, sans-serif', letterSpacing: '-0.01em' }}>FlowForge</span>
          </div>
        </div>

        <div className="card" style={{ padding: '28px 24px' }}>

          {/* ── Step 1: Credentials ── */}
          {step === 'credentials' && (
            <>
              <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 20, marginTop: 0 }}>Sign in</h2>
              <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div className="field">
                  <label htmlFor="login-username">Username</label>
                  <input
                    id="login-username"
                    className="input"
                    type="text"
                    data-testid="username"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    autoFocus
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="login-password">Password</label>
                  <input
                    id="login-password"
                    className="input"
                    type="password"
                    data-testid="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                  />
                </div>
                {error && <ErrorBox>{error}</ErrorBox>}
                <button type="submit" className="btn btn-primary" disabled={loading}
                  style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}>
                  {loading ? 'Signing in…' : 'Sign in'}
                </button>
                <button type="button"
                  style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', marginTop: 6, fontSize: 12, color: 'var(--accent-text)', textDecoration: 'none' }}
                  onClick={() => { setStep('forgot-password'); setError('') }}>
                  Forgot password?
                </button>
              </form>

              {anySso && (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '18px 0 14px' }}>
                    <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>or continue with</span>
                    <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {ssoProviders.google && (
                      <a href="/api/auth/sso/google" className="btn" style={{ width: '100%', justifyContent: 'center', gap: 8, textDecoration: 'none' }}>
                        <GoogleIcon /> Sign in with Google
                      </a>
                    )}
                    {ssoProviders.microsoft && (
                      <a href="/api/auth/sso/microsoft" className="btn" style={{ width: '100%', justifyContent: 'center', gap: 8, textDecoration: 'none' }}>
                        <MicrosoftIcon /> Sign in with Microsoft
                      </a>
                    )}
                  </div>
                </>
              )}
            </>
          )}

          {/* ── Step 2a: MFA code ── */}
          {step === 'mfa-code' && (
            <>
              <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 8, marginTop: 0 }}>Two-factor authentication</h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 18 }}>
                Enter the 6-digit code from your authenticator app.
              </p>
              <form onSubmit={handleMfaVerify} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div className="field">
                  <label htmlFor="mfa-code">Authenticator code</label>
                  <input
                    id="mfa-code"
                    className="input mono"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    placeholder="000000"
                    value={mfaCode}
                    onChange={e => setMfaCode(e.target.value.replace(/\D/g, ''))}
                    autoFocus
                    required
                    style={{ letterSpacing: '0.3em', fontSize: 18, textAlign: 'center' }}
                  />
                </div>
                {error && <ErrorBox>{error}</ErrorBox>}
                <button type="submit" className="btn btn-primary" disabled={loading || mfaCode.length !== 6}
                  style={{ width: '100%', justifyContent: 'center' }}>
                  {loading ? 'Verifying…' : 'Verify'}
                </button>
              </form>
              <button
                type="button"
                className="btn"
                style={{ width: '100%', justifyContent: 'center', marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}
                onClick={() => { setStep('mfa-backup'); setError('') }}
              >
                Use a backup code instead
              </button>
              <button
                type="button"
                style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', marginTop: 6, fontSize: 12, color: 'var(--text-dim)', textDecoration: 'underline' }}
                onClick={() => { setStep('credentials'); setError('') }}
              >
                ← Back to sign in
              </button>
            </>
          )}

          {/* ── Forgot password ── */}
          {step === 'forgot-password' && (
            <>
              <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 8, marginTop: 0 }}>Forgot password</h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 18 }}>
                Enter your username. If an account with a registered email exists, you'll receive a reset link.
              </p>
              <form onSubmit={handleForgotPassword} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div className="field">
                  <label htmlFor="forgot-username">Username</label>
                  <input id="forgot-username" className="input" type="text" value={username}
                    onChange={e => setUsername(e.target.value)} autoFocus required />
                </div>
                {error && <ErrorBox>{error}</ErrorBox>}
                <button type="submit" className="btn btn-primary" disabled={loading}
                  style={{ width: '100%', justifyContent: 'center' }}>
                  {loading ? 'Sending…' : 'Send reset link'}
                </button>
              </form>
              <button type="button"
                style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', marginTop: 10, fontSize: 12, color: 'var(--text-dim)', textDecoration: 'underline' }}
                onClick={() => { setStep('credentials'); setError('') }}>
                ← Back to sign in
              </button>
            </>
          )}

          {/* ── Forgot-sent confirmation ── */}
          {step === 'forgot-sent' && (
            <>
              <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 8, marginTop: 0 }}>Check your email</h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                If an account for <strong>{username}</strong> has a registered email address, a reset link has been sent. It expires in 1 hour.
              </p>
              <button type="button" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: 18 }}
                onClick={() => { setStep('credentials'); setError('') }}>
                Back to sign in
              </button>
            </>
          )}

          {/* ── Reset password form (arrived via email link) ── */}
          {step === 'reset-password' && (
            <>
              <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 8, marginTop: 0 }}>Set new password</h2>
              <form onSubmit={handleResetPassword} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div className="field">
                  <label htmlFor="reset-new-password">New password</label>
                  <input id="reset-new-password" className="input" type="password" value={newPassword}
                    onChange={e => setNewPassword(e.target.value)} autoFocus required minLength={8} />
                </div>
                <div className="field">
                  <label htmlFor="reset-confirm-password">Confirm new password</label>
                  <input id="reset-confirm-password" className="input" type="password" value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)} required />
                </div>
                {error && <ErrorBox>{error}</ErrorBox>}
                <button type="submit" className="btn btn-primary" disabled={loading}
                  style={{ width: '100%', justifyContent: 'center' }}>
                  {loading ? 'Saving…' : 'Set password'}
                </button>
              </form>
            </>
          )}

          {/* ── Reset done ── */}
          {step === 'reset-done' && (
            <>
              <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 8, marginTop: 0 }}>Password updated</h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>Your password has been set successfully. You can now sign in.</p>
              <button type="button" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: 18 }}
                onClick={() => { setStep('credentials'); setError(''); setNewPassword(''); setConfirmPassword('') }}>
                Sign in
              </button>
            </>
          )}

          {/* ── Step 2b: backup code ── */}
          {step === 'mfa-backup' && (
            <>
              <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', marginBottom: 8, marginTop: 0 }}>Backup code</h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 18 }}>
                Enter one of the one-time backup codes you saved during MFA setup.
              </p>
              <form onSubmit={handleMfaBackup} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div className="field">
                  <label htmlFor="mfa-backup-code">Backup code</label>
                  <input
                    id="mfa-backup-code"
                    className="input mono"
                    type="text"
                    placeholder="XXXX-XXXX"
                    value={backupCode}
                    onChange={e => setBackupCode(e.target.value.toUpperCase())}
                    autoFocus
                    required
                  />
                </div>
                {error && <ErrorBox>{error}</ErrorBox>}
                <button type="submit" className="btn btn-primary" disabled={loading}
                  style={{ width: '100%', justifyContent: 'center' }}>
                  {loading ? 'Verifying…' : 'Use backup code'}
                </button>
              </form>
              <button
                type="button"
                style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', marginTop: 10, fontSize: 12, color: 'var(--text-dim)', textDecoration: 'underline' }}
                onClick={() => { setStep('mfa-code'); setError('') }}
              >
                ← Use authenticator code
              </button>
            </>
          )}
        </div>

        <p style={{ textAlign: 'center', marginTop: 20, fontSize: 12, color: 'var(--text-dim)' }}>
          FlowForge — database-driven pipeline orchestrator
        </p>
      </div>
    </div>
  )
}

function ErrorBox({ children }: Readonly<{ children: string }>) {
  return (
    <div style={{ fontSize: 12.5, color: 'var(--failure-text)', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: '8px 12px' }}>
      {children}
    </div>
  )
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  )
}

function MicrosoftIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 21 21" fill="none">
      <rect x="1" y="1" width="9" height="9" fill="#F25022"/>
      <rect x="11" y="1" width="9" height="9" fill="#7FBA00"/>
      <rect x="1" y="11" width="9" height="9" fill="#00A4EF"/>
      <rect x="11" y="11" width="9" height="9" fill="#FFB900"/>
    </svg>
  )
}
