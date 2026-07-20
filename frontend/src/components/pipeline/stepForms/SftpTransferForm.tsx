import { useState } from 'react'
import { ChevronDown, ChevronUp, Settings2 } from 'lucide-react'
import Field from './Field'
import FieldTooltip from '../../shared/FieldTooltip'
import type { StepFormProps } from './types'

export default function SftpTransferForm({ cfg, setConfig }: StepFormProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)
  // Toggle is user-driven, not derived from field content — otherwise picking
  // "Private key auth" before typing a key path would immediately snap back
  // to "Password auth" (key_path is still empty at that point).
  const [authMethod, setAuthMethod] = useState<'password' | 'key'>(() => (cfg.key_path ? 'key' : 'password'))

  const operation = String(cfg.operation ?? 'download')

  const switchAuthMethod = (method: 'password' | 'key') => {
    setAuthMethod(method)
    if (method === 'password') {
      setConfig('key_path', '')
      setConfig('key_passphrase', '')
    } else {
      setConfig('password', '')
    }
  }

  return (
    <>
      {/* Operation toggle */}
      <div className="flex gap-0 rounded-r-sm overflow-hidden border border-border-strong w-fit">
        {(['download', 'upload'] as const).map(op => (
          <button
            key={op}
            type="button"
            onClick={() => setConfig('operation', op)}
            className={`py-[5px] px-4 text-xs font-semibold border-none cursor-pointer transition-colors duration-150 ${operation === op ? 'bg-accent text-white' : 'bg-transparent text-text-muted'}`}
          >
            {op === 'download' ? 'Download from server' : 'Upload to server'}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-[1fr_auto] gap-2.5">
        <Field label="Host">
          <input className="input mono-input" value={String(cfg.host ?? '')} onChange={e => setConfig('host', e.target.value)} placeholder="sftp.example.com" />
        </Field>
        <Field label="Port">
          <input className="input w-[90px]" type="number" min={1} max={65535} value={String(cfg.port ?? 22)} onChange={e => setConfig('port', Number.parseInt(e.target.value) || 22)} />
        </Field>
      </div>

      <Field label="Username">
        <input className="input" value={String(cfg.username ?? '')} onChange={e => setConfig('username', e.target.value)} placeholder="sftpuser" />
      </Field>

      <div className="flex gap-0 rounded-r-sm overflow-hidden border border-border-strong w-fit">
        {(['password', 'key'] as const).map(m => (
          <button
            key={m}
            type="button"
            onClick={() => switchAuthMethod(m)}
            className={`py-[5px] px-4 text-xs font-semibold border-none cursor-pointer transition-colors duration-150 ${authMethod === m ? 'bg-accent text-white' : 'bg-transparent text-text-muted'}`}
          >
            {m === 'password' ? 'Password auth' : 'Private key auth'}
          </button>
        ))}
      </div>

      {authMethod === 'password' && (
        <Field label="Password">
          <input className="input" type="password" value={String(cfg.password ?? '')} onChange={e => setConfig('password', e.target.value)} placeholder="•••••••••" />
        </Field>
      )}

      {authMethod === 'key' && (
        <div className="grid grid-cols-2 gap-2.5">
          <Field label="Private key path">
            <input className="input mono-input" value={String(cfg.key_path ?? '')} onChange={e => setConfig('key_path', e.target.value)} placeholder="/etc/flowforge/keys/sftp_id_rsa" />
          </Field>
          <Field label="Key passphrase (optional)">
            <input className="input" type="password" value={String(cfg.key_passphrase ?? '')} onChange={e => setConfig('key_passphrase', e.target.value)} placeholder="•••••••••" />
          </Field>
        </div>
      )}

      <Field label="Remote path (supports {{ variables }})" tooltip={<FieldTooltip field="sftp_remote_path" />}>
        <input className="input mono-input" value={String(cfg.remote_path ?? '')} onChange={e => setConfig('remote_path', e.target.value)} placeholder={operation === 'download' ? '/incoming/reports/' : '/outgoing/report_{{ current_date }}.csv'} />
      </Field>

      <Field label="Local path (supports {{ variables }})">
        <input className="input mono-input" value={String(cfg.local_path ?? '')} onChange={e => setConfig('local_path', e.target.value)} placeholder={operation === 'download' ? 'downloads/{{ current_date }}/' : "{{ steps.generate_report.output_path }}"} />
      </Field>

      {/* ── Advanced (collapsible) ────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setShowAdvanced(x => !x)}
        className="flex items-center gap-1.5 bg-transparent border-none text-text-muted text-[11.5px] cursor-pointer py-0.5 px-0 font-medium"
      >
        <Settings2 size={12} />
        Advanced options
        {showAdvanced ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>

      {showAdvanced && (
        <div className="flex flex-col gap-2.5 pl-3 border-l-2 border-border">
          {operation === 'download' && (
            <Field label="Filename pattern (optional, directory downloads only)">
              <input className="input mono-input" value={String(cfg.pattern ?? '')} onChange={e => setConfig('pattern', e.target.value)} placeholder="*.csv" />
            </Field>
          )}

          <Field label="Connection timeout (seconds)">
            <input className="input w-[120px]" type="number" min={1} max={600} value={String(cfg.timeout ?? 30)} onChange={e => setConfig('timeout', Number.parseInt(e.target.value) || 30)} />
          </Field>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input type="checkbox" checked={Boolean(cfg.overwrite ?? true)} onChange={e => setConfig('overwrite', e.target.checked)} />
            <span className="text-[12.5px] text-text-2">
              Overwrite existing files at the destination
            </span>
          </label>

          {operation === 'upload' && (
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" checked={Boolean(cfg.create_remote_dirs ?? true)} onChange={e => setConfig('create_remote_dirs', e.target.checked)} />
              <span className="text-[12.5px] text-text-2">
                Create missing remote directories before uploading
              </span>
            </label>
          )}
        </div>
      )}
    </>
  )
}
