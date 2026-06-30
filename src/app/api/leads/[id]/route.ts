import { NextRequest } from 'next/server'
import { prisma } from '@/lib/db'
import { requireOrg, ok, err } from '@/lib/api-helpers'
import { scoreLead } from '@/lib/scoring'
import { generateScoreRationale } from '@/adapters/llm'
import { scoreQueue, enrichQueue } from '@/lib/queue'

export async function GET(req: NextRequest, { params }: { params: { id: string } }) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const lead = await prisma.lead.findFirst({
    where: { id: params.id, orgId: orgId! },
    include: {
      signals:    { orderBy: { occurredAt: 'desc' } },
      messages:   { orderBy: { createdAt: 'desc' }, take: 20 },
      activities: { orderBy: { createdAt: 'desc' }, take: 30 },
    },
  })
  if (!lead) return err('Not found', 404)
  return ok(lead)
}

export async function PATCH(req: NextRequest, { params }: { params: { id: string } }) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const body = await req.json()

  const lead = await prisma.lead.updateMany({
    where:  { id: params.id, orgId: orgId! },
    data:   body,
  })
  return ok(lead)
}

export async function DELETE(_req: NextRequest, { params }: { params: { id: string } }) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  await prisma.lead.deleteMany({ where: { id: params.id, orgId: orgId! } })
  return ok({ deleted: true })
}

// POST /api/leads/[id]/score — trigger re-score
export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const url  = new URL(req.url)
  const action = url.pathname.split('/').pop()

  if (action === 'score' || url.searchParams.get('action') === 'score') {
    const result = await scoreLead(params.id)

    const lead = await prisma.lead.findFirst({ where: { id: params.id, orgId: orgId! } })
    if (!lead) return err('Not found', 404)

    const icp = await prisma.icpProfile.findFirst({
      where: { orgId: orgId!, isActive: true },
    })

    if (icp) {
      try {
        const rationale = await generateScoreRationale({
          lead: lead as unknown as Record<string, unknown>,
          ...result,
          icpDescription: icp.description,
        })
        await prisma.lead.update({ where: { id: params.id }, data: { llmRationale: rationale } })
      } catch {
        // non-fatal
      }
    }

    return ok(result)
  }

  return err('Unknown action', 400)
}
