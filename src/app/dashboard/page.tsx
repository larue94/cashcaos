import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/db'
import Link from 'next/link'

async function getStats(orgId: string) {
  const [totalLeads, hotLeads, drafts, sent, replied, campaigns] = await Promise.all([
    prisma.lead.count({ where: { orgId } }),
    prisma.lead.count({ where: { orgId, tier: 'Hot' } }),
    prisma.message.count({ where: { lead: { orgId }, status: 'draft' } }),
    prisma.message.count({ where: { lead: { orgId }, status: 'sent' } }),
    prisma.message.count({ where: { lead: { orgId }, direction: 'in' } }),
    prisma.campaign.count({ where: { orgId, status: 'active' } }),
  ])
  return { totalLeads, hotLeads, drafts, sent, replied, campaigns }
}

export default async function DashboardPage() {
  const session = await getServerSession(authOptions)
  const user    = await prisma.user.findUnique({ where: { email: session!.user!.email! }, select: { orgId: true } })

  const hasOrg = !!user?.orgId
  const stats  = hasOrg ? await getStats(user!.orgId!) : null
  const hasIcp = hasOrg
    ? (await prisma.icpProfile.count({ where: { orgId: user!.orgId! } })) > 0
    : false

  if (!hasIcp) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <div className="card p-10 max-w-lg text-center">
          <div className="text-4xl mb-4">🎯</div>
          <h2 className="text-xl font-bold text-slate-900 mb-2">Set up your ICP</h2>
          <p className="text-slate-500 mb-6">
            Tell us what you sell and who you target. We'll use this to score leads and personalize outreach.
          </p>
          <Link href="/dashboard/onboarding" className="btn-primary">
            Get Started →
          </Link>
        </div>
      </div>
    )
  }

  const s = stats!
  const cards = [
    { label: 'Total Leads',       value: s.totalLeads, icon: '👥', href: '/dashboard/leads' },
    { label: 'Hot Leads',         value: s.hotLeads,   icon: '🔥', href: '/dashboard/leads?tier=Hot' },
    { label: 'Awaiting Approval', value: s.drafts,     icon: '✅', href: '/dashboard/approval' },
    { label: 'Emails Sent',       value: s.sent,       icon: '📨', href: '/dashboard/analytics' },
    { label: 'Replies',           value: s.replied,    icon: '💬', href: '/dashboard/inbox' },
    { label: 'Active Campaigns',  value: s.campaigns,  icon: '🚀', href: '/dashboard/campaigns' },
  ]

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Overview</h1>
        <p className="text-slate-500 mt-1">Your outbound pipeline at a glance</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {cards.map((c) => (
          <Link key={c.label} href={c.href} className="card p-5 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{c.icon}</span>
              <div>
                <p className="text-2xl font-bold text-slate-900">{c.value}</p>
                <p className="text-sm text-slate-500">{c.label}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 mb-4">Quick Actions</h3>
          <div className="space-y-2">
            <Link href="/dashboard/leads" className="btn-secondary w-full justify-center">
              📥 Import Leads (CSV)
            </Link>
            <Link href="/dashboard/campaigns" className="btn-secondary w-full justify-center">
              ➕ Create Campaign
            </Link>
            <Link href="/dashboard/approval" className="btn-secondary w-full justify-center">
              ✅ Review Draft Messages ({s.drafts})
            </Link>
          </div>
        </div>

        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 mb-4">Pipeline Health</h3>
          {s.totalLeads === 0 ? (
            <p className="text-sm text-slate-400">No leads yet. <Link href="/dashboard/leads" className="text-brand-600 hover:underline">Import some leads</Link> to get started.</p>
          ) : (
            <div className="space-y-3">
              {[
                { label: 'Reply rate', value: s.sent > 0 ? `${Math.round((s.replied / s.sent) * 100)}%` : '—' },
                { label: 'Hot leads',  value: s.totalLeads > 0 ? `${Math.round((s.hotLeads / s.totalLeads) * 100)}% of pipeline` : '—' },
                { label: 'In queue',   value: `${s.drafts} drafts awaiting review` },
              ].map((row) => (
                <div key={row.label} className="flex justify-between text-sm">
                  <span className="text-slate-500">{row.label}</span>
                  <span className="font-medium text-slate-900">{row.value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
