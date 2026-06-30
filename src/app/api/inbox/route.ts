import { NextRequest } from 'next/server'
import { prisma } from '@/lib/db'
import { requireOrg, ok, err } from '@/lib/api-helpers'
import { draftReply } from '@/adapters/llm'

// Unified inbox — all inbound messages grouped by thread
export async function GET(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const messages = await prisma.message.findMany({
    where:   { direction: 'in', lead: { orgId: orgId! } },
    orderBy: { createdAt: 'desc' },
    take:    200,
    include: { lead: { select: { id: true, firstName: true, lastName: true, email: true, company: true } } },
  })

  // Group by threadId
  const threads = new Map<string, typeof messages>()
  for (const m of messages) {
    const key = m.threadId || m.id
    if (!threads.has(key)) threads.set(key, [])
    threads.get(key)!.push(m)
  }

  return ok(Array.from(threads.values()))
}

// POST /api/inbox/reply — AI-draft a reply
export async function POST(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const body = await req.json()
  if (!body.threadId && !body.leadId) return err('threadId or leadId required')

  const messages = await prisma.message.findMany({
    where:   body.threadId
      ? { threadId: body.threadId, lead: { orgId: orgId! } }
      : { leadId: body.leadId,    lead: { orgId: orgId! } },
    orderBy: { createdAt: 'asc' },
    take:    10,
    include: { lead: true },
  })
  if (!messages.length) return err('No messages found', 404)

  const icp = await prisma.icpProfile.findFirst({ where: { orgId: orgId!, isActive: true } })

  const threadSummary = messages
    .map((m: { direction: string; body: string }) => `[${m.direction === 'in' ? 'THEM' : 'US'}]: ${m.body}`)
    .join('\n\n')

  let suggestion = ''
  try {
    suggestion = await draftReply({
      threadSummary,
      icpDescription: icp?.description || 'B2B SaaS product',
      tone:           body.tone || 'friendly and professional',
    })
  } catch {
    suggestion = ''
  }

  return ok({ suggestion })
}
