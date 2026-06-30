import { NextRequest } from 'next/server'
import { prisma } from '@/lib/db'
import { requireOrg, ok } from '@/lib/api-helpers'
import { subDays, startOfDay, format } from 'date-fns'

export async function GET(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const days = Number(new URL(req.url).searchParams.get('days') || '30')
  const since = subDays(new Date(), days)

  const [
    totalLeads,
    tierCounts,
    statusCounts,
    sourceCounts,
    recentActivity,
    messageSent,
    messageReplied,
    campaignStats,
  ] = await Promise.all([
    prisma.lead.count({ where: { orgId: orgId! } }),

    prisma.lead.groupBy({
      by: ['tier'],
      where: { orgId: orgId! },
      _count: true,
    }),

    prisma.lead.groupBy({
      by: ['status'],
      where: { orgId: orgId! },
      _count: true,
    }),

    prisma.lead.groupBy({
      by: ['source'],
      where: { orgId: orgId! },
      _count: true,
    }),

    prisma.activity.findMany({
      where:   { lead: { orgId: orgId! }, createdAt: { gte: since } },
      orderBy: { createdAt: 'desc' },
      take:    50,
      include: { lead: { select: { firstName: true, lastName: true, company: true } } },
    }),

    prisma.message.count({
      where: { lead: { orgId: orgId! }, direction: 'out', status: 'sent', sentAt: { gte: since } },
    }),

    prisma.message.count({
      where: { lead: { orgId: orgId! }, direction: 'in', createdAt: { gte: since } },
    }),

    prisma.campaign.findMany({
      where: { orgId: orgId! },
      include: {
        _count: { select: { messages: true, enrollments: true } },
      },
    }),
  ])

  // Daily trend: messages sent per day
  const dailyMessages = await prisma.message.groupBy({
    by:    ['sentAt'],
    where: { lead: { orgId: orgId! }, direction: 'out', sentAt: { gte: since } },
    _count: true,
  })

  const trendMap = new Map<string, number>()
  for (let i = 0; i < days; i++) {
    trendMap.set(format(subDays(new Date(), i), 'yyyy-MM-dd'), 0)
  }
  for (const row of dailyMessages) {
    if (row.sentAt) {
      const key = format(row.sentAt, 'yyyy-MM-dd')
      trendMap.set(key, (trendMap.get(key) || 0) + row._count)
    }
  }

  const trend = Array.from(trendMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, count]) => ({ date, count }))

  return ok({
    totalLeads,
    tierCounts:   Object.fromEntries(tierCounts.map((r: { tier: string; _count: number }) => [r.tier,   r._count])),
    statusCounts: Object.fromEntries(statusCounts.map((r: { status: string; _count: number }) => [r.status, r._count])),
    sourceCounts: Object.fromEntries(sourceCounts.map((r: { source: string; _count: number }) => [r.source, r._count])),
    messageSent,
    messageReplied,
    replyRate: messageSent > 0 ? Math.round((messageReplied / messageSent) * 100) : 0,
    trend,
    recentActivity,
    campaigns: campaignStats.map((c: { id: string; name: string; status: string; mode: string; _count: { enrollments: number; messages: number } }) => ({
      id:          c.id,
      name:        c.name,
      status:      c.status,
      mode:        c.mode,
      enrolled:    c._count.enrollments,
      messages:    c._count.messages,
    })),
  })
}
