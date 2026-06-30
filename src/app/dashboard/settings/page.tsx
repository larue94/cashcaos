'use client'
import { useEffect, useState } from 'react'

type Settings = {
  providers: { email: string; enrichment: string; crm: string; llm: string }
  socialChannels: { name: string; available: boolean; note?: string }[]
  models: { anthropic: string; openai: string }
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [icps, setIcps]         = useState<{ id: string; name: string; isActive: boolean; scoringWeights: Record<string, number>; description: string }[]>([])

  useEffect(() => {
    Promise.all([
      fetch('/api/settings').then((r) => r.json()),
      fetch('/api/icp').then((r) => r.json()),
    ]).then(([s, i]) => {
      setSettings(s)
      setIcps(i)
    })
  }, [])

  async function toggleIcp(id: string, isActive: boolean) {
    await fetch('/api/icp', {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ id, isActive }),
    })
    const res = await fetch('/api/icp')
    setIcps(await res.json())
  }

  async function updateWeights(id: string, weights: Record<string, number>) {
    await fetch('/api/icp', {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ id, scoringWeights: weights }),
    })
  }

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <h1 className="text-xl font-bold text-slate-900">Settings</h1>

      {/* Provider status */}
      <div className="card p-5">
        <h3 className="font-semibold text-slate-900 mb-4">Active Providers</h3>
        {settings ? (
          <div className="space-y-3">
            {Object.entries(settings.providers).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between text-sm">
                <span className="text-slate-500 capitalize">{k}</span>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${v === 'mock' ? 'bg-amber-400' : 'bg-green-500'}`} />
                  <code className="bg-slate-100 px-2 py-0.5 rounded text-xs">{v}</code>
                  {v === 'mock' && (
                    <span className="text-xs text-slate-400">Set in .env</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-400 text-sm">Loading…</p>
        )}
      </div>

      {/* Social channels */}
      {settings && (
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 mb-4">Social Channels</h3>
          <div className="space-y-3">
            {settings.socialChannels.map((ch) => (
              <div key={ch.name} className="flex items-start gap-3">
                <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${ch.available ? 'bg-green-500' : 'bg-slate-300'}`} />
                <div>
                  <p className="text-sm font-medium text-slate-900">{ch.name}</p>
                  {ch.note && <p className="text-xs text-slate-400 mt-0.5">{ch.note}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ICP profiles */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-slate-900">ICP Profiles</h3>
          <a href="/dashboard/onboarding" className="btn-secondary text-xs">+ New ICP</a>
        </div>
        {icps.length === 0 ? (
          <p className="text-sm text-slate-400">No ICP profiles yet. <a href="/dashboard/onboarding" className="text-brand-600 hover:underline">Create one</a>.</p>
        ) : (
          <div className="space-y-3">
            {icps.map((icp) => (
              <div key={icp.id} className="border border-slate-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-slate-900">{icp.name}</h4>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={icp.isActive}
                      onChange={(e) => toggleIcp(icp.id, e.target.checked)}
                      className="rounded"
                    />
                    Active
                  </label>
                </div>
                <p className="text-xs text-slate-500 mb-3">{icp.description}</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400">Fit weight %</label>
                    <input
                      type="number" min={0} max={100}
                      className="input text-sm mt-0.5"
                      defaultValue={icp.scoringWeights.fit ?? 60}
                      onBlur={(e) => updateWeights(icp.id, {
                        ...icp.scoringWeights,
                        fit:    Number(e.target.value),
                        intent: 100 - Number(e.target.value),
                      })}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400">Intent weight %</label>
                    <input
                      type="number" min={0} max={100}
                      className="input text-sm mt-0.5"
                      defaultValue={icp.scoringWeights.intent ?? 40}
                      readOnly
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Webhook info */}
      <div className="card p-5">
        <h3 className="font-semibold text-slate-900 mb-3">Signal Webhook</h3>
        <p className="text-sm text-slate-500 mb-3">
          POST buying signals from external tools to this endpoint:
        </p>
        <code className="block bg-slate-900 text-green-400 text-xs p-3 rounded-lg">
          POST {typeof window !== 'undefined' ? window.location.origin : 'https://your-app.com'}/api/webhooks/signals
        </code>
        <div className="mt-3 text-xs text-slate-500 space-y-1">
          <p>Required headers: <code className="bg-slate-100 px-1 rounded">x-webhook-secret: YOUR_WEBHOOK_SIGNAL_SECRET</code></p>
          <p>Body fields: <code className="bg-slate-100 px-1 rounded">email | leadId, type, source, payload, weight?, occurredAt?</code></p>
        </div>
      </div>

      {/* .env reference */}
      <div className="card p-5">
        <h3 className="font-semibold text-slate-900 mb-3">Environment Variables</h3>
        <p className="text-sm text-slate-500">
          All credentials are configured via environment variables. See{' '}
          <code className="bg-slate-100 px-1 rounded">.env.example</code> for the full list.
        </p>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-500">
          {[
            'ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'APOLLO_API_KEY',
            'HUBSPOT_ACCESS_TOKEN', 'RESEND_API_KEY', 'GMAIL_CLIENT_ID',
            'LLM_PROVIDER', 'EMAIL_PROVIDER', 'ENRICHMENT_PROVIDER',
          ].map((k) => (
            <code key={k} className="bg-slate-50 border border-slate-200 px-2 py-1 rounded">{k}</code>
          ))}
        </div>
      </div>
    </div>
  )
}
