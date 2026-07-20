export const STEP_META: Record<string, { label: string; cls: string }> = {
  db_procedure:      { label: 'Proc',   cls: 'tbadge-procedure' },
  db_query:          { label: 'Query',  cls: 'tbadge-query' },
  report:            { label: 'Report', cls: 'tbadge-report' },
  email:             { label: 'Email',  cls: 'tbadge-email' },
  drive_upload:      { label: 'Drive',  cls: 'tbadge-drive' },
  onedrive_upload:   { label: 'OneDrive', cls: 'tbadge-drive' },
  ai_analyze:        { label: 'AI',     cls: 'tbadge-transform' },
  data_load:         { label: 'Load',   cls: 'tbadge-load' },
  bulk_load:         { label: 'Bulk',   cls: 'tbadge-bulk' },
  sftp_transfer:     { label: 'SFTP',   cls: 'tbadge-export' },
  ssh_command:       { label: 'SSH',    cls: 'tbadge-transform' },
  db_health_check:   { label: 'Health', cls: 'tbadge-procedure' },
  data_report:       { label: 'Report', cls: 'tbadge-report' },
  ssh_health_check:  { label: 'Health', cls: 'tbadge-transform' },
  notification:      { label: 'Notify', cls: 'tbadge-email' },
  s3_upload:         { label: 'S3',     cls: 'tbadge-drive' },
  azure_blob_upload: { label: 'Azure',  cls: 'tbadge-drive' },
}

export function stepMeta(stepType: string): { label: string; cls: string } {
  return STEP_META[stepType] ?? { label: stepType, cls: 'tbadge-query' }
}
