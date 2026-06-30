'use client'
import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'

type Analytics = {
  totalLeads: number
  tierCounts: Record<string, number>
  statusCounts: Record<string, number>
  sourceCounts: Record<string, number>
  messageSent: number
  messageReplied: number
  replyRate: number
  trend: { date: string; count: number }[]
  campaigns: { id: string; name: string; status: string; enrolled: number; messages: number }[]
}

const TIER_COLORS  = { Hot: '#ef4444', Warm: '#f59e0b', Cold: '#94a3b8' }
const STATUS_COLORS = ['#3b82f6', '#8b5cf6', '#22c55e', '#10b981', '#64748b']

export default function AnalyticsPage() {
  const [data, setData]   = useState<Analytics | null>(null)
  const [days, setDays]   = useState(30)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/analytics?days=${days}`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false) })
  }, [days])

  if (loading || !data) return <div className="p-8 text-slate-400">Loading analytics…</div>

  const tierData   = Object.entries(data.tierCounts).map(([name, value]) => ({ name, value }))
  const statusData = Object.entries(data.statusCounts).map(([name, value]) => ({ name, value }))

  const metrics = [
    { label: 'Total Leads',  value: data.totalLeads },
    { label: 'Emails Sent',  value: data.messageSent },
    { label: 'Replies',      value: data.messageReplied },
    { label: 'Reply Rate',   value: `${data.replyRate}%` },
    { label: 'Hot Leads',    value: data.tierCounts.Hot || 0 },
    { label: 'Warm Leads',   value: data.tierCounts.Warm || 0 },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-900">Analytics</h1>
        <select className="input w-auto" value={days} onChange={(e) => setDays(Number(e.target.value))}>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="card p-4">
            <p className="text-sm text-slate-500">{m.label}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{m.value}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Daily trend */}
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 mb-4">Emails Sent per Day</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data.trend}>
              <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => v.slice(5)} />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#16a34a" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Tier breakdown */}
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 mb-4">Lead Tiers</h3>
          {tierData.length === 0 ? (
            <p className="text-sm text-slate-400 py-8 text-center">No leads yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={tierData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
                  {tierData.map((entry) => (
                    <Cell key={entry.name} fill={TIER_COLORS[entry.name as keyof typeof TIER_COLORS] || '#94a3b8'} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Status breakdown */}
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 mb-4">Lead Status Breakdown</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={statusData} layout="vertical">
              <XAxis type="number" tick={{ fontSize: 10 }} allowDecimals={false} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={80} />
              <Tooltip />
              <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                {statusData.map((_, i) => (
                  <Cell key={i} fill={STATUS_COLORS[i % STATUS_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Campaign leaderboard */}
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 mb-4">Campaign Performance</h3>
          {data.campaigns.length === 0 ? (
            <p className="text-sm text-slate-400">No campaigns yet.</p>
          ) : (
            <div className="space-y-2">
              {data.campaigns.map((c) => (
                <div key={c.id} className="flex items-center gap-3 py-1.5 border-b border-slate-100">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-slate-900">{c.name}</p>
                    <p className="text-xs text-slate-400">{c.enrolled} enrolled · {c.messages} msgs</p>
                  </div>
                  <span className={`badge text-xs ${c.status === 'active' ? 'bg-green-100 text-green-700 border-green-200' : 'bg-slate-100 text-slate-500 border-slate-200'}`}>
                    {c.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
