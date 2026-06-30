import { NextRequest } from 'next/server'
import { prisma } from '@/lib/db'
import { requireOrg, ok, err } from '@/lib/api-helpers'

export async function GET() {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const campaigns = await prisma.campaign.findMany({
    where:   { orgId: orgId! },
    orderBy: { createdAt: 'desc' },
    include: { steps: { orderBy: { order: 'asc' } }, _count: { select: { enrollments: true, messages: true } } },
  })
  return ok(campaigns)
}

export async function POST(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const body = await req.json()
  if (!body.name) return err('name required')

  const campaign = await prisma.campaign.create({
    data: {
      orgId:          orgId!,
      name:           body.name,
      description:    body.description || '',
      channels:       body.channels    || ['email'],
      mode:           body.mode        || 'copilot',
      status:         'draft',
      segmentFilter:  body.segmentFilter || null,
      steps: {
        create: (body.steps || []).map((s: {
          order: number; channel: string; subject?: string;
          template: string; delayDays: number; aiPersonalize: boolean
        }, i: number) => ({
          order:         s.order ?? i,
          channel:       s.channel || 'email',
          subject:       s.subject || '',
          template:      s.template || '',
          delayDays:     s.delayDays || 0,
          aiPersonalize: s.aiPersonalize ?? true,
        })),
      },
    },
    include: { steps: true },
  })
  return ok(campaign, 201)
}
