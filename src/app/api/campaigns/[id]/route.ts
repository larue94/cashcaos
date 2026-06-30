import { NextRequest } from 'next/server'
import { prisma } from '@/lib/db'
import { requireOrg, ok, err } from '@/lib/api-helpers'
import { sequenceQueue } from '@/lib/queue'
import { addDays } from 'date-fns'

export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const campaign = await prisma.campaign.findFirst({
    where:   { id: params.id, orgId: orgId! },
    include: { steps: { orderBy: { order: 'asc' } }, enrollments: { take: 10 } },
  })
  if (!campaign) return err('Not found', 404)
  return ok(campaign)
}

export async function PATCH(req: NextRequest, { params }: { params: { id: string } }) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const body = await req.json()

  if (body.status === 'active') {
    // Enroll matching leads
    const campaign = await prisma.campaign.findFirst({
      where:   { id: params.id, orgId: orgId! },
      include: { steps: { orderBy: { order: 'asc' } } },
    })
    if (!campaign) return err('Not found', 404)

    const leads = await prisma.lead.findMany({
      where: { orgId: orgId!, unsubscribed: false, status: { not: 'disqualified' } },
    })

    for (const lead of leads) {
      try {
        const enrollment = await prisma.enrollment.create({
          data: {
            campaignId: params.id,
            leadId:     lead.id,
            stepIndex:  0,
            status:     'active',
            nextSendAt: new Date(),
          },
        })

        const firstStep = campaign.steps[0]
        if (firstStep) {
          const delay = firstStep.delayDays * 24 * 60 * 60 * 1000
          await sequenceQueue.add(
            'send-step',
            { enrollmentId: enrollment.id, stepIndex: 0, leadId: lead.id, campaignId: params.id },
            { delay }
          )
        }
      } catch {
        // enrollment already exists — skip
      }
    }
  }

  const updated = await prisma.campaign.updateMany({
    where: { id: params.id, orgId: orgId! },
    data:  { status: body.status, name: body.name, mode: body.mode, description: body.description },
  })
  return ok(updated)
}

export async function DELETE(_req: NextRequest, { params }: { params: { id: string } }) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  await prisma.campaign.deleteMany({ where: { id: params.id, orgId: orgId! } })
  return ok({ deleted: true })
}
