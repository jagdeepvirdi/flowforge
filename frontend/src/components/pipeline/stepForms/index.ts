import type { ComponentType } from 'react'
import AzureBlobUploadForm from './AzureBlobUploadForm'
import BulkLoadForm from './BulkLoadForm'
import DataLoadForm from './DataLoadForm'
import DbProcedureForm from './DbProcedureForm'
import DbQueryForm from './DbQueryForm'
import DriveUploadForm from './DriveUploadForm'
import EmailForm from './EmailForm'
import NotificationForm from './NotificationForm'
import ReportForm from './ReportForm'
import S3UploadForm from './S3UploadForm'
import SftpTransferForm from './SftpTransferForm'
import type { StepFormProps } from './types'

export type { StepFormProps } from './types'

// Step types with a dedicated config form here. Anything else (plugin types, or
// built-ins without a form yet) falls back to the generic JSON config editor in StepEditor.
export const STEP_FORMS: Record<string, ComponentType<StepFormProps>> = {
  db_procedure: DbProcedureForm,
  db_query: DbQueryForm,
  report: ReportForm,
  email: EmailForm,
  drive_upload: DriveUploadForm,
  data_load: DataLoadForm,
  bulk_load: BulkLoadForm,
  notification: NotificationForm,
  s3_upload: S3UploadForm,
  azure_blob_upload: AzureBlobUploadForm,
  sftp_transfer: SftpTransferForm,
}
