import { useChangePassword } from '../../hooks/useChangePassword'

export default function ChangePasswordCard() {
  const { form, setForm, error, success, mut, handleSubmit } = useChangePassword()

  return (
    <div className="card flex flex-col gap-3.5">
      <div className="text-[13px] font-semibold text-text-primary">Change Password</div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2.5">
        <div className="field">
          <label htmlFor="settings-current-password">Current Password</label>
          <input id="settings-current-password" className="input" type="password" value={form.current_password}
            onChange={e => setForm(f => ({ ...f, current_password: e.target.value }))} required />
        </div>
        <div className="field">
          <label htmlFor="settings-new-password">New Password</label>
          <input id="settings-new-password" className="input" type="password" value={form.new_password}
            onChange={e => setForm(f => ({ ...f, new_password: e.target.value }))} required />
        </div>
        <div className="field">
          <label htmlFor="settings-confirm-password">Confirm New Password</label>
          <input id="settings-confirm-password" className="input" type="password" value={form.confirm}
            onChange={e => setForm(f => ({ ...f, confirm: e.target.value }))} required />
        </div>
        {error && (
          <div className="text-[12.5px] text-failure-text bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-r-sm py-2 px-3">
            {error}
          </div>
        )}
        {success && (
          <div className="text-[12.5px] text-success-text bg-[rgba(34,197,94,0.08)] border border-[rgba(34,197,94,0.2)] rounded-r-sm py-2 px-3">
            Password changed successfully.
          </div>
        )}
        <div>
          <button type="submit" className="btn btn-primary" disabled={mut.isPending}>
            {mut.isPending ? 'Saving…' : 'Change Password'}
          </button>
        </div>
      </form>
    </div>
  )
}
