import { NextRequest } from 'next/server'
import { prisma } from '@/lib/db'
import { requireOrg, ok, err } from '@/lib/api-helpers'
import { scoreQueue } from '@/lib/queue'

export async function GET(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const leadId = new URL(req.url).searchParams.get('leadId')
  const signals = await prisma.signal.findMany({
    where:   leadId ? { leadId } : { lead: { orgId: orgId! } },
    orderBy: { occurredAt: 'desc' },
    take:    200,
  })
  return ok(signals)
}

export async function POST(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const body = await req.json()
  if (!body.leadId) return err('leadId required')

  // Verify lead belongs to org
  const lead = await prisma.lead.findFirst({ where: { id: body.leadId, orgId: orgId! } })
  if (!lead) return err('Lead not found', 404)

  const signal = await prisma.signal.create({
    data: {
      leadId:     body.leadId,
      type:       body.type   || 'manual',
      source:     body.source || 'manual',
      payload:    body.payload || {},
      weight:     body.weight  || 1.0,
      occurredAt: body.occurredAt ? new Date(body.occurredAt) : new Date(),
    },
  })

  // Re-score lead
  await scoreQueue.add('score', { leadId: body.leadId })

  return ok(signal, 201)
}
