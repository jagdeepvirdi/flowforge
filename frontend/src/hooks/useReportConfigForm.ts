import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { getReportConfig, createReportConfig, updateReportConfig, getDbConnections, getSetupStatus } from '../lib/api'
import type { ColumnFormatRule } from '../lib/types'
import { useProjectStore } from '../lib/store'

const schema = z.object({
  name:      z.string().min(1, 'Name is required'),
  desc:      z.string(),
  connId:    z.string(),
  query:     z.string().min(1, 'SQL query is required'),
  format:    z.enum(['excel', 'csv', 'pdf', 'json']),
  filename:  z.string().min(1),
  sheetName: z.string(),
  title:     z.string(),
})
export type ReportFormValues = z.infer<typeof schema>

/** Report config CRUD: loads the existing config (if editing), db connections, AI availability,
 * the react-hook-form instance, and the save handler. */
export function useReportConfigForm() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { activeProjectId } = useProjectStore()

  const { data: existing, isLoading } = useQuery({ queryKey: ['report-config', id], queryFn: () => getReportConfig(id!), enabled: !isNew })
  const { data: dbConns = [] } = useQuery({ queryKey: ['db-connections'], queryFn: getDbConnections })
  const { data: setupStatus } = useQuery({ queryKey: ['setup-status'], queryFn: getSetupStatus, staleTime: 60_000 })
  const aiEnabled = setupStatus?.ai?.enabled ?? true

  const { register, handleSubmit, watch, getValues, setValue, reset, formState: { errors, isSubmitting } } = useForm<ReportFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '', desc: '', connId: '', query: '',
      format: 'excel',
      filename: 'report_{{ current_month }}.xlsx',
      sheetName: 'Sheet1', title: '',
    },
  })

  const [columnFormatting, setColumnFormatting] = useState<ColumnFormatRule[]>([])
  const [error, setError] = useState('')

  const format = watch('format')
  const name   = watch('name')

  useEffect(() => {
    if (!existing) return
    reset({
      name:      existing.name,
      desc:      existing.description ?? '',
      connId:    existing.connection_id ?? '',
      query:     existing.query,
      format:    existing.format,
      filename:  existing.output_filename,
      sheetName: existing.sheet_name ?? 'Sheet1',
      title:     existing.title ?? '',
    })
    setColumnFormatting(existing.column_formatting ?? [])
  }, [existing, reset])

  const onSubmit = async (values: ReportFormValues) => {
    setError('')
    try {
      const payload = {
        name: values.name, description: values.desc,
        connection_id: values.connId || null,
        query: values.query, format: values.format,
        output_filename: values.filename,
        sheet_name: values.sheetName, title: values.title,
        column_formatting: columnFormatting,
        ...(isNew && activeProjectId ? { project_id: activeProjectId } : {}),
      }
      isNew ? await createReportConfig(payload) : await updateReportConfig(id!, payload)
      qc.invalidateQueries({ queryKey: ['report-configs'] })
      navigate('/reports')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    }
  }

  return {
    id, isNew, isLoading, dbConns, aiEnabled,
    register, handleSubmit, watch, getValues, setValue, errors, isSubmitting,
    columnFormatting, setColumnFormatting,
    error, setError,
    format, name,
    onSubmit,
  }
}
