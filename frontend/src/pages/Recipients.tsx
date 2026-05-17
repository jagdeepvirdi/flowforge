import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, Check, X } from 'lucide-react'
import { getRecipientGroups, createRecipientGroup, updateRecipientGroup, deleteRecipientGroup } from '../lib/api'
import type { RecipientGroup } from '../lib/types'
import PageHeader from '../components/shared/PageHeader'
import Spinner from '../components/shared/Spinner'

function ChipInput({ values, onChange }: { values: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState('')
  const add = () => {
    const v = input.trim()
    if (v && !values.includes(v)) onChange([...values, v])
    setInput('')
  }
  return (
    <div className="input flex flex-wrap gap-1 min-h-9 h-auto py-1.5">
      {values.map(v => (
        <span key={v} className="badge-muted flex items-center gap-1">
          {v}<button onClick={() => onChange(values.filter(x => x !== v))}><X size={10}/></button>
        </span>
      ))}
      <input className="flex-1 bg-transparent outline-none text-sm min-w-40"
        value={input} onChange={e => setInput(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add() } }}
        onBlur={add} placeholder={values.length === 0 ? 'email@example.com, …' : ''}/>
    </div>
  )
}

function GroupRow({ group, onSaved, onDelete }: { group: RecipientGroup; onSaved: () => void; onDelete: () => void }) {
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
      <tr className="border-b border-border/50 last:border-0 hover:bg-surface2/50">
        <td className="px-4 py-3 font-medium text-text-primary">{group.name}</td>
        <td className="px-4 py-3 text-text-muted text-xs">{group.description}</td>
        <td className="px-4 py-3">
          <div className="flex flex-wrap gap-1">{group.addresses.map(a => <span key={a} className="badge-muted text-xs">{a}</span>)}</div>
        </td>
        <td className="px-4 py-3">
          <div className="flex gap-1 justify-end">
            <button className="btn-ghost p-1.5" onClick={() => setEditing(true)}><Pencil size={14}/></button>
            <button className="btn-ghost p-1.5 hover:text-danger" onClick={() => window.confirm(`Delete "${group.name}"?`) && onDelete()}><Trash2 size={14}/></button>
          </div>
        </td>
      </tr>
    )
  }

  return (
    <tr className="border-b border-border/50">
      <td className="px-4 py-3"><input className="input" value={name} onChange={e => setName(e.target.value)}/></td>
      <td className="px-4 py-3"><input className="input text-sm" value={desc} onChange={e => setDesc(e.target.value)}/></td>
      <td className="px-4 py-3"><ChipInput values={addresses} onChange={setAddresses}/></td>
      <td className="px-4 py-3">
        <div className="flex gap-1 justify-end">
          <button className="btn-ghost p-1.5 text-success" onClick={() => save()} disabled={isPending}>{isPending ? <Spinner size={13}/> : <Check size={14}/>}</button>
          <button className="btn-ghost p-1.5" onClick={() => setEditing(false)}><X size={14}/></button>
        </div>
      </td>
    </tr>
  )
}

export default function Recipients() {
  const qc = useQueryClient()
  const { data: groups = [], isLoading } = useQuery({ queryKey: ['recipient-groups'], queryFn: getRecipientGroups })
  const [showNew, setShowNew]   = useState(false)
  const [newName, setNewName]   = useState('')
  const [newDesc, setNewDesc]   = useState('')
  const [newAddrs, setNewAddrs] = useState<string[]>([])

  const { mutate: remove }   = useMutation({ mutationFn: deleteRecipientGroup, onSuccess: () => qc.invalidateQueries({ queryKey: ['recipient-groups'] }) })
  const { mutate: add, isPending } = useMutation({
    mutationFn: () => createRecipientGroup({ name: newName, description: newDesc, addresses: newAddrs }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['recipient-groups'] }); setShowNew(false); setNewName(''); setNewDesc(''); setNewAddrs([]) },
  })

  if (isLoading) return <div className="p-8 flex justify-center"><Spinner /></div>

  return (
    <div className="p-8">
      <PageHeader title="Recipient Groups" subtitle={`${groups.length} groups`}
        action={<button className="btn-primary" onClick={() => setShowNew(true)}><Plus size={15}/> New Group</button>} />

      {showNew && (
        <div className="card mb-4 space-y-3 border-accent/30">
          <h3 className="text-sm font-medium text-text-primary">New Group</h3>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Name *</label><input className="input" value={newName} onChange={e => setNewName(e.target.value)}/></div>
            <div><label className="label">Description</label><input className="input" value={newDesc} onChange={e => setNewDesc(e.target.value)}/></div>
          </div>
          <div><label className="label">Email addresses</label><ChipInput values={newAddrs} onChange={setNewAddrs}/></div>
          <div className="flex gap-2">
            <button className="btn-primary" onClick={() => add()} disabled={isPending || !newName}>{isPending ? <Spinner size={14}/> : null} Create</button>
            <button className="btn-secondary" onClick={() => setShowNew(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="border-b border-border">
            <tr className="text-xs text-text-muted">
              <th className="text-left px-4 py-3">Name</th>
              <th className="text-left px-4 py-3">Description</th>
              <th className="text-left px-4 py-3">Addresses</th>
              <th className="px-4 py-3"/>
            </tr>
          </thead>
          <tbody>
            {groups.length === 0 && <tr><td colSpan={4} className="text-center py-8 text-text-muted">No groups yet.</td></tr>}
            {groups.map(g => <GroupRow key={g.id} group={g} onSaved={() => qc.invalidateQueries({ queryKey: ['recipient-groups'] })} onDelete={() => remove(g.id)} />)}
          </tbody>
        </table>
      </div>
    </div>
  )
}
