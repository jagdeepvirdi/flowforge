import { useState } from 'react'
import { previewReport } from '../lib/api'
import type { ChartConfig } from '../components/report/ChartPreview'

/** Query preview + chart tooling for a saved report config. Shares a single error banner with
 * the form hook via the passed-in setError. */
export function useReportPreviewTools(id: string | undefined, setError: (msg: string) => void) {
  const [preview, setPreview]         = useState<{ columns: string[]; rows: unknown[][] } | null>(null)
  const [previewing, setPreviewing]   = useState(false)
  const [chartConfig, setChartConfig] = useState<ChartConfig | null>(null)

  const handlePreview = async () => {
    if (!id) { setError('Save the report first to preview'); return }
    setPreviewing(true)
    try {
      const result = await previewReport(id)
      setPreview(result)
      setChartConfig(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed')
    } finally {
      setPreviewing(false)
    }
  }

  /** Start a bar chart from the first column (x) and last column (y); ChartPreview lets the user change them. */
  const handleVisualize = () => {
    if (!preview || preview.columns.length === 0) return
    const { columns } = preview
    setChartConfig({
      type: 'bar',
      x: columns[0],
      y: columns.length > 1 ? columns[columns.length - 1] : columns[0],
      title: '',
      available_columns: columns,
    })
  }

  return {
    preview, previewing, handlePreview,
    chartConfig, setChartConfig, handleVisualize,
  }
}
