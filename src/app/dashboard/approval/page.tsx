'use client'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'

type Lead = { firstName: string; lastName: string; email: string; company: string }
type Message = {
  id: string; channel: string; subject: string; body: string; status: string; createdAt: string;
  lead: Lead
}

export default function ApprovalPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading]   = useState(true)
  const [editing, setEditing]   = useState<Record<string, { subject: string; body: string }>>({})
  const [busy, setBusy]         = useState<Record<string, boolean>>({})

  async function fetchDrafts() {
    const res  = await fetch('/api/messages?status=draft&direction=out')
    const data = await res.json()
    setMessages(data)
    setLoading(false)
  }

  useEffect(() => { fetchDrafts() }, [])

  function getEdit(m: Message) {
    return editing[m.id] || { subject: m.subject, body: m.body }
  }

  async function action(m: Message, act: 'approve' | 'discard') {
    setBusy({ ...busy, [m.id]: true })
    await fetch('/api/messages', {
      method:  'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ id: m.id, action: act, ...getEdit(m) }),
    })
    setBusy({ ...busy, [m.id]: false })
    fetchDrafts()
  }

  async function saveEdit(m: Message) {
    setBusy({ ...busy, [m.id]: true })
    await fetch('/api/messages', {
      method:  'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ id: m.id, action: 'edit', ...getEdit(m) }),
    })
    setBusy({ ...busy, [m.id]: false })
    setEditing({ ...editing, [m.id]: undefined! })
    fetchDrafts()
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Approval Queue</h1>
          <p className="text-sm text-slate-500">Review and approve AI-drafted messages before sending</p>
        </div>
        <span className="badge bg-amber-100 text-amber-700 border-amber-200 text-sm">
          {messages.length} pending
        </span>
      </div>

      {loading ? (
        <p className="text-slate-400">Loading…</p>
      ) : messages.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="text-4xl mb-3">✅</div>
          <p className="text-slate-500">No messages awaiting approval.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {messages.map((m) => {
            const edit = getEdit(m)
            const isEditing = !!editing[m.id]
            return (
              <div key={m.id} className="card p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-medium text-slate-900">
                      {[m.lead.firstName, m.lead.lastName].filter(Boolean).join(' ') || m.lead.email}
                      {m.lead.company && <span className="text-slate-400"> · {m.lead.company}</span>}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {m.channel} · {format(new Date(m.createdAt), 'MMM d, h:mm a')}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => action(m, 'approve')}
                      disabled={busy[m.id]}
                      className="btn-primary text-xs py-1.5"
                    >
                      {busy[m.id] ? '…' : '✉ Send'}
                    </button>
                    <button
                      onClick={() => setEditing({ ...editing, [m.id]: { subject: m.subject, body: m.body } })}
                      className="btn-secondary text-xs py-1.5"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => action(m, 'discard')}
                      disabled={busy[m.id]}
                      className="btn-secondary text-xs py-1.5 text-red-500"
                    >
                      Discard
                    </button>
                  </div>
                </div>

                {isEditing ? (
                  <div className="space-y-2">
                    <input
                      className="input text-sm"
                      placeholder="Subject"
                      value={edit.subject}
                      onChange={(e) => setEditing({ ...editing, [m.id]: { ...edit, subject: e.target.value } })}
                    />
                    <textarea
                      className="input text-sm font-mono"
                      rows={6}
                      value={edit.body}
                      onChange={(e) => setEditing({ ...editing, [m.id]: { ...edit, body: e.target.value } })}
                    />
                    <div className="flex gap-2">
                      <button onClick={() => saveEdit(m)} className="btn-primary text-xs py-1.5">Save</button>
                      <button onClick={() => setEditing({ ...editing, [m.id]: undefined! })} className="btn-secondary text-xs py-1.5">Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div className="bg-slate-50 rounded-lg p-3">
                    {m.subject && <p className="text-xs font-semibold text-slate-600 mb-2">Subject: {m.subject}</p>}
                    <p className="text-sm text-slate-700 whitespace-pre-wrap">{m.body}</p>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
