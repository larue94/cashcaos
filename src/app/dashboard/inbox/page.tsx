'use client'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'

type Lead = { id: string; firstName: string; lastName: string; email: string; company: string }
type Message = { id: string; threadId: string; channel: string; direction: string; subject: string; body: string; status: string; createdAt: string; lead: Lead }
type Thread  = Message[]

export default function InboxPage() {
  const [threads, setThreads]     = useState<Thread[]>([])
  const [selected, setSelected]   = useState<Thread | null>(null)
  const [loading, setLoading]     = useState(true)
  const [replying, setReplying]   = useState('')
  const [aiSuggestion, setAiSugg] = useState('')
  const [loadingAi, setLoadingAi] = useState(false)

  async function fetchInbox() {
    const res  = await fetch('/api/inbox')
    const data = await res.json()
    setThreads(data)
    setLoading(false)
  }

  useEffect(() => { fetchInbox() }, [])

  async function fetchAiSuggestion(thread: Thread) {
    setLoadingAi(true)
    const threadId = thread[0]?.threadId || thread[0]?.id
    const res = await fetch('/api/inbox', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ threadId, tone: 'helpful and professional' }),
    })
    const data = await res.json()
    setAiSugg(data.suggestion || '')
    setReplying(data.suggestion || '')
    setLoadingAi(false)
  }

  async function sendReply() {
    if (!selected || !replying.trim()) return
    const latest = selected[selected.length - 1]
    await fetch('/api/messages', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        leadId:    latest.lead.id,
        channel:   latest.channel,
        template:  replying,
        subject:   `Re: ${latest.subject}`,
        aiPersonalize: false,
      }),
    })
    // Auto-approve
    const res  = await fetch('/api/messages?status=draft&direction=out&leadId=' + latest.lead.id)
    const msgs = await res.json()
    if (msgs[0]) {
      await fetch('/api/messages', {
        method:  'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ id: msgs[0].id, action: 'approve' }),
      })
    }
    setReplying('')
    setSelected(null)
    fetchInbox()
  }

  return (
    <div className="flex h-full">
      {/* Thread list */}
      <div className="w-72 border-r border-slate-200 bg-white flex flex-col">
        <div className="p-4 border-b border-slate-200">
          <h1 className="font-bold text-slate-900">Inbox</h1>
          <p className="text-xs text-slate-400">{threads.length} conversations</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <p className="p-4 text-sm text-slate-400">Loading…</p>
          ) : threads.length === 0 ? (
            <p className="p-4 text-sm text-slate-400">No replies yet.</p>
          ) : (
            threads.map((thread, i) => {
              const latest = thread[thread.length - 1]
              const isActive = selected?.[0]?.id === thread[0]?.id
              return (
                <button
                  key={i}
                  onClick={() => { setSelected(thread); setAiSugg(''); setReplying('') }}
                  className={cn(
                    'w-full text-left p-3 border-b border-slate-100 hover:bg-slate-50',
                    isActive && 'bg-brand-50 border-l-2 border-l-brand-500'
                  )}
                >
                  <p className="font-medium text-sm text-slate-900 truncate">
                    {[latest.lead?.firstName, latest.lead?.lastName].filter(Boolean).join(' ') || latest.lead?.email}
                  </p>
                  <p className="text-xs text-slate-500 truncate">{latest.subject || latest.body}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{format(new Date(latest.createdAt), 'MMM d')}</p>
                </button>
              )
            })
          )}
        </div>
      </div>

      {/* Thread view */}
      {selected ? (
        <div className="flex-1 flex flex-col">
          <div className="p-4 border-b border-slate-200 bg-white">
            <p className="font-semibold text-slate-900">
              {[selected[0].lead?.firstName, selected[0].lead?.lastName].filter(Boolean).join(' ') || selected[0].lead?.email}
            </p>
            <p className="text-xs text-slate-400">{selected[0].lead?.company}</p>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {selected.map((m) => (
              <div key={m.id} className={cn('max-w-prose', m.direction === 'out' ? 'ml-auto' : '')}>
                <div className={cn(
                  'rounded-xl px-4 py-3 text-sm',
                  m.direction === 'out' ? 'bg-brand-600 text-white' : 'bg-white border border-slate-200 text-slate-800'
                )}>
                  {m.subject && <p className="font-semibold text-xs mb-1 opacity-80">Re: {m.subject}</p>}
                  <p className="whitespace-pre-wrap">{m.body}</p>
                </div>
                <p className="text-xs text-slate-400 mt-0.5 px-1">{format(new Date(m.createdAt), 'MMM d, h:mm a')}</p>
              </div>
            ))}
          </div>

          {/* Reply composer */}
          <div className="border-t border-slate-200 p-4 bg-white">
            {aiSuggestion && (
              <div className="bg-brand-50 border border-brand-200 rounded-lg p-3 mb-3">
                <p className="text-xs font-semibold text-brand-700 mb-1">🤖 AI Suggestion</p>
                <p className="text-sm text-brand-900">{aiSuggestion}</p>
                <button onClick={() => setReplying(aiSuggestion)} className="text-xs text-brand-600 mt-1 hover:underline">
                  Use this
                </button>
              </div>
            )}
            <textarea
              className="input w-full mb-2"
              rows={3}
              placeholder="Write a reply…"
              value={replying}
              onChange={(e) => setReplying(e.target.value)}
            />
            <div className="flex gap-2">
              <button onClick={sendReply} disabled={!replying.trim()} className="btn-primary text-sm">
                Send Reply
              </button>
              <button
                onClick={() => fetchAiSuggestion(selected)}
                disabled={loadingAi}
                className="btn-secondary text-sm"
              >
                {loadingAi ? 'Drafting…' : '✨ AI Draft'}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-slate-300">
          <div className="text-center">
            <div className="text-5xl mb-3">📨</div>
            <p>Select a conversation</p>
          </div>
        </div>
      )}
    </div>
  )
}
