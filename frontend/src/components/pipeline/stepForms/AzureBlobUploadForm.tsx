import Field from './Field'
import type { StepFormProps } from './types'

export default function AzureBlobUploadForm({ cfg, setConfig }: StepFormProps) {
  return (
    <>
      <Field label="File path (supports {{ variables }})">
        <input className="input mono-input" value={String(cfg.file_path ?? '')} onChange={e => setConfig('file_path', e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-2.5">
        <Field label="Container">
          <input className="input" value={String(cfg.container ?? '')} onChange={e => setConfig('container', e.target.value)} placeholder="mycontainer" />
        </Field>
        <Field label="Blob name (optional)">
          <input className="input" value={String(cfg.blob_name ?? '')} onChange={e => setConfig('blob_name', e.target.value)} placeholder="report_{{ current_month }}.xlsx" />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        <Field label="Rename to (optional)">
          <input className="input" value={String(cfg.rename_to ?? '')} onChange={e => setConfig('rename_to', e.target.value)} placeholder="report_{{ current_month }}.xlsx" />
        </Field>
        <label className="flex items-center gap-1.5 text-xs text-text-3 mt-[18px]">
          <input type="checkbox" checked={Boolean(cfg.shareable_url ?? true)} onChange={e => setConfig('shareable_url', e.target.checked)} />{' '}
          Return shareable (SAS) URL
        </label>
      </div>
    </>
  )
}
