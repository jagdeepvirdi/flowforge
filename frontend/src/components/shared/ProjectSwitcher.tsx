import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, Plus, Layers } from 'lucide-react'
import { getProjects } from '../../lib/api'
import { useProjectStore } from '../../lib/store'

const PROJECT_COLORS = [
  '#F97316', '#3B82F6', '#22C55E', '#A855F7',
  '#EC4899', '#EAB308', '#14B8A6', '#F43F5E',
]

function ColorDot({ color }: { color: string }) {
  return (
    <span
      className="inline-block w-2 h-2 rounded-full shrink-0"
      style={{ background: color || 'var(--accent)' }}
    />
  )
}

export default function ProjectSwitcher({ compact = false }: { compact?: boolean }) {
  const { activeProjectId, setActiveProjectId } = useProjectStore()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
    staleTime: 0,
  })

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && e.target instanceof Node && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const activeProject = projects.find(p => p.id === activeProjectId)
  const label = activeProject ? activeProject.name : 'All Projects'
  const color = activeProject?.color || null

  function select(id: string | null) {
    setActiveProjectId(id)
    setOpen(false)
  }

  return (
    <div ref={ref} className={`relative ${compact ? 'mb-0' : 'mb-1'}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className={`flex items-center gap-2 rounded-r-sm cursor-pointer text-text-primary text-[12.5px] font-semibold transition-colors duration-150 whitespace-nowrap border ${compact ? 'py-1 px-2' : 'w-full py-[7px] px-2.5'} ${open ? 'bg-surface2 border-[#3D4460]' : 'bg-transparent border-transparent hover:bg-surface-hover'}`}
      >
        {color ? <ColorDot color={color} /> : (
          <Layers size={12} className="text-text-muted shrink-0" />
        )}
        <span className="flex-1 text-left overflow-hidden text-ellipsis whitespace-nowrap">
          {label}
        </span>
        <ChevronDown size={12} className={`text-text-muted shrink-0 transition-transform duration-150 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className={`absolute top-[calc(100%+4px)] left-0 bg-surface2 border border-border rounded-r shadow-[0_8px_24px_rgba(0,0,0,0.4)] z-[100] overflow-hidden min-w-[180px] ${compact ? '' : 'right-0'}`}>
          <button
            onClick={() => select(null)}
            className={`w-full flex items-center gap-2 py-2 px-3 border-none cursor-pointer text-[12.5px] text-left ${activeProjectId === null ? 'bg-border text-text-primary font-semibold' : 'bg-transparent text-text-muted font-normal'}`}
          >
            <Layers size={12} className="text-text-muted shrink-0" />
            All Projects
          </button>

          {projects.length > 0 && (
            <div className="border-t border-border">
              {projects.map(p => (
                <button
                  key={p.id}
                  onClick={() => select(p.id)}
                  className={`w-full flex items-center gap-2 py-2 px-3 border-none cursor-pointer text-[12.5px] text-left ${activeProjectId === p.id ? 'bg-border text-text-primary font-semibold' : 'bg-transparent text-text-muted font-normal'}`}
                >
                  <ColorDot color={p.color || PROJECT_COLORS[0]} />
                  <span className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap">{p.name}</span>
                </button>
              ))}
            </div>
          )}

          <div className="border-t border-border">
            <Link
              to="/projects"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 py-2 px-3 text-accent text-[12.5px] no-underline font-medium"
            >
              <Plus size={12} />
              Manage projects
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
