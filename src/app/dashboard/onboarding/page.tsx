'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState<'url' | 'edit'>('url')
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [icp, setIcp] = useState({
    name:             'My ICP',
    description:      '',
    targetTitles:     [] as string[],
    targetIndustries: [] as string[],
    companySizeMin:   null as number | null,
    companySizeMax:   null as number | null,
    keywords:         [] as string[],
    websiteUrl:       '',
    scoringWeights:   { fit: 60, intent: 40 },
  })

  async function fetchFromUrl() {
    setLoading(true)
    try {
      const res  = await fetch('/api/icp', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ websiteUrl: url }),
      })
      const data = await res.json()
      setIcp({ ...icp, ...data, websiteUrl: url })
      setStep('edit')
    } catch {
      alert('Could not extract ICP. Fill in manually.')
      setStep('edit')
    } finally {
      setLoading(false)
    }
  }

  async function saveIcp() {
    setLoading(true)
    await fetch('/api/icp', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ ...icp }),
    })
    setLoading(false)
    router.push('/dashboard')
  }

  function listField(key: 'targetTitles' | 'targetIndustries' | 'keywords') {
    return (
      <textarea
        className="input font-mono"
        rows={3}
        placeholder="One per line"
        value={(icp[key] as string[]).join('\n')}
        onChange={(e) =>
          setIcp({ ...icp, [key]: e.target.value.split('\n').map((s) => s.trim()).filter(Boolean) })
        }
      />
    )
  }

  if (step === 'url') {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <div className="card p-10 max-w-lg w-full">
          <div className="text-4xl mb-4 text-center">🎯</div>
          <h1 className="text-xl font-bold text-slate-900 text-center mb-2">Define your ICP</h1>
          <p className="text-slate-500 text-center mb-8">
            Paste your website URL and our AI will extract your Ideal Customer Profile, or skip to fill it in manually.
          </p>
          <div className="space-y-4">
            <div>
              <label className="label">Your website URL</label>
              <input
                type="url"
                className="input"
                placeholder="https://yourcompany.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={fetchFromUrl}
                disabled={loading || !url}
                className="btn-primary flex-1 justify-center"
              >
                {loading ? 'Analyzing…' : '✨ Extract with AI'}
              </button>
              <button onClick={() => setStep('edit')} className="btn-secondary">
                Skip
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-xl font-bold text-slate-900 mb-1">Edit your ICP</h1>
      <p className="text-slate-500 mb-6">This drives lead scoring and AI personalization.</p>

      <div className="card p-6 space-y-5">
        <div>
          <label className="label">Profile name</label>
          <input className="input" value={icp.name} onChange={(e) => setIcp({ ...icp, name: e.target.value })} />
        </div>

        <div>
          <label className="label">What you sell (2–3 sentences)</label>
          <textarea className="input" rows={3} value={icp.description}
            onChange={(e) => setIcp({ ...icp, description: e.target.value })} />
        </div>

        <div>
          <label className="label">Target job titles (one per line)</label>
          {listField('targetTitles')}
        </div>

        <div>
          <label className="label">Target industries (one per line)</label>
          {listField('targetIndustries')}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Company size min (employees)</label>
            <input type="number" className="input" value={icp.companySizeMin || ''}
              onChange={(e) => setIcp({ ...icp, companySizeMin: e.target.value ? Number(e.target.value) : null })} />
          </div>
          <div>
            <label className="label">Company size max</label>
            <input type="number" className="input" value={icp.companySizeMax || ''}
              onChange={(e) => setIcp({ ...icp, companySizeMax: e.target.value ? Number(e.target.value) : null })} />
          </div>
        </div>

        <div>
          <label className="label">Keywords (one per line)</label>
          {listField('keywords')}
        </div>

        <div>
          <label className="label">Scoring weights</label>
          <div className="grid grid-cols-2 gap-4 mt-2">
            <div>
              <label className="text-xs text-slate-500">Firmographic fit %</label>
              <input type="number" min={0} max={100} className="input mt-1"
                value={icp.scoringWeights.fit}
                onChange={(e) => setIcp({ ...icp, scoringWeights: { ...icp.scoringWeights, fit: Number(e.target.value), intent: 100 - Number(e.target.value) } })} />
            </div>
            <div>
              <label className="text-xs text-slate-500">Intent signals %</label>
              <input type="number" min={0} max={100} className="input mt-1"
                value={icp.scoringWeights.intent} readOnly />
            </div>
          </div>
        </div>

        <button onClick={saveIcp} disabled={loading} className="btn-primary w-full justify-center">
          {loading ? 'Saving…' : 'Save ICP & Continue →'}
        </button>
      </div>
    </div>
  )
}
