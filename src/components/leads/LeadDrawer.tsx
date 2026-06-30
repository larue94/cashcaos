'use client'
import { useEffect, useState } from 'react'
import { cn, tierColor, statusColor } from '@/lib/utils'
import { format } from 'date-fns'

type Signal = { id: string; type: string; source: string; weight: number; occurredAt: string; payload: Record<string, unknown> }
type Message = { id: string; channel: string; direction: string; subject: string; body: string; status: string; createdAt: string }
type Lead = {
  id: string; firstName: string; lastName: string; email: string; title: string;
  company: string; domain: string; linkedinUrl: string; location: string; industry: string;
  companySize: string; tier: string; fitScore: number; intentScore: number; totalScore: number;
  status: string; source: string; llmRationale: string; tags: string[];
  signals: Signal[]; messages: Message[]; activities: unknown[]
}

const SIGNAL_TYPES = [
  'website_visit', 'competitor_engagement', 'follows_company',
  'hiring', 'tech_stack', 'manual', 'webhook',
]

export function LeadDrawer({ leadId, onClose }: { leadId: string; onClose: () => void }) {
  const [lead, setLead] = useState<Lead | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'overview' | 'signals' | 'messages'>('overview')
  const [addingSignal, setAddingSignal] = useState(false)
  const [sigType, setSigType] = useState('manual')
  const [sigNote, setSigNote] = useState('')
  const [scoring, setScoring] = useState(false)

  async function fetchLead() {
    const res  = await fetch(`/api/leads/${leadId}`)
    const data = await res.json()
    setLead(data)
    setLoading(false)
  }

  useEffect(() => { fetchLead() }, [leadId])

  async function addSignal() {
    await fetch('/api/signals', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ leadId, type: sigType, source: 'manual', payload: { note: sigNote }, weight: 1 }),
    })
    setAddingSignal(false)
    setSigNote('')
    fetchLead()
  }

  async function rescore() {
    setScoring(true)
    await fetch(`/api/leads/${leadId}?action=score`, { method: 'POST' })
    await fetchLead()
    setScoring(false)
  }

  async function updateStatus(status: string) {
    await fetch(`/api/leads/${leadId}`, {
      method:  'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ status }),
    })
    fetchLead()
  }

  async function enrich() {
    await fetch('/api/enrich', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ leadId }),
    })
    fetchLead()
  }

  if (loading) {
    return (
      <div className="fixed inset-y-0 right-0 w-[520px] bg-white border-l border-slate-200 shadow-xl flex items-center justify-center z-40">
        <p className="text-slate-400">Loading…</p>
      </div>
    )
  }
  if (!lead) return null

  const name = [lead.firstName, lead.lastName].filter(Boolean).join(' ') || lead.email || 'Unknown'

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-30" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 w-[520px] bg-white border-l border-slate-200 shadow-xl z-40 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-start justify-between">
          <div className="flex-1">
            <h2 className="text-lg font-bold text-slate-900">{name}</h2>
            <p className="text-sm text-slate-500">{lead.title}{lead.company && ` · ${lead.company}`}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 ml-4">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Score bar */}
        <div className="px-5 py-3 bg-slate-50 border-b border-slate-100 flex items-center gap-4">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-500">Score</span>
              <span className="text-sm font-bold text-slate-900">{Math.round(lead.totalScore)}/100</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div
                className={cn('h-2 rounded-full', lead.tier === 'Hot' ? 'bg-red-500' : lead.tier === 'Warm' ? 'bg-amber-400' : 'bg-slate-400')}
                style={{ width: `${lead.totalScore}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-400 mt-1">
              <span>Fit: {Math.round(lead.fitScore)}</span>
              <span>Intent: {Math.round(lead.intentScore)}</span>
            </div>
          </div>
          <span className={cn('badge', tierColor(lead.tier))}>{lead.tier}</span>
          <button onClick={rescore} disabled={scoring} className="btn-secondary text-xs py-1 px-2">
            {scoring ? '…' : 'Re-score'}
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200">
          {(['overview', 'signals', 'messages'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                'flex-1 py-2.5 text-sm font-medium capitalize',
                tab === t ? 'text-brand-600 border-b-2 border-brand-600' : 'text-slate-500 hover:text-slate-700'
              )}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {tab === 'overview' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                {[
                  { label: 'Email',    value: lead.email },
                  { label: 'Domain',   value: lead.domain },
                  { label: 'Industry', value: lead.industry },
                  { label: 'Size',     value: lead.companySize },
                  { label: 'Location', value: lead.location },
                  { label: 'Source',   value: lead.source },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <p className="text-xs text-slate-400 uppercase tracking-wide">{label}</p>
                    <p className="font-medium text-slate-900 truncate">{value || '—'}</p>
                  </div>
                ))}
              </div>

              {lead.linkedinUrl && (
                <a href={lead.linkedinUrl} target="_blank" rel="noreferrer" className="btn-secondary text-xs">
                  🔗 LinkedIn Profile
                </a>
              )}

              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Status</p>
                <select
                  className="input w-auto"
                  value={lead.status}
                  onChange={(e) => updateStatus(e.target.value)}
                >
                  {['new', 'contacted', 'replied', 'booked', 'disqualified'].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              {lead.llmRationale && (
                <div className="bg-brand-50 rounded-lg p-3">
                  <p className="text-xs text-brand-700 font-semibold mb-1">🤖 AI Score Rationale</p>
                  <p className="text-sm text-brand-900">{lead.llmRationale}</p>
                </div>
              )}

              <button onClick={enrich} className="btn-secondary text-xs">
                ✨ Enrich with {process.env.NEXT_PUBLIC_ENRICHMENT_PROVIDER || 'provider'}
              </button>
            </div>
          )}

          {tab === 'signals' && (
            <div className="space-y-3">
              <button onClick={() => setAddingSignal(true)} className="btn-secondary text-xs">+ Add Signal</button>

              {addingSignal && (
                <div className="card p-3 space-y-2">
                  <select className="input text-sm" value={sigType} onChange={(e) => setSigType(e.target.value)}>
                    {SIGNAL_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                  <input className="input text-sm" placeholder="Note" value={sigNote} onChange={(e) => setSigNote(e.target.value)} />
                  <div className="flex gap-2">
                    <button onClick={addSignal} className="btn-primary text-xs py-1">Save</button>
                    <button onClick={() => setAddingSignal(false)} className="btn-secondary text-xs py-1">Cancel</button>
                  </div>
                </div>
              )}

              {lead.signals.length === 0 ? (
                <p className="text-sm text-slate-400">No signals yet.</p>
              ) : (
                lead.signals.map((s) => (
                  <div key={s.id} className="flex items-start gap-3 py-2 border-b border-slate-100">
                    <div className="w-2 h-2 bg-brand-500 rounded-full mt-1.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-slate-900 capitalize">{s.type.replace(/_/g, ' ')}</p>
                      <p className="text-xs text-slate-400">
                        {s.source} · weight {s.weight} · {format(new Date(s.occurredAt), 'MMM d, yyyy')}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === 'messages' && (
            <div className="space-y-3">
              {lead.messages.length === 0 ? (
                <p className="text-sm text-slate-400">No messages yet.</p>
              ) : (
                lead.messages.map((m) => (
                  <div key={m.id} className={cn('rounded-lg p-3', m.direction === 'in' ? 'bg-slate-50' : 'bg-brand-50')}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-slate-500">{m.direction === 'in' ? '← Reply' : '→ Sent'} · {m.channel}</span>
                      <span className={cn('badge text-xs', statusColor(m.status))}>{m.status}</span>
                    </div>
                    {m.subject && <p className="text-xs font-semibold text-slate-700 mb-1">Re: {m.subject}</p>}
                    <p className="text-sm text-slate-700 whitespace-pre-wrap">{m.body}</p>
                    <p className="text-xs text-slate-400 mt-1">{format(new Date(m.createdAt), 'MMM d, h:mm a')}</p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
