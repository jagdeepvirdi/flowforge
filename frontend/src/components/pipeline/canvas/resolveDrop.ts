export interface DropWaveColumn {
  /** The group value all items in this column share (null = an ungrouped single-step wave). */
  parallel_group: string | null
  /** Rendered x-center of the column, in the same coordinate space as dropPos. */
  xCenter: number
  /** Items in this column, in step_order order, with their rendered y-centers. */
  items: { id: string; yCenter: number }[]
}

export interface DropResolution {
  /**
   * Index into the steps array with the dragged step already removed (i.e.
   * the same convention `assignParallelGroup`/`reorderSteps` expect for
   * `targetIndex`/`to`).
   */
  targetIndex: number
  parallel_group: string | null
}

/**
 * Pure coordinate math for canvas drag-drop: given where a node was
 * dropped and the columns as currently rendered (wave layout with the
 * dragged node excluded), resolve which column it landed in and at what
 * position. No react-flow/DOM dependency — testable with hand-built
 * columns.
 */
export function resolveDropTarget(
  dropPos: { x: number; y: number },
  columns: DropWaveColumn[],
): DropResolution {
  if (columns.length === 0) return { targetIndex: 0, parallel_group: null }

  let nearestColIndex = 0
  let bestDist = Math.abs(dropPos.x - columns[0].xCenter)
  for (let i = 1; i < columns.length; i++) {
    const d = Math.abs(dropPos.x - columns[i].xCenter)
    if (d < bestDist) {
      bestDist = d
      nearestColIndex = i
    }
  }
  const nearestCol = columns[nearestColIndex]

  const withinColIndex = nearestCol.items.filter(it => it.yCenter < dropPos.y).length

  let targetIndex = withinColIndex
  for (let i = 0; i < nearestColIndex; i++) targetIndex += columns[i].items.length

  return { targetIndex, parallel_group: nearestCol.parallel_group }
}
