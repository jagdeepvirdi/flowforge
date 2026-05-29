import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, Layers } from 'lucide-react'
import { getProjects, createProject, updateProject, deleteProject } from '../lib/api'
import { useProjectStore } from '../lib/store'
import type { Project } from '../lib/types'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'

const PROJECT_COLORS = [
  '#F97316', '#3B82F6', '#22C55E', '#A855F7',
  '#EC4899', '#EAB308', '#14B8A6', '#F43F5E',
]

function ColorPicker({ value, onChange }: { value: string; onChange: (c: string) => void }) {
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {PROJECT_COLORS.map(c => (
        <button
          key={c}
          type="button"
          onClick={() => onChange(c)}
          style={{
            width: 22,
            height: 22,
            borderRadius: '50%',
            background: c,
            border: value === c ? '2px solid #fff' : '2px solid transparent',
            cursor: 'pointer',
            outline: value === c ? `2px solid ${c}` : 'none',
            outlineOffset: 1,
          }}
        />
      ))}
    </div>
  )
}

interface ProjectFormData {
  name: string
  description: string
  color: string
}

function ProjectModal({
  project,
  onClose,
}: {
  project?: Project
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [form, setForm] = useState<ProjectFormData>({
    name: project?.name ?? '',
    description: project?.description ?? '',
    color: project?.color ?? PROJECT_COLORS[0],
  })
  const [error, setError] = useState('')

  const { mutate: save, isPending } = useMutation({
    mutationFn: () =>
      project
        ? updateProject(project.id, form)
        : createProject(form),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['projects'] })
      onClose()
    },
    onError: (e: Error) => setError(e.message),
  })

  const saveButtonLabel = (() => {
    if (isPending) return 'Saving…'
    return project ? 'Save' : 'Create'
  })()

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200,
    }}>
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12,
        padding: 24, width: 400, maxWidth: '90vw',
      }}>
        <h2 style={{ margin: '0 0 20px', fontSize: 16, fontWeight: 600 }}>
          {project ? 'Edit Project' : 'New Project'}
        </h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label className="label" htmlFor="project-name">Name</label>
            <input
              id="project-name"
              className="input"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Finance Reports"
              autoFocus
            />
          </div>
          <div>
            <label className="label" htmlFor="project-description">Description</label>
            <input
              id="project-description"
              className="input"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Optional description"
            />
          </div>
          <div>
            <label className="label" style={{ marginBottom: 8, display: 'block' }}>Color</label>
            <ColorPicker value={form.color} onChange={c => setForm(f => ({ ...f, color: c }))} />
          </div>
        </div>

        {error && (
          <div style={{ marginTop: 12, padding: '8px 12px', background: 'rgba(239,68,68,0.1)', borderRadius: 6, color: 'var(--failure-text)', fontSize: 12.5 }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 20 }}>
          <button className="btn btn-sm btn-ghost" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-sm btn-primary"
            onClick={() => save()}
            disabled={!form.name.trim() || isPending}
          >
            {saveButtonLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

function ProjectCard({ project, onEdit }: { project: Project; onEdit: (p: Project) => void }) {
  const qc = useQueryClient()
  const { activeProjectId, setActiveProjectId } = useProjectStore()

  const { mutate: remove } = useMutation({
    mutationFn: () => deleteProject(project.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      if (activeProjectId === project.id) setActiveProjectId(null)
    },
  })

  const counts = project.resource_counts
  const total = counts ? counts.pipelines + counts.reports + counts.emails + counts.recipients : 0
  const isActive = activeProjectId === project.id

  return (
    <div
      className="card"
      role="button"
      tabIndex={0}
      aria-pressed={isActive}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        borderColor: isActive ? project.color || 'var(--accent)' : undefined,
        cursor: 'pointer',
      }}
      onClick={() => setActiveProjectId(isActive ? null : project.id)}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setActiveProjectId(isActive ? null : project.id) }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            width: 10, height: 10, borderRadius: '50%',
            background: project.color || 'var(--accent)', flexShrink: 0,
          }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text)' }}>{project.name}</div>
            {project.description && (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{project.description}</div>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {!project.is_default && (
            <>
              <button
                className="btn btn-sm btn-ghost btn-icon"
                onClick={e => { e.stopPropagation(); onEdit(project) }}
                title="Edit"
              >
                <Pencil size={12} />
              </button>
              <button
                className="btn btn-sm btn-ghost btn-icon"
                style={{ color: 'var(--text-muted)' }}
                onMouseEnter={e => (e.currentTarget.style.color = 'var(--failure-text)')}
                onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
                onClick={e => {
                  e.stopPropagation()
                  if (total > 0) {
                    alert(`Cannot delete "${project.name}" — it has ${total} resource(s). Move or delete them first.`)
                    return
                  }
                  globalThis.confirm(`Delete project "${project.name}"?`) && remove()
                }}
                title="Delete"
              >
                <Trash2 size={12} />
              </button>
            </>
          )}
        </div>
      </div>

      {counts && (
        <div style={{ display: 'flex', gap: 16 }}>
          {[
            ['Pipelines', counts.pipelines],
            ['Reports', counts.reports],
            ['Emails', counts.emails],
            ['Recipients', counts.recipients],
          ].map(([label, n]) => (
            <div key={String(label)}>
              <div style={{ fontSize: 16, fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: 'var(--text)' }}>{n}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      {project.is_default && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
          Default project — all unassigned resources land here
        </div>
      )}

      {isActive && (
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          fontSize: 11, color: project.color || 'var(--accent)', fontWeight: 600,
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: project.color || 'var(--accent)' }} />{' '}
          Active filter
        </div>
      )}
    </div>
  )
}

export default function Projects() {
  const [modalProject, setModalProject] = useState<Project | undefined>(undefined)
  const [showModal, setShowModal] = useState(false)

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  })

  function openCreate() {
    setModalProject(undefined)
    setShowModal(true)
  }

  function openEdit(p: Project) {
    setModalProject(p)
    setShowModal(true)
  }

  if (isLoading) return (
    <>
      <TopBar crumbs={['Workspace', 'Projects']} />
      <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div>
    </>
  )

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Projects']}
        actions={
          <button className="btn btn-primary btn-sm" onClick={openCreate}><Plus size={13} />{' '}New Project</button>
        }
      />

      <div className="scroll">
        <div className="page-h">
          <div>
            <h1>Projects</h1>
            <p>Organize your pipelines, reports, and email templates by project.</p>
          </div>
        </div>

        {projects.length === 0 ? (
          <div className="card ff-empty">
            <Layers size={32} style={{ color: 'var(--text-muted)', marginBottom: 8 }} />
            <p className="msg">No projects yet.</p>
            <button className="btn btn-primary" onClick={openCreate}>Create your first project</button>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
            {projects.map(p => (
              <ProjectCard key={p.id} project={p} onEdit={openEdit} />
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <ProjectModal project={modalProject} onClose={() => setShowModal(false)} />
      )}
    </>
  )
}
