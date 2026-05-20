import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Pencil, Trash2, Check, X } from 'lucide-react'
import { getRecipientGroups, createRecipientGroup, updateRecipientGroup, deleteRecipientGroup } from '../lib/api'
import type { RecipientGroup } from '../lib/types'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import PageIntro from '../components/shared/PageIntro'

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
      <tr>
        <td style={{ fontWeight: 500, color: '#F1F5F9' }}>{group.name}</td>
        <td style={{ color: '#94A3B8', fontSize: 12 }}>{group.description}</td>
        <td>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {group.addresses.map(a => <span key={a} className="chip" style={{ height: 20, fontSize: 11 }}>{a}</span>)}
          </div>
        </td>
        <td>
          <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
            <button className="btn btn-sm btn-ghost btn-icon" onClick={() => setEditing(true)}><Pencil size={12} /></button>
            <button className="btn btn-sm btn-ghost btn-icon" onClick={() => window.confirm(`Delete "${group.name}"?`) && onDelete()}><Trash2 size={12} /></button>
          </div>
        </td>
      </tr>
    )
  }

  return (
    <tr>
      <td><input className="input" value={name} onChange={e => setName(e.target.value)} style={{ height: 32 }} /></td>
      <td><input className="input" value={desc} onChange={e => setDesc(e.target.value)} style={{ height: 32 }} /></td>
      <td><ChipInput values={addresses} onChange={setAddresses} /></td>
      <td>
        <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
          <button className="btn btn-sm btn-ghost btn-icon" onClick={() => save()} disabled={isPending} style={{ color: '#4ADE80' }}>
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

  if (isLoading) return (
    <><TopBar crumbs={['Workspace', 'Recipients']} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
  )

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Recipients']}
        helpTopic="recipients"
        actions={<button className="btn btn-primary btn-sm" onClick={() => setShowNew(true)}><Plus size={13} /> New Group</button>}
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
          <div className="card" style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 12, borderColor: 'rgba(249,115,22,0.3)' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>New Group</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="field"><label>Name *</label><input className="input" value={newName} onChange={e => setNewName(e.target.value)} /></div>
              <div className="field"><label>Description</label><input className="input" value={newDesc} onChange={e => setNewDesc(e.target.value)} /></div>
            </div>
            <div className="field"><label>Email addresses</label><ChipInput values={newAddrs} onChange={setNewAddrs} /></div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary btn-sm" onClick={() => add()} disabled={isPending || !newName}>
                {isPending ? <Spinner size={12} /> : null} Create
              </button>
              <button className="btn btn-sm" onClick={() => setShowNew(false)}>Cancel</button>
            </div>
          </div>
        )}

        <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
          <table className="tbl">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Addresses</th>
                <th style={{ width: 80 }} />
              </tr>
            </thead>
            <tbody>
              {groups.length === 0 && <tr><td colSpan={4} style={{ textAlign: 'center', padding: '40px 0', color: '#64748B' }}>No recipient groups yet. Create a named list of addresses — "Finance Team", "Management" — and assign it to an email config.</td></tr>}
              {groups.map(g => <GroupRow key={g.id} group={g} onSaved={() => qc.invalidateQueries({ queryKey: ['recipient-groups'] })} onDelete={() => remove(g.id)} />)}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
