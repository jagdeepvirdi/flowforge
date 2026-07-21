import { useMemo, useState, useCallback } from 'react'
import {
  ReactFlow, ReactFlowProvider, Background, Controls, BackgroundVariant,
  type Node, type Edge, type NodeMouseHandler, type OnNodeDrag, type OnConnect, type OnEdgesDelete,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { PipelineStep, StepDep } from '../../../lib/types'
import { addStepDep, removeStepDep } from '../../../lib/api'
import { computeWaves } from '../../../lib/pipelineWaves'
import { assignParallelGroup } from '../../../lib/pipelineReorder'
import { layoutWaves, layoutRealEdges, buildWaveEdges, CANVAS_NODE_WIDTH, CANVAS_NODE_HEIGHT } from './layout'
import { resolveDropTarget, type DropWaveColumn } from './resolveDrop'
import { toRealFlowEdges, canConnectSteps } from './stepDeps'
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
  /** Undefined for an unsaved (`isNew`) pipeline — step-dependency edges require a real pipeline_id. */
  pipelineId?: string
  /** Real, persisted step-dependency edges for this pipeline (Phase 14 Option B). */
  stepDeps?: StepDep[]
  /** Called after a successful add/remove so the parent can refetch. */
  onStepDepsChanged?: () => void
}>

function CanvasInner({
  steps, onStepsChange, onDuplicate, onDelete,
  dbConnections, reportConfigs, emailConfigs, bulkLoadConfigs,
  pipelineId, stepDeps = [], onStepDepsChanged,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [connectError, setConnectError] = useState('')

  // Mirrors the backend's dual-path gate (runner.run_pipeline / StepDependency.exists_for_pipeline):
  // once a pipeline has any real step-dependency edges, the canvas uses them exclusively —
  // synthetic wave-to-wave edges and step_order/parallel_group-driven drag-reorder both stop
  // applying, since execution order now comes from the graph, not the wave model.
  const hasRealEdges = stepDeps.length > 0

  const waves = useMemo(() => computeWaves(steps), [steps])
  const realEdgePairs = useMemo(
    () => stepDeps.map(d => ({ source: d.upstream_step_id, target: d.downstream_step_id })),
    [stepDeps],
  )
  const positions = useMemo(
    () => hasRealEdges ? layoutRealEdges(steps, realEdgePairs) : layoutWaves(waves),
    [hasRealEdges, steps, realEdgePairs, waves],
  )

  const nodes: StepFlowNode[] = useMemo(() => steps.map(step => ({
    id: step.id,
    type: 'step',
    position: positions.get(step.id) ?? { x: 0, y: 0 },
    data: { step, onDuplicate, onDelete },
    selected: step.id === selectedId,
    draggable: true,
  })), [steps, positions, selectedId, onDuplicate, onDelete])

  const edges: Edge[] = useMemo(() => {
    if (hasRealEdges) return toRealFlowEdges(stepDeps)
    return buildWaveEdges(waves).map(e => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: 'smoothstep',
      animated: false,
      deletable: false,
      style: { stroke: 'var(--border-strong)', strokeWidth: 1.5 },
    }))
  }, [hasRealEdges, stepDeps, waves])

  const handleConnect: OnConnect = useCallback((connection) => {
    const { source, target } = connection
    const guard = canConnectSteps({ pipelineId, source, target })
    if (!guard.allowed) {
      setConnectError(guard.reason ?? 'Cannot connect these steps.')
      return
    }
    addStepDep(pipelineId!, source, target)
      .then(() => { setConnectError(''); onStepDepsChanged?.() })
      .catch((err: Error) => setConnectError(err.message))
  }, [pipelineId, onStepDepsChanged])

  const handleEdgesDelete: OnEdgesDelete = useCallback((deleted) => {
    if (!pipelineId) return
    for (const edge of deleted) {
      const depId = (edge.data as { depId?: string } | undefined)?.depId
      if (!depId) continue
      removeStepDep(pipelineId, depId)
        .then(() => onStepDepsChanged?.())
        .catch((err: Error) => setConnectError(err.message))
    }
  }, [pipelineId, onStepDepsChanged])

  const handleNodeClick: NodeMouseHandler = useCallback((_, node: Node) => {
    setSelectedId(node.id)
  }, [])

  const handlePaneClick = useCallback(() => setSelectedId(null), [])

  const handleNodeDragStop: OnNodeDrag = useCallback((_, node) => {
    // Once a pipeline is in DAG mode, step_order/parallel_group no longer drive execution
    // order (the graph does) — dragging a node just repositions it for this render; the next
    // render snaps it back to the dagre-computed position since x/y are never persisted.
    if (hasRealEdges) return

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
  }, [hasRealEdges, steps, onStepsChange])

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
    <div className="ff-canvas-wrap relative rounded-[10px] border border-border overflow-hidden" style={{ height: 480 }}>
      {connectError && (
        <div
          className="absolute top-2 left-2 right-2 z-10 p-[6px_10px] bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.25)] rounded-[6px] text-[11.5px] text-[var(--failure-text)] flex items-center justify-between gap-2"
          data-testid="canvas-connect-error"
        >
          <span>{connectError}</span>
          <button className="bg-transparent border-none cursor-pointer text-[var(--failure-text)] shrink-0" onClick={() => setConnectError('')}>×</button>
        </div>
      )}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        onNodeDragStop={handleNodeDragStop}
        onConnect={handleConnect}
        onEdgesDelete={handleEdgesDelete}
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
