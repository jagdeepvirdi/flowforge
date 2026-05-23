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
    <span style={{
      display: 'inline-block',
      width: 8,
      height: 8,
      borderRadius: '50%',
      background: color || '#F97316',
      flexShrink: 0,
    }} />
  )
}

export default function ProjectSwitcher() {
  const { activeProjectId, setActiveProjectId } = useProjectStore()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  })

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
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
    <div ref={ref} style={{ position: 'relative', marginBottom: 4 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '7px 10px',
          background: open ? '#21252F' : 'transparent',
          border: '1px solid',
          borderColor: open ? '#3D4460' : 'transparent',
          borderRadius: 8,
          cursor: 'pointer',
          color: 'var(--text)',
          fontSize: 12.5,
          fontWeight: 600,
          transition: 'border-color 0.15s, background 0.15s',
        }}
        onMouseEnter={e => { if (!open) (e.currentTarget.style.background = '#1E2130') }}
        onMouseLeave={e => { if (!open) (e.currentTarget.style.background = 'transparent') }}
      >
        {color ? <ColorDot color={color} /> : (
          <Layers size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
        )}
        <span style={{ flex: 1, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {label}
        </span>
        <ChevronDown size={12} style={{ color: 'var(--text-muted)', flexShrink: 0, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 4px)',
          left: 0,
          right: 0,
          background: '#21252F',
          border: '1px solid #2D3143',
          borderRadius: 8,
          boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
          zIndex: 100,
          overflow: 'hidden',
          minWidth: 180,
        }}>
          <button
            onClick={() => select(null)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 12px',
              background: activeProjectId === null ? '#2D3143' : 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: activeProjectId === null ? 'var(--text)' : 'var(--text-muted)',
              fontSize: 12.5,
              fontWeight: activeProjectId === null ? 600 : 400,
              textAlign: 'left',
            }}
          >
            <Layers size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            All Projects
          </button>

          {projects.length > 0 && (
            <div style={{ borderTop: '1px solid #2D3143' }}>
              {projects.map(p => (
                <button
                  key={p.id}
                  onClick={() => select(p.id)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '8px 12px',
                    background: activeProjectId === p.id ? '#2D3143' : 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: activeProjectId === p.id ? 'var(--text)' : 'var(--text-muted)',
                    fontSize: 12.5,
                    fontWeight: activeProjectId === p.id ? 600 : 400,
                    textAlign: 'left',
                  }}
                >
                  <ColorDot color={p.color || PROJECT_COLORS[0]} />
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</span>
                </button>
              ))}
            </div>
          )}

          <div style={{ borderTop: '1px solid #2D3143' }}>
            <Link
              to="/projects"
              onClick={() => setOpen(false)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 12px',
                color: 'var(--accent)',
                fontSize: 12.5,
                textDecoration: 'none',
                fontWeight: 500,
              }}
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
