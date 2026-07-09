import { describe, it, expect } from 'vitest'
import { resolveDropTarget, type DropWaveColumn } from '../components/pipeline/canvas/resolveDrop'

describe('resolveDropTarget', () => {
  const columns: DropWaveColumn[] = [
    { parallel_group: null, xCenter: 0, items: [{ id: 'a', yCenter: 0 }] },
    { parallel_group: 'g1', xCenter: 300, items: [{ id: 'b', yCenter: 0 }, { id: 'c', yCenter: 100 }] },
    { parallel_group: null, xCenter: 600, items: [{ id: 'd', yCenter: 0 }] },
  ]

  it('picks the nearest column by x-center', () => {
    expect(resolveDropTarget({ x: 10, y: 0 }, columns).parallel_group).toBeNull()
    expect(resolveDropTarget({ x: 290, y: 0 }, columns).parallel_group).toBe('g1')
    expect(resolveDropTarget({ x: 610, y: 0 }, columns).parallel_group).toBeNull()
  })

  it('inserts before an item when dropped above its y-center', () => {
    // Dropping at y=-10 in the g1 column (above b's yCenter=0) should target
    // index 1 (right after column 0's single item, before b).
    const res = resolveDropTarget({ x: 300, y: -10 }, columns)
    expect(res.targetIndex).toBe(1)
  })

  it('inserts after an item when dropped below its y-center', () => {
    // Dropping at y=50 (below b's yCenter=0, above c's yCenter=100) lands after b.
    const res = resolveDropTarget({ x: 300, y: 50 }, columns)
    expect(res.targetIndex).toBe(2)
  })

  it('inserts at the end of a column when dropped below all its items', () => {
    const res = resolveDropTarget({ x: 300, y: 200 }, columns)
    expect(res.targetIndex).toBe(3)
  })

  it('computes absolute index by summing preceding columns sizes', () => {
    // Dropping into the third column (single item at x=600) after its item.
    const res = resolveDropTarget({ x: 600, y: 50 }, columns)
    // 1 (col0) + 2 (col1) + 1 (after col2's item) = 4
    expect(res.targetIndex).toBe(4)
    expect(res.parallel_group).toBeNull()
  })

  it('returns a safe default for no columns', () => {
    expect(resolveDropTarget({ x: 0, y: 0 }, [])).toEqual({ targetIndex: 0, parallel_group: null })
  })
})
