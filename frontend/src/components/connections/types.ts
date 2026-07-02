export const DB_COLORS: Record<string, string> = { postgresql: '#3B82F6', oracle: '#EF4444', mysql: '#14B8A6', mssql: '#A855F7', odbc: '#6B7280', redshift: '#DC2626', snowflake: '#38BDF8', bigquery: '#4285F4' }
export const DB_LABELS: Record<string, string> = { postgresql: 'PostgreSQL', oracle: 'Oracle', mysql: 'MySQL', mssql: 'SQL Server', odbc: 'ODBC', redshift: 'Redshift', snowflake: 'Snowflake', bigquery: 'BigQuery' }
export const PROVIDER_LABELS: Record<string, string> = { gmail: 'Gmail', microsoft365: 'Microsoft 365', smtp: 'SMTP', sendgrid: 'SendGrid', ses: 'AWS SES', mailgun: 'Mailgun' }

export type DbForm = {
  name: string; db_type: 'postgresql' | 'oracle' | 'mysql' | 'mssql' | 'odbc' | 'redshift' | 'snowflake' | 'bigquery'
  host: string; port: string; database: string; username: string; password: string
  driver: string        // mssql only
  dsn: string           // odbc only
  connection_string: string  // odbc only
  account: string; warehouse: string; schema_name: string; role: string  // snowflake only
  project_id: string; dataset: string; credentials_json: string          // bigquery only
  is_default: boolean
}

export type MailForm = {
  name: string; provider_type: 'gmail' | 'microsoft365' | 'smtp' | 'sendgrid' | 'ses' | 'mailgun'
  // smtp
  host: string; port: string; username: string; password: string
  use_tls: boolean
  // gmail/m365
  client_id: string; client_secret: string; refresh_token: string; sender: string
  tenant_id: string
  // sendgrid / mailgun / ses
  api_key: string; from_email: string; from_name: string
  // ses
  aws_access_key_id: string; aws_secret_access_key: string; aws_region: string
  // mailgun
  domain: string; region: string
  is_default: boolean
}

export const emptyDb = (): DbForm => ({
  name: '', db_type: 'postgresql', host: 'localhost', port: '5432',
  database: '', username: '', password: '',
  driver: 'ODBC Driver 17 for SQL Server', dsn: '', connection_string: '',
  account: '', warehouse: '', schema_name: '', role: '',
  project_id: '', dataset: '', credentials_json: '',
  is_default: false,
})

export const emptyMail = (): MailForm => ({
  name: '', provider_type: 'smtp', host: '', port: '587',
  username: '', password: '', use_tls: true,
  client_id: '', client_secret: '', refresh_token: '', sender: '', tenant_id: '',
  api_key: '', from_email: '', from_name: '',
  aws_access_key_id: '', aws_secret_access_key: '', aws_region: 'us-east-1',
  domain: '', region: 'us',
  is_default: false,
})

export function defaultDbPort(dbType: string): string {
  if (dbType === 'oracle')   return '1521'
  if (dbType === 'mysql')    return '3306'
  if (dbType === 'mssql')    return '1433'
  if (dbType === 'redshift') return '5439'
  return '5432'
}

export function buildDbConfig(form: DbForm): Record<string, unknown> {
  if (form.db_type === 'odbc') {
    return { dsn: form.dsn, connection_string: form.connection_string }
  }
  if (form.db_type === 'snowflake') {
    return {
      account: form.account, username: form.username, password: form.password,
      warehouse: form.warehouse, database: form.database, schema: form.schema_name, role: form.role,
    }
  }
  if (form.db_type === 'bigquery') {
    return { project_id: form.project_id, dataset: form.dataset, credentials_json: form.credentials_json }
  }
  const cfg: Record<string, unknown> = {
    host: form.host, port: Number(form.port),
    database: form.database, username: form.username, password: form.password,
  }
  if (form.db_type === 'mssql') cfg.driver = form.driver
  return cfg
}

export function buildMailProviderConfig(form: MailForm): Record<string, unknown> {
  if (form.provider_type === 'smtp') {
    return { host: form.host, port: Number(form.port), username: form.username, password: form.password, use_tls: form.use_tls, sender: form.sender }
  }
  if (form.provider_type === 'gmail') {
    return { client_id: form.client_id, client_secret: form.client_secret, refresh_token: form.refresh_token, sender: form.sender }
  }
  if (form.provider_type === 'microsoft365') {
    return { tenant_id: form.tenant_id, client_id: form.client_id, client_secret: form.client_secret, sender: form.sender }
  }
  if (form.provider_type === 'sendgrid') {
    return { api_key: form.api_key, from_email: form.from_email, from_name: form.from_name }
  }
  if (form.provider_type === 'ses') {
    return { aws_access_key_id: form.aws_access_key_id, aws_secret_access_key: form.aws_secret_access_key, aws_region: form.aws_region, from_email: form.from_email, from_name: form.from_name }
  }
  if (form.provider_type === 'mailgun') {
    return { api_key: form.api_key, domain: form.domain, from_email: form.from_email, from_name: form.from_name, region: form.region }
  }
  return {}
}
