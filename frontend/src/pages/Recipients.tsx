import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, Check, X } from 'lucide-react'
import { getRecipientGroups, createRecipientGroup, updateRecipientGroup, deleteRecipientGroup } from '../lib/api'
import type { RecipientGroup } from '../lib/types'
import { useProjectStore } from '../lib/store'
import { useCurrentUser } from '../lib/auth'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import PageIntro from '../components/shared/PageIntro'
import Sk from '../components/shared/Skeleton'

function ChipInput({ values, onChange, id }: { values: string[]; onChange: (v: string[]) => void; id?: string }) {
  const [input, setInput] = useState('')
  const add = () => {
    const v = input.trim()
    if (v && !values.includes(v)) onChange([...values, v])
    setInput('')
  }
  return (
    <div className="input flex flex-wrap gap-1 min-h-9 !h-auto !py-1.5">
      {values.map(v => (
        <span key={v} className="chip">
          {v}<button className="x" onClick={() => onChange(values.filter(x => x !== v))}><X size={10}/></button>
        </span>
      ))}
      <input id={id} className="flex-1 bg-transparent outline-none text-sm min-w-40"
        value={input} onChange={e => setInput(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add() } }}
        onBlur={add} placeholder={values.length === 0 ? 'email@example.com, …' : ''}/>
    </div>
  )
}

function GroupRow({ group, onSaved, onDelete, canEdit }: { group: RecipientGroup; onSaved: () => void; onDelete: () => void; canEdit: boolean }) {
  const [editing, setEditing] = useState(false)
  const [name, setName]       = useState(group.name)
  const [desc, setDesc]       = useState(group.description)
  const [addresses, setAddresses] = useState(group.addresses)
  const { mutate: save, isPending } = useMutation({
    mutationFn: () => updateRecipientGroup(group.id, { name, description: desc, addresses }),
    onSuccess: () => { setEditing(false); onSaved() },
  })

  if (!editing) {
    return (
      <tr>
        <td className="font-medium !text-text-primary">{group.name}</td>
        <td className="!text-text-3 text-xs">{group.description}</td>
        <td>
          <div className="flex flex-wrap gap-1">
            {group.addresses.map(a => <span key={a} className="chip !h-5 !text-[11px]">{a}</span>)}
          </div>
        </td>
        {canEdit && (
          <td>
            <div className="flex gap-1 justify-end">
              <button className="btn btn-sm btn-ghost btn-icon" onClick={() => setEditing(true)}><Pencil size={12} /></button>
              <button className="btn btn-sm btn-ghost btn-icon" onClick={() => globalThis.confirm(`Delete "${group.name}"?`) && onDelete()}><Trash2 size={12} /></button>
            </div>
          </td>
        )}
      </tr>
    )
  }

  return (
    <tr>
      <td><input className="input !h-8" value={name} onChange={e => setName(e.target.value)} /></td>
      <td><input className="input !h-8" value={desc} onChange={e => setDesc(e.target.value)} /></td>
      <td><ChipInput values={addresses} onChange={setAddresses} /></td>
      <td>
        <div className="flex gap-1 justify-end">
          <button className="btn btn-sm btn-ghost btn-icon !text-success-text" onClick={() => save()} disabled={isPending}>
            {isPending ? <Spinner size={12} /> : <Check size={13} />}
          </button>
          <button className="btn btn-sm btn-ghost btn-icon" onClick={() => setEditing(false)}><X size={13} /></button>
        </div>
      </td>
    </tr>
  )
}

export default function Recipients() {
  const qc = useQueryClient()
  const { activeProjectId } = useProjectStore()
  const me = useCurrentUser()
  const canEdit = me?.role !== 'viewer'
  const { data: groups = [], isLoading } = useQuery({
    queryKey: ['recipient-groups', activeProjectId],
    queryFn: () => getRecipientGroups(activeProjectId ? { project_id: activeProjectId } : undefined),
  })
  const [showNew, setShowNew]   = useState(false)
  const [newName, setNewName]   = useState('')
  const [newDesc, setNewDesc]   = useState('')
  const [newAddrs, setNewAddrs] = useState<string[]>([])

  const { mutate: remove }   = useMutation({ mutationFn: deleteRecipientGroup, onSuccess: () => qc.invalidateQueries({ queryKey: ['recipient-groups'] }) })
  const { mutate: add, isPending } = useMutation({
    mutationFn: () => createRecipientGroup({ name: newName, description: newDesc, addresses: newAddrs, project_id: activeProjectId ?? undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['recipient-groups'] }); setShowNew(false); setNewName(''); setNewDesc(''); setNewAddrs([]) },
  })

  if (isLoading) return (
    <>
      <TopBar crumbs={['Workspace', 'Recipients']} />
      <div className="scroll">
        <div className="page-h">
          <div className="flex flex-col gap-2">
            <Sk h={28} r={6} style={{ width: 180 }} />
            <Sk h={14} style={{ width: 70 }} />
          </div>
        </div>
        <div className="card !p-0 overflow-hidden">
          <table className="tbl">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Addresses</th>
                <th className="w-20" />
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 6 }, (_, i) => i).map(n => (
                <tr key={'sk-' + n}>
                  <td><Sk h={14} style={{ width: '50%' }} /></td>
                  <td><Sk h={12} style={{ width: '60%' }} /></td>
                  <td><Sk h={12} style={{ width: '75%' }} /></td>
                  <td><Sk h={24} r={4} style={{ width: 50, marginLeft: 'auto' }} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Recipients']}
        helpTopic="recipients"
        actions={canEdit ? <button className="btn btn-primary btn-sm" onClick={() => setShowNew(true)}><Plus size={13} /> New Group</button> : undefined}
      />
      <div className="scroll">
        <PageIntro page="recipients" />
        <div className="page-h">
          <div>
            <h1>Recipient Groups</h1>
            <p>{groups.length} group{groups.length !== 1 ? 's' : ''}</p>
          </div>
        </div>

        {showNew && (
          <div className="card mb-4 flex flex-col gap-3 !border-[rgba(249,115,22,0.3)]">
            <div className="text-[13px] font-semibold text-text-primary">New Group</div>
            <div className="grid grid-cols-2 gap-3">
              <div className="field"><label htmlFor="rg-name">Name *</label><input id="rg-name" className="input" value={newName} onChange={e => setNewName(e.target.value)} /></div>
              <div className="field"><label htmlFor="rg-desc">Description</label><input id="rg-desc" className="input" value={newDesc} onChange={e => setNewDesc(e.target.value)} /></div>
            </div>
            <div className="field"><label htmlFor="rg-addresses">Email addresses</label><ChipInput id="rg-addresses" values={newAddrs} onChange={setNewAddrs} /></div>
            <div className="flex gap-2">
              <button className="btn btn-primary btn-sm" onClick={() => add()} disabled={isPending || !newName}>
                {isPending ? <Spinner size={12} /> : null} Create
              </button>
              <button className="btn btn-sm" onClick={() => setShowNew(false)}>Cancel</button>
            </div>
          </div>
        )}

        <div className="card !p-0 overflow-hidden">
          <table className="tbl">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Addresses</th>
                <th className="w-20" />
              </tr>
            </thead>
            <tbody>
              {groups.length === 0 && <tr><td colSpan={4} className="text-center !py-10 !px-0 !text-text-muted">No recipient groups yet. Create a named list of addresses — "Finance Team", "Management" — and assign it to an email config.</td></tr>}
              {groups.map(g => <GroupRow key={g.id} group={g} canEdit={canEdit} onSaved={() => qc.invalidateQueries({ queryKey: ['recipient-groups'] })} onDelete={() => remove(g.id)} />)}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
