'use client'
import { useEffect, useState } from 'react'
import { cn, statusColor } from '@/lib/utils'
import { CampaignBuilder } from '@/components/campaigns/CampaignBuilder'

type Step = { id: string; order: number; channel: string; subject: string; template: string; delayDays: number; aiPersonalize: boolean }
type Campaign = {
  id: string; name: string; description: string; channels: string[]; mode: string;
  status: string; createdAt: string; steps: Step[];
  _count: { enrollments: number; messages: number }
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading]     = useState(true)
  const [building, setBuilding]   = useState(false)

  async function fetchCampaigns() {
    const res  = await fetch('/api/campaigns')
    const data = await res.json()
    setCampaigns(data)
    setLoading(false)
  }

  useEffect(() => { fetchCampaigns() }, [])

  async function updateStatus(id: string, status: string) {
    await fetch(`/api/campaigns/${id}`, {
      method:  'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ status }),
    })
    fetchCampaigns()
  }

  async function deleteCampaign(id: string) {
    if (!confirm('Delete this campaign?')) return
    await fetch(`/api/campaigns/${id}`, { method: 'DELETE' })
    fetchCampaigns()
  }

  if (building) {
    return <CampaignBuilder onSave={() => { setBuilding(false); fetchCampaigns() }} onCancel={() => setBuilding(false)} />
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Campaigns</h1>
          <p className="text-sm text-slate-500">{campaigns.length} campaigns</p>
        </div>
        <button onClick={() => setBuilding(true)} className="btn-primary">+ New Campaign</button>
      </div>

      {loading ? (
        <p className="text-slate-400">Loading…</p>
      ) : campaigns.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-slate-400 mb-4">No campaigns yet.</p>
          <button onClick={() => setBuilding(true)} className="btn-primary">Create your first campaign</button>
        </div>
      ) : (
        <div className="space-y-4">
          {campaigns.map((c) => (
            <div key={c.id} className="card p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-semibold text-slate-900">{c.name}</h3>
                    <span className={cn('badge', statusColor(c.status))}>{c.status}</span>
                    <span className="badge bg-slate-100 text-slate-600 border-slate-200">
                      {c.mode === 'auto' ? '⚡ Auto' : '🧑 Copilot'}
                    </span>
                  </div>
                  {c.description && <p className="text-sm text-slate-500 mb-3">{c.description}</p>}
                  <div className="flex gap-4 text-xs text-slate-500">
                    <span>📩 {c.channels.join(', ')}</span>
                    <span>🪜 {c.steps.length} steps</span>
                    <span>👥 {c._count.enrollments} enrolled</span>
                    <span>📨 {c._count.messages} messages</span>
                  </div>
                </div>
                <div className="flex gap-2 ml-4">
                  {c.status === 'draft' && (
                    <button onClick={() => updateStatus(c.id, 'active')} className="btn-primary text-xs py-1.5">
                      ▶ Launch
                    </button>
                  )}
                  {c.status === 'active' && (
                    <button onClick={() => updateStatus(c.id, 'paused')} className="btn-secondary text-xs py-1.5">
                      ⏸ Pause
                    </button>
                  )}
                  {c.status === 'paused' && (
                    <button onClick={() => updateStatus(c.id, 'active')} className="btn-secondary text-xs py-1.5">
                      ▶ Resume
                    </button>
                  )}
                  <button onClick={() => deleteCampaign(c.id)} className="btn-secondary text-xs py-1.5 text-red-500">
                    Delete
                  </button>
                </div>
              </div>

              {/* Steps preview */}
              {c.steps.length > 0 && (
                <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
                  {c.steps.map((step, i) => (
                    <div key={step.id} className="flex items-center gap-2 flex-shrink-0">
                      <div className="bg-slate-100 rounded-lg px-3 py-2 text-xs">
                        <div className="font-medium text-slate-700">Step {i + 1} · {step.channel}</div>
                        <div className="text-slate-400">{step.delayDays === 0 ? 'Immediate' : `+${step.delayDays}d`}</div>
                      </div>
                      {i < c.steps.length - 1 && <div className="text-slate-300">→</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
