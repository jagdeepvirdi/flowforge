import { Shield, ShieldCheck, ShieldOff } from 'lucide-react'
import Spinner from '../shared/Spinner'
import { useMfa } from '../../hooks/useMfa'

export default function MfaCard() {
  const {
    enabled, phase, setPhase,
    qrDataUrl, secret, uri,
    code, setCode,
    password, setPassword,
    backupCodes, setBackupCodes,
    error, setError,
    copied, copySecret,
    enrollMut, confirmMut, disableMut,
  } = useMfa()

  return (
    <div className="card flex flex-col gap-3.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-[7px] text-[13px] font-semibold text-text-primary">
          {enabled ? <ShieldCheck size={15} className="text-success" /> : <Shield size={15} className="text-text-muted" />}
          Two-Factor Authentication (MFA)
        </div>
        <span className={`text-[11px] font-semibold py-0.5 px-2 rounded uppercase tracking-[0.06em] ${enabled ? 'bg-[rgba(34,197,94,0.12)] text-success-text' : 'bg-[rgba(107,114,128,0.12)] text-text-muted'}`}>
          {enabled ? 'Active' : 'Disabled'}
        </span>
      </div>

      <p className="text-[13px] text-text-muted m-0">
        {enabled
          ? 'MFA is active on your account. You will be asked for a TOTP code on every login.'
          : 'Add a second factor to your account using any TOTP authenticator app (Google Authenticator, Authy, 1Password, etc.).'}
      </p>

      {error && (
        <div className="text-[12.5px] text-failure-text bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-r-sm py-2 px-3">
          {error}
        </div>
      )}

      {/* ── Not enrolled → start enrollment ── */}
      {!enabled && phase === 'idle' && (
        <button className="btn btn-primary self-start"
          onClick={() => { setError(''); enrollMut.mutate() }}
          disabled={enrollMut.isPending}>
          {enrollMut.isPending ? <Spinner size={13} /> : 'Enable MFA'}
        </button>
      )}

      {/* ── Scan QR / copy secret ── */}
      {phase === 'confirming' && (
        <div className="flex flex-col gap-3.5">
          <p className="text-[13px] text-text-2 m-0">
            Scan the QR code with your authenticator app, then enter the 6-digit code to confirm.
          </p>
          {qrDataUrl
            ? <img src={qrDataUrl} alt="MFA QR code" width={160} height={160} className="rounded-r border border-border bg-white" />
            : (
              <div className="flex flex-col gap-1.5">
                <span className="text-xs text-text-muted">Manual entry secret:</span>
                <div className="flex gap-2 items-center">
                  <code className="mono text-[13px] bg-surface2 border border-border rounded-r-sm py-1.5 px-2.5 flex-1 [overflow-wrap:anywhere]">
                    {secret}
                  </code>
                  <button className="btn whitespace-nowrap text-xs" onClick={copySecret}>
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <a href={uri} className="text-xs text-accent-text">Open in authenticator app</a>
              </div>
            )
          }
          <form onSubmit={e => { e.preventDefault(); confirmMut.mutate() }} className="flex flex-col gap-2.5">
            <div className="field">
              <label htmlFor="mfa-confirm-code">Verification code</label>
              <input
                id="mfa-confirm-code"
                className="input mono tracking-[0.3em] text-lg text-center max-w-40"
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder="000000"
                value={code}
                onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
                autoFocus
                required
              />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn btn-primary" disabled={confirmMut.isPending || code.length !== 6}>
                {confirmMut.isPending ? 'Activating…' : 'Activate MFA'}
              </button>
              <button type="button" className="btn" onClick={() => { setPhase('idle'); setError('') }}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* ── Show backup codes once ── */}
      {phase === 'backup-codes' && (
        <div className="flex flex-col gap-3">
          <div className="py-2.5 px-3.5 bg-[rgba(34,197,94,0.08)] border border-[rgba(34,197,94,0.2)] rounded-r-sm text-[13px] text-success-text">
            MFA activated! Save these backup codes — they are shown only once.
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {backupCodes.map(c => (
              <code key={c} className="mono text-[13px] bg-surface2 border border-border rounded py-[5px] px-2.5 text-center">
                {c}
              </code>
            ))}
          </div>
          <button className="btn btn-primary self-start" onClick={() => { setPhase('idle'); setBackupCodes([]) }}>
            Done — I've saved my backup codes
          </button>
        </div>
      )}

      {/* ── Disable MFA ── */}
      {enabled && phase === 'idle' && (
        <button
          className="btn self-start text-failure-text flex items-center gap-[5px]"
          onClick={() => { setPhase('disabling'); setError('') }}
        >
          <ShieldOff size={13} /> Disable MFA
        </button>
      )}

      {phase === 'disabling' && (
        <form onSubmit={e => { e.preventDefault(); disableMut.mutate() }} className="flex flex-col gap-2.5">
          <div className="field">
            <label htmlFor="mfa-disable-password">Confirm your password to disable MFA</label>
            <input
              id="mfa-disable-password"
              className="input"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn text-failure-text" disabled={disableMut.isPending}>
              {disableMut.isPending ? 'Disabling…' : 'Disable MFA'}
            </button>
            <button type="button" className="btn" onClick={() => { setPhase('idle'); setError('') }}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  )
}
