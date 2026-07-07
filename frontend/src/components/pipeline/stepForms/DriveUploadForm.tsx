import FieldTooltip from '../../shared/FieldTooltip'
import Field from './Field'
import type { StepFormProps } from './types'

export default function DriveUploadForm({ cfg, setConfig }: StepFormProps) {
  return (
    <>
      <Field label="File path (supports {{ variables }})">
        <input className="input mono-input" value={String(cfg.file_path ?? '')} onChange={e => setConfig('file_path', e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-2.5">
        <Field label="Drive folder ID" tooltip={<FieldTooltip field="drive_folder_id" />}>
          <input className="input" value={String(cfg.folder_id ?? '')} onChange={e => setConfig('folder_id', e.target.value)} />
        </Field>
        <Field label="Rename to (optional)">
          <input className="input" value={String(cfg.rename_to ?? '')} onChange={e => setConfig('rename_to', e.target.value)} placeholder="report_{{ current_month }}.xlsx" />
        </Field>
      </div>
    </>
  )
}
