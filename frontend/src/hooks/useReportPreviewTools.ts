import { useState } from 'react'
import type { UseFormGetValues, UseFormSetValue } from 'react-hook-form'
import { previewReport, generateChartConfig, aiQuery, profileData } from '../lib/api'
import type { ChartConfig } from '../components/report/ChartPreview'
import type { ReportFormValues } from './useReportConfigForm'

/** Query preview + AI-assisted tooling (explain/optimize/visualize/profile) for a saved report
 * config. Reads/writes the SQL query field via the report-form's getValues/setValue, and shares
 * a single error banner with the form hook via the passed-in setError. */
export function useReportPreviewTools(
  id: string | undefined,
  getValues: UseFormGetValues<ReportFormValues>,
  setValue: UseFormSetValue<ReportFormValues>,
  setError: (msg: string) => void,
) {
  const [preview, setPreview]           = useState<{ columns: string[]; rows: unknown[][] } | null>(null)
  const [previewing, setPreviewing]     = useState(false)
  const [chartConfig, setChartConfig]   = useState<ChartConfig | null>(null)
  const [visualizing, setVisualizing]   = useState(false)
  const [explanation, setExplanation]   = useState<string | null>(null)
  const [explaining, setExplaining]     = useState(false)
  const [optimization, setOptimization] = useState<{ original: string; suggested: string } | null>(null)
  const [optimizing, setOptimizing]     = useState(false)
  const [profileConsented, setProfileConsented] = useState(false)
  const [profilePending, setProfilePending]     = useState(false)
  const [profileResult, setProfileResult]       = useState<string | null>(null)
  const [profiling, setProfiling]       = useState(false)

  const handlePreview = async () => {
    if (!id) { setError('Save the report first to preview'); return }
    setPreviewing(true)
    try {
      const result = await previewReport(id)
      setPreview(result)
      setChartConfig(null)
      setExplanation(null)
      setOptimization(null)
      setProfileResult(null)
      setProfilePending(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed')
    } finally {
      setPreviewing(false)
    }
  }

  const handleExplain = async () => {
    const sql = getValues('query').trim()
    if (!sql) return
    setExplaining(true)
    setError('')
    try {
      const { result } = await aiQuery({ task: 'explain', sql })
      setExplanation(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Explanation failed')
    } finally {
      setExplaining(false)
    }
  }

  const handleOptimize = async () => {
    const sql = getValues('query').trim()
    if (!sql) return
    setOptimizing(true)
    setError('')
    try {
      const { result } = await aiQuery({ task: 'optimize', sql })
      setOptimization({ original: sql, suggested: result })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Optimization failed')
    } finally {
      setOptimizing(false)
    }
  }

  const doProfile = async () => {
    if (!preview) return
    setProfiling(true)
    setProfileResult(null)
    setError('')
    try {
      const { result } = await profileData({ columns: preview.columns, rows: preview.rows })
      setProfileResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Profiling failed')
    } finally {
      setProfiling(false)
    }
  }

  const handleSummarise = () => {
    if (!preview) return
    if (profileConsented) {
      doProfile()
    } else {
      setProfilePending(true)
    }
  }

  const handleProfileProceed = () => {
    setProfileConsented(true)
    setProfilePending(false)
    doProfile()
  }

  const acceptOptimization = () => {
    if (!optimization) return
    setValue('query', optimization.suggested)
    setOptimization(null)
    setExplanation(null)
  }

  const handleVisualize = async () => {
    if (!preview) return
    setVisualizing(true)
    setError('')
    try {
      const cfg = await generateChartConfig({ columns: preview.columns, rows: preview.rows })
      setChartConfig(cfg)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Visualization failed')
    } finally {
      setVisualizing(false)
    }
  }

  return {
    preview, previewing, handlePreview,
    chartConfig, setChartConfig, visualizing, handleVisualize,
    explanation, setExplanation, explaining, handleExplain,
    optimization, setOptimization, optimizing, handleOptimize, acceptOptimization,
    profileConsented, profilePending, setProfilePending, profileResult, setProfileResult, profiling,
    handleSummarise, handleProfileProceed,
  }
}
