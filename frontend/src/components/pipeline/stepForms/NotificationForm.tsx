import Field from './Field'
import type { StepFormProps } from './types'

export default function NotificationForm({ cfg, setConfig }: StepFormProps) {
  const platform = String(cfg.platform ?? 'slack')

  return (
    <>
      <Field label="Platform">
        <select className="input" value={platform} onChange={e => setConfig('platform', e.target.value)} style={{ height: 34 }}>
          <option value="slack">Slack</option>
          <option value="teams">Microsoft Teams</option>
          <option value="telegram">Telegram</option>
        </select>
      </Field>

      {(platform === 'slack' || platform === 'teams') && (
        <Field label="Webhook URL">
          <input className="input" type="url" value={String(cfg.webhook_url ?? '')} onChange={e => setConfig('webhook_url', e.target.value)} placeholder="https://hooks.slack.com/…" />
        </Field>
      )}

      {platform === 'telegram' && (
        <>
          <Field label="Bot token">
            <input className="input" type="password" value={String(cfg.bot_token ?? '')} onChange={e => setConfig('bot_token', e.target.value)} placeholder="123456:ABC-DEF…" />
          </Field>
          <Field label="Chat ID">
            <input className="input mono-input" value={String(cfg.chat_id ?? '')} onChange={e => setConfig('chat_id', e.target.value)} placeholder="-100123456789" />
          </Field>
        </>
      )}

      <Field label="Title (optional)">
        <input className="input" value={String(cfg.title ?? '')} onChange={e => setConfig('title', e.target.value)} placeholder="Pipeline alert" />
      </Field>

      <Field label="Message (Jinja2)">
        <textarea className="input mono-input" rows={3} value={String(cfg.message ?? '')} onChange={e => setConfig('message', e.target.value)}
          placeholder="Pipeline {{ pipeline_name }} finished at {{ current_date }}."
          style={{ height: 'auto', resize: 'none' }} />
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
          Supports all pipeline variables: <code style={{ color: 'var(--text-3)' }}>{'{{ pipeline_name }}'}</code> <code style={{ color: 'var(--text-3)' }}>{'{{ run_id }}'}</code> <code style={{ color: 'var(--text-3)' }}>{'{{ current_date }}'}</code>
        </span>
      </Field>
    </>
  )
}
