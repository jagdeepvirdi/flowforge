import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getRetentionSettings, updateRetentionSettings } from '../lib/api'

/** Data-retention form: fetches current settings, syncs them into editable form state,
 * validates, and saves (or resets a single field back to its env-var default). */
export function useRetentionSettings() {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['retention-settings'],
    queryFn: getRetentionSettings,
  })

  const [form, setForm] = useState({ run: '', audit: '', outputTtl: '' })
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState(false)

  // Sync fetched data into local editable form state, adjusted during render
  // (React's documented pattern for this) rather than in an effect.
  const [prevData, setPrevData] = useState(data)
  if (data !== prevData) {
    setPrevData(data)
    if (data) {
      setForm({
        run:       String(data.run_retention_days),
        audit:     String(data.audit_retention_days),
        outputTtl: String(data.output_ttl_days),
      })
    }
  }

  const mut = useMutation({
    mutationFn: updateRetentionSettings,
    onSuccess: () => {
      setSuccess(true)
      setError('')
      qc.invalidateQueries({ queryKey: ['retention-settings'] })
    },
    onError: (e: Error) => { setError(e.message); setSuccess(false) },
  })

  const outputTtlNum = Number(form.outputTtl)
  const outputTtlInvalid = form.outputTtl.trim() === '' || !Number.isInteger(outputTtlNum) || outputTtlNum < 1

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess(false)
    if (outputTtlInvalid) {
      setError('Output file TTL must be at least 1 day — 0 would delete every generated report immediately.')
      return
    }
    mut.mutate({
      run_retention_days: Number(form.run),
      audit_retention_days: Number(form.audit),
      output_ttl_days: outputTtlNum,
    })
  }

  function resetToDefault(field: 'run_retention_days' | 'audit_retention_days' | 'output_ttl_days') {
    setError('')
    setSuccess(false)
    mut.mutate({ [field]: null })
  }

  return {
    data, isLoading, form, setForm, error, success, mut,
    outputTtlInvalid, handleSubmit, resetToDefault,
  }
}
