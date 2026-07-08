import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, Layers, Users, X } from 'lucide-react'
import {
  getProjects, createProject, updateProject, deleteProject,
  getProjectMembers, addProjectMember, removeProjectMember, getUsers,
} from '../lib/api'
import { useProjectStore } from '../lib/store'
import { useCurrentUser } from '../lib/auth'
import type { Project } from '../lib/types'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'

const PROJECT_COLORS = [
  '#F97316', '#3B82F6', '#22C55E', '#A855F7',
  '#EC4899', '#EAB308', '#14B8A6', '#F43F5E',
]

function ColorPicker({ value, onChange }: { value: string; onChange: (c: string) => void }) {
  return (
    <div className="flex gap-1.5 flex-wrap">
      {PROJECT_COLORS.map(c => (
        <button
          key={c}
          type="button"
          onClick={() => onChange(c)}
          className="w-[22px] h-[22px] rounded-full cursor-pointer"
          style={{
            background: c,
            border: value === c ? '2px solid #fff' : '2px solid transparent',
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
    <div className="fixed inset-0 bg-[rgba(0,0,0,0.6)] flex items-center justify-center z-[200]">
      <div className="bg-surface border border-border rounded-xl p-6 w-[400px] max-w-[90vw]">
        <h2 className="m-0 mb-5 text-base font-semibold">
          {project ? 'Edit Project' : 'New Project'}
        </h2>

        <div className="flex flex-col gap-3.5">
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
            <div className="label mb-2">Color</div>
            <ColorPicker value={form.color} onChange={c => setForm(f => ({ ...f, color: c }))} />
          </div>
        </div>

        {error && (
          <div className="mt-3 py-2 px-3 bg-[rgba(239,68,68,0.1)] rounded-r-sm text-failure-text text-[12.5px]">
            {error}
          </div>
        )}

        <div className="flex gap-2 justify-end mt-5">
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

function MembersModal({ project, onClose }: { project: Project; onClose: () => void }) {
  const qc = useQueryClient()
  const currentUser = useCurrentUser()
  const isAdmin = currentUser?.role === 'admin'
  const [selectedUserId, setSelectedUserId] = useState('')
  const [error, setError] = useState('')

  const { data: members = [], isLoading } = useQuery({
    queryKey: ['project-members', project.id],
    queryFn: () => getProjectMembers(project.id),
  })

  const { data: allUsers = [] } = useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
    enabled: isAdmin,
  })

  const { mutate: addMember, isPending: adding } = useMutation({
    mutationFn: () => addProjectMember(project.id, selectedUserId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project-members', project.id] })
      setSelectedUserId('')
      setError('')
    },
    onError: (e: Error) => setError(e.message),
  })

  const { mutate: removeMember } = useMutation({
    mutationFn: (userId: string) => removeProjectMember(project.id, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project-members', project.id] }),
  })

  const memberIds = new Set(members.map(m => m.user_id))
  const addableUsers = allUsers.filter(u => u.role !== 'admin' && !memberIds.has(u.id))

  return (
    <div className="fixed inset-0 bg-[rgba(0,0,0,0.6)] flex items-center justify-center z-[200]">
      <div className="bg-surface border border-border rounded-xl p-6 w-[420px] max-w-[90vw]">
        <div className="flex items-center justify-between mb-4">
          <h2 className="m-0 text-base font-semibold">Members — {project.name}</h2>
          <button className="btn btn-sm btn-ghost btn-icon" onClick={onClose}><X size={14} /></button>
        </div>

        {isLoading ? (
          <div className="flex justify-center p-3"><Spinner /></div>
        ) : (
          <div className="flex flex-col gap-1 max-h-[280px] overflow-y-auto">
            {members.length === 0 && (
              <p className="text-[12.5px] text-text-muted">No members yet — admins can still access every project.</p>
            )}
            {members.map(m => (
              <div key={m.id} className="flex items-center justify-between py-1.5 px-2 rounded-r-sm bg-surface2">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] text-text-primary">{m.username}</span>
                  <span className="text-[10px] text-text-muted uppercase tracking-[0.03em]">{m.role}</span>
                </div>
                {isAdmin && (
                  <button
                    className="btn btn-sm btn-ghost btn-icon"
                    onClick={() => removeMember(m.user_id)}
                    title="Remove member"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {isAdmin && (
          <div className="flex gap-2 mt-4">
            <select
              className="input flex-1"
              value={selectedUserId}
              onChange={e => setSelectedUserId(e.target.value)}
            >
              <option value="">Select a user…</option>
              {addableUsers.map(u => (
                <option key={u.id} value={u.id}>{u.username} ({u.role})</option>
              ))}
            </select>
            <button
              className="btn btn-sm btn-primary"
              disabled={!selectedUserId || adding}
              onClick={() => addMember()}
            >
              Add
            </button>
          </div>
        )}

        {error && (
          <div className="mt-3 py-2 px-3 bg-[rgba(239,68,68,0.1)] rounded-r-sm text-failure-text text-[12.5px]">
            {error}
          </div>
        )}

        <div className="flex justify-end mt-5">
          <button className="btn btn-sm btn-ghost" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}

function ProjectCard({ project, onEdit, onManageMembers }: { project: Project; onEdit: (p: Project) => void; onManageMembers: (p: Project) => void }) {
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
      className="card flex flex-col gap-3 cursor-pointer"
      role="button"
      tabIndex={0}
      aria-pressed={isActive}
      style={{ borderColor: isActive ? project.color || 'var(--accent)' : undefined }}
      onClick={() => setActiveProjectId(isActive ? null : project.id)}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setActiveProjectId(isActive ? null : project.id) }}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: project.color || 'var(--accent)' }} />
          <div>
            <div className="font-semibold text-sm text-text-primary">{project.name}</div>
            {project.description && (
              <div className="text-xs text-text-muted mt-0.5">{project.description}</div>
            )}
          </div>
        </div>
        <div className="flex gap-1">
          <button
            className="btn btn-sm btn-ghost btn-icon"
            onClick={e => { e.stopPropagation(); onManageMembers(project) }}
            title="Manage members"
          >
            <Users size={12} />
          </button>
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
                className="btn btn-sm btn-ghost btn-icon hover:text-failure-text"
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
        <div className="flex gap-4">
          {[
            ['Pipelines', counts.pipelines],
            ['Reports', counts.reports],
            ['Emails', counts.emails],
            ['Recipients', counts.recipients],
          ].map(([label, n]) => (
            <div key={String(label)}>
              <div className="text-base font-semibold font-mono text-text-primary">{n}</div>
              <div className="text-[11px] text-text-muted">{label}</div>
            </div>
          ))}
        </div>
      )}

      {project.is_default && (
        <div className="text-[11px] text-text-muted italic">
          Default project — all unassigned resources land here
        </div>
      )}

      {isActive && (
        <div className="inline-flex items-center gap-1 text-[11px] font-semibold" style={{ color: project.color || 'var(--accent)' }}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: project.color || 'var(--accent)' }} />{' '}
          Active filter
        </div>
      )}
    </div>
  )
}

export default function Projects() {
  const [modalProject, setModalProject] = useState<Project | undefined>(undefined)
  const [showModal, setShowModal] = useState(false)
  const [membersProject, setMembersProject] = useState<Project | undefined>(undefined)

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
      <div className="scroll">
        <div className="page-h">
          <div className="flex flex-col gap-2">
            <Sk h={28} r={6} style={{ width: 120 }} />
            <Sk h={14} style={{ width: 260 }} />
          </div>
        </div>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-3">
          {[0, 1, 2].map(i => (
            <div key={i} className="card flex flex-col gap-3">
              <div className="flex items-center gap-2.5">
                <Sk h={10} r={99} style={{ width: 10, flexShrink: 0 }} />
                <Sk h={14} style={{ width: 130 }} />
              </div>
              <div className="flex gap-4">
                {[0, 1, 2, 3].map(j => (
                  <div key={j} className="flex flex-col gap-1">
                    <Sk h={16} style={{ width: 24 }} />
                    <Sk h={10} style={{ width: 45 }} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
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
            <Layers size={32} className="text-text-muted mb-2" />
            <p className="msg">No projects yet.</p>
            <button className="btn btn-primary" onClick={openCreate}>Create your first project</button>
          </div>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-3">
            {projects.map(p => (
              <ProjectCard key={p.id} project={p} onEdit={openEdit} onManageMembers={setMembersProject} />
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <ProjectModal project={modalProject} onClose={() => setShowModal(false)} />
      )}

      {membersProject && (
        <MembersModal project={membersProject} onClose={() => setMembersProject(undefined)} />
      )}
    </>
  )
}
