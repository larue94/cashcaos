'use client'
import { useState } from 'react'

type Step = {
  order: number; channel: string; subject: string; template: string;
  delayDays: number; aiPersonalize: boolean
}

const DEFAULT_STEP: Step = {
  order: 0, channel: 'email', subject: '', template: '', delayDays: 0, aiPersonalize: true,
}

export function CampaignBuilder({ onSave, onCancel }: { onSave: () => void; onCancel: () => void }) {
  const [name, setName]         = useState('')
  const [desc, setDesc]         = useState('')
  const [mode, setMode]         = useState('copilot')
  const [steps, setSteps]       = useState<Step[]>([{ ...DEFAULT_STEP }])
  const [saving, setSaving]     = useState(false)

  function addStep() {
    setSteps([...steps, { ...DEFAULT_STEP, order: steps.length, delayDays: 3 }])
  }

  function removeStep(i: number) {
    setSteps(steps.filter((_, idx) => idx !== i).map((s, idx) => ({ ...s, order: idx })))
  }

  function updateStep(i: number, patch: Partial<Step>) {
    setSteps(steps.map((s, idx) => idx === i ? { ...s, ...patch } : s))
  }

  async function save() {
    if (!name) return alert('Campaign name required')
    if (!steps.length) return alert('Add at least one step')
    setSaving(true)
    await fetch('/api/campaigns', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ name, description: desc, channels: ['email'], mode, steps }),
    })
    setSaving(false)
    onSave()
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={onCancel} className="text-slate-400 hover:text-slate-600">
          ← Back
        </button>
        <h1 className="text-xl font-bold text-slate-900">New Campaign</h1>
      </div>

      <div className="space-y-6">
        <div className="card p-5 space-y-4">
          <div>
            <label className="label">Campaign name *</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Q3 Outbound — SaaS CTOs" />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea className="input" rows={2} value={desc} onChange={(e) => setDesc(e.target.value)} />
          </div>
          <div>
            <label className="label">Mode</label>
            <div className="flex gap-3 mt-1">
              {[
                { value: 'copilot', label: '🧑 Copilot', desc: 'Drafts queued for your approval before sending' },
                { value: 'auto',    label: '⚡ Auto',    desc: 'Messages sent automatically (use with care)' },
              ].map((opt) => (
                <label
                  key={opt.value}
                  className={`flex-1 border rounded-lg p-3 cursor-pointer ${mode === opt.value ? 'border-brand-500 bg-brand-50' : 'border-slate-200'}`}
                >
                  <input type="radio" value={opt.value} checked={mode === opt.value}
                    onChange={() => setMode(opt.value)} className="sr-only" />
                  <p className="font-medium text-sm text-slate-900">{opt.label}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{opt.desc}</p>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div>
          <h3 className="font-semibold text-slate-900 mb-3">Sequence Steps</h3>
          <div className="space-y-3">
            {steps.map((step, i) => (
              <div key={i} className="card p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-semibold text-slate-700">Step {i + 1}</span>
                  {steps.length > 1 && (
                    <button onClick={() => removeStep(i)} className="text-xs text-red-400 hover:text-red-600">Remove</button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label text-xs">Channel</label>
                    <select className="input text-sm" value={step.channel}
                      onChange={(e) => updateStep(i, { channel: e.target.value })}>
                      <option value="email">Email</option>
                    </select>
                  </div>
                  <div>
                    <label className="label text-xs">Send after (days)</label>
                    <input type="number" min={0} className="input text-sm"
                      value={step.delayDays}
                      onChange={(e) => updateStep(i, { delayDays: Number(e.target.value) })} />
                  </div>
                </div>
                <div className="mt-3">
                  <label className="label text-xs">Subject (email)</label>
                  <input className="input text-sm" value={step.subject}
                    onChange={(e) => updateStep(i, { subject: e.target.value })}
                    placeholder="Subject line…" />
                </div>
                <div className="mt-3">
                  <label className="label text-xs">Message template</label>
                  <textarea className="input text-sm font-mono" rows={4} value={step.template}
                    onChange={(e) => updateStep(i, { template: e.target.value })}
                    placeholder="Hi {{firstName}}, I noticed {{company}} is…" />
                </div>
                <label className="flex items-center gap-2 mt-3 text-sm text-slate-600 cursor-pointer">
                  <input type="checkbox" checked={step.aiPersonalize}
                    onChange={(e) => updateStep(i, { aiPersonalize: e.target.checked })}
                    className="rounded border-slate-300 text-brand-600" />
                  AI personalize before sending
                </label>
              </div>
            ))}
          </div>
          <button onClick={addStep} className="btn-secondary mt-3 text-sm">
            + Add Step
          </button>
        </div>

        <div className="flex gap-3">
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? 'Saving…' : 'Save Campaign'}
          </button>
          <button onClick={onCancel} className="btn-secondary">Cancel</button>
        </div>
      </div>
    </div>
  )
}
