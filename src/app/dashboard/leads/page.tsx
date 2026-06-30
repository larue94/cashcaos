'use client'
import { useEffect, useState, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Papa from 'papaparse'
import { tierColor, statusColor, cn } from '@/lib/utils'
import { LeadDrawer } from '@/components/leads/LeadDrawer'

type Lead = {
  id: string; firstName: string; lastName: string; email: string; title: string;
  company: string; domain: string; tier: string; totalScore: number; fitScore: number;
  intentScore: number; status: string; source: string; signals: unknown[]
}

export default function LeadsPage() {
  const sp     = useSearchParams()
  const router = useRouter()
  const [leads, setLeads] = useState<Lead[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [tierFilter, setTierFilter] = useState(sp.get('tier') || '')
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedLead, setSelectedLead] = useState<string | null>(null)
  const [importing, setImporting] = useState(false)
  const [showManual, setShowManual] = useState(false)
  const [newLead, setNewLead] = useState({ firstName: '', lastName: '', email: '', title: '', company: '' })

  const fetchLeads = useCallback(async () => {
    setLoading(true)
    const params = new URLSearchParams()
    if (search)       params.set('search', search)
    if (tierFilter)   params.set('tier',   tierFilter)
    if (statusFilter) params.set('status', statusFilter)
    const res  = await fetch(`/api/leads?${params}`)
    const data = await res.json()
    setLeads(data.leads || [])
    setTotal(data.total || 0)
    setLoading(false)
  }, [search, tierFilter, statusFilter])

  useEffect(() => { fetchLeads() }, [fetchLeads])

  async function handleCsvUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: async (results) => {
        await fetch('/api/leads', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify(results.data),
        })
        setImporting(false)
        fetchLeads()
      },
    })
    e.target.value = ''
  }

  async function addManualLead() {
    await fetch('/api/leads', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ ...newLead, source: 'manual' }),
    })
    setShowManual(false)
    setNewLead({ firstName: '', lastName: '', email: '', title: '', company: '' })
    fetchLeads()
  }

  async function triggerScore(leadId: string) {
    await fetch(`/api/leads/${leadId}?action=score`, { method: 'POST' })
    fetchLeads()
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Leads</h1>
          <p className="text-sm text-slate-500">{total} prospects</p>
        </div>
        <div className="flex gap-2">
          <label className={cn('btn-secondary cursor-pointer', importing && 'opacity-50')}>
            {importing ? 'Importing…' : '📥 Import CSV'}
            <input type="file" accept=".csv" className="hidden" onChange={handleCsvUpload} disabled={importing} />
          </label>
          <button onClick={() => setShowManual(true)} className="btn-primary">+ Add Lead</button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="search"
          placeholder="Search leads…"
          className="input max-w-xs"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="input w-auto" value={tierFilter} onChange={(e) => setTierFilter(e.target.value)}>
          <option value="">All tiers</option>
          <option>Hot</option>
          <option>Warm</option>
          <option>Cold</option>
        </select>
        <select className="input w-auto" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="replied">Replied</option>
          <option value="booked">Booked</option>
          <option value="disqualified">Disqualified</option>
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              {['Name', 'Company', 'Title', 'Score', 'Tier', 'Status', 'Signals', ''].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-12 text-center text-slate-400">Loading…</td></tr>
            ) : leads.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-12 text-center text-slate-400">
                No leads found. <button onClick={() => setShowManual(true)} className="text-brand-600 hover:underline">Add one</button> or import a CSV.
              </td></tr>
            ) : (
              leads.map((lead) => (
                <tr
                  key={lead.id}
                  className="hover:bg-slate-50 cursor-pointer"
                  onClick={() => setSelectedLead(lead.id)}
                >
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {[lead.firstName, lead.lastName].filter(Boolean).join(' ') || lead.email || '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{lead.company || '—'}</td>
                  <td className="px-4 py-3 text-slate-500">{lead.title || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <div className="w-16 bg-slate-100 rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full bg-brand-500"
                          style={{ width: `${lead.totalScore}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-slate-700">{Math.round(lead.totalScore)}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn('badge', tierColor(lead.tier))}>{lead.tier}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn('badge', statusColor(lead.status))}>{lead.status}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{(lead.signals as unknown[]).length} signals</td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => triggerScore(lead.id)}
                      className="text-xs text-slate-400 hover:text-brand-600"
                    >
                      Re-score
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Manual add modal */}
      {showManual && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="card p-6 w-full max-w-md">
            <h3 className="font-semibold text-slate-900 mb-4">Add Lead</h3>
            <div className="space-y-3">
              {(['firstName', 'lastName', 'email', 'title', 'company'] as const).map((f) => (
                <div key={f}>
                  <label className="label capitalize">{f.replace(/([A-Z])/g, ' $1')}</label>
                  <input className="input" value={newLead[f]}
                    onChange={(e) => setNewLead({ ...newLead, [f]: e.target.value })} />
                </div>
              ))}
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={addManualLead} className="btn-primary flex-1 justify-center">Add Lead</button>
              <button onClick={() => setShowManual(false)} className="btn-secondary">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Lead drawer */}
      {selectedLead && (
        <LeadDrawer
          leadId={selectedLead}
          onClose={() => { setSelectedLead(null); fetchLeads() }}
        />
      )}
    </div>
  )
}
