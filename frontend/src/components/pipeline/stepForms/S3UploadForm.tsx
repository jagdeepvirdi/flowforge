import Field from './Field'
import type { StepFormProps } from './types'

export default function S3UploadForm({ cfg, setConfig }: StepFormProps) {
  return (
    <>
      <Field label="File path (supports {{ variables }})">
        <input className="input mono-input" value={String(cfg.file_path ?? '')} onChange={e => setConfig('file_path', e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-2.5">
        <Field label="Bucket">
          <input className="input" value={String(cfg.bucket ?? '')} onChange={e => setConfig('bucket', e.target.value)} placeholder="my-bucket" />
        </Field>
        <Field label="Key (optional)">
          <input className="input" value={String(cfg.key ?? '')} onChange={e => setConfig('key', e.target.value)} placeholder="reports/report_{{ current_month }}.xlsx" />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        <Field label="Rename to (optional)">
          <input className="input" value={String(cfg.rename_to ?? '')} onChange={e => setConfig('rename_to', e.target.value)} placeholder="report_{{ current_month }}.xlsx" />
        </Field>
        <label className="flex items-center gap-1.5 text-xs text-text-3 mt-[18px]">
          <input type="checkbox" checked={Boolean(cfg.presigned_url ?? true)} onChange={e => setConfig('presigned_url', e.target.checked)} />{' '}
          Return presigned URL
        </label>
      </div>
    </>
  )
}
