import { useMemo, useState, useCallback } from 'react'
import {
  ReactFlow, ReactFlowProvider, Background, Controls, BackgroundVariant,
  type Node, type Edge, type NodeMouseHandler, type OnNodeDrag,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { PipelineStep } from '../../../lib/types'
import { computeWaves } from '../../../lib/pipelineWaves'
import { assignParallelGroup } from '../../../lib/pipelineReorder'
import { layoutWaves, buildWaveEdges, CANVAS_NODE_WIDTH, CANVAS_NODE_HEIGHT } from './layout'
import { resolveDropTarget, type DropWaveColumn } from './resolveDrop'
import StepNode, { type StepFlowNode } from './StepNode'
import StepPanel from './StepPanel'

const nodeTypes = { step: StepNode }

type Props = Readonly<{
  steps: PipelineStep[]
  onStepsChange: (steps: PipelineStep[]) => void
  onDuplicate: (id: string) => void
  onDelete: (id: string) => void
  dbConnections: { id: string; name: string }[]
  reportConfigs: { id: string; name: string; output_filename: string }[]
  emailConfigs: { id: string; name: string }[]
  bulkLoadConfigs: { id: string; name: string; source_directory: string; target_table: string }[]
}>

function CanvasInner({
  steps, onStepsChange, onDuplicate, onDelete,
  dbConnections, reportConfigs, emailConfigs, bulkLoadConfigs,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const waves = useMemo(() => computeWaves(steps), [steps])
  const positions = useMemo(() => layoutWaves(waves), [waves])

  const nodes: StepFlowNode[] = useMemo(() => steps.map(step => ({
    id: step.id,
    type: 'step',
    position: positions.get(step.id) ?? { x: 0, y: 0 },
    data: { step, onDuplicate, onDelete },
    selected: step.id === selectedId,
    draggable: true,
  })), [steps, positions, selectedId, onDuplicate, onDelete])

  const edges: Edge[] = useMemo(() => buildWaveEdges(waves).map(e => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: 'smoothstep',
    animated: false,
    style: { stroke: 'var(--border-strong)', strokeWidth: 1.5 },
  })), [waves])

  const handleNodeClick: NodeMouseHandler = useCallback((_, node: Node) => {
    setSelectedId(node.id)
  }, [])

  const handlePaneClick = useCallback(() => setSelectedId(null), [])

  const handleNodeDragStop: OnNodeDrag = useCallback((_, node) => {
    const draggedId = node.id
    const otherSteps = steps.filter(s => s.id !== draggedId)
    const otherWaves = computeWaves(otherSteps)
    const otherPositions = layoutWaves(otherWaves)

    const columns: DropWaveColumn[] = otherWaves.map(wave => {
      const xs = wave.map(s => (otherPositions.get(s.id)?.x ?? 0) + CANVAS_NODE_WIDTH / 2)
      const xCenter = xs.reduce((a, b) => a + b, 0) / (xs.length || 1)
      return {
        parallel_group: wave[0]?.parallel_group ?? null,
        xCenter,
        items: wave.map(s => ({ id: s.id, yCenter: (otherPositions.get(s.id)?.y ?? 0) + CANVAS_NODE_HEIGHT / 2 })),
      }
    })

    const dropPos = { x: node.position.x + CANVAS_NODE_WIDTH / 2, y: node.position.y + CANVAS_NODE_HEIGHT / 2 }
    const { targetIndex, parallel_group } = resolveDropTarget(dropPos, columns)

    // assignParallelGroup handles both cases uniformly: reordering the
    // dragged step to `targetIndex` (an index into `steps` with the dragged
    // step removed) and setting its parallel_group — which is a no-op field
    // change when the resolved group equals the step's current group, i.e.
    // a pure reorder within/around the same column.
    onStepsChange(assignParallelGroup(steps, draggedId, parallel_group, targetIndex))
  }, [steps, onStepsChange])

  const selectedStep = steps.find(s => s.id === selectedId) ?? null

  const handlePanelChange = useCallback((id: string, updates: Partial<PipelineStep>) => {
    onStepsChange(steps.map(s => s.id === id ? { ...s, ...updates } : s))
  }, [steps, onStepsChange])

  const handlePanelDelete = useCallback((id: string) => {
    onDelete(id)
    setSelectedId(null)
  }, [onDelete])

  if (steps.length === 0) {
    return (
      <div className="card ff-empty border-dashed py-6">
        <p className="msg">Add steps using the buttons above.</p>
      </div>
    )
  }

  return (
    <div className="ff-canvas-wrap rounded-[10px] border border-border overflow-hidden" style={{ height: 480 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        onNodeDragStop={handleNodeDragStop}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>

      <StepPanel
        step={selectedStep}
        onClose={() => setSelectedId(null)}
        onChange={handlePanelChange}
        onDuplicate={onDuplicate}
        onDelete={handlePanelDelete}
        allSteps={steps}
        dbConnections={dbConnections}
        reportConfigs={reportConfigs}
        emailConfigs={emailConfigs}
        bulkLoadConfigs={bulkLoadConfigs}
      />
    </div>
  )
}

export default function PipelineCanvas(props: Props) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  )
}
