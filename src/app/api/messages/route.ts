import { NextRequest } from 'next/server'
import { prisma } from '@/lib/db'
import { requireOrg, ok, err } from '@/lib/api-helpers'
import { getEmailChannel } from '@/adapters/email'
import { draftOutreachMessage } from '@/adapters/llm'

export async function GET(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const { searchParams } = new URL(req.url)
  const status     = searchParams.get('status')
  const direction  = searchParams.get('direction')
  const campaignId = searchParams.get('campaignId')
  const leadId     = searchParams.get('leadId')

  const where: Record<string, unknown> = { lead: { orgId: orgId! } }
  if (status)     where.status     = status
  if (direction)  where.direction  = direction
  if (campaignId) where.campaignId = campaignId
  if (leadId)     where.leadId     = leadId

  const messages = await prisma.message.findMany({
    where,
    orderBy: { createdAt: 'desc' },
    take: 100,
    include: { lead: { select: { firstName: true, lastName: true, email: true, company: true } } },
  })
  return ok(messages)
}

// Approve and send a draft message
export async function PATCH(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const body = await req.json()
  if (!body.id) return err('id required')

  const msg = await prisma.message.findFirst({
    where:   { id: body.id, lead: { orgId: orgId! } },
    include: { lead: true },
  })
  if (!msg) return err('Not found', 404)

  if (body.action === 'approve') {
    if (msg.channel === 'email') {
      const email = getEmailChannel()
      try {
        const { messageId, threadId } = await email.send({
          to:       msg.lead.email || '',
          subject:  msg.subject || '(no subject)',
          body:     body.body || msg.body,
          threadId: msg.threadId || undefined,
        })
        await prisma.message.update({
          where: { id: msg.id },
          data: {
            status:     'sent',
            sentAt:     new Date(),
            externalId: messageId,
            threadId:   threadId || msg.threadId,
            body:       body.body || msg.body,
          },
        })
        await prisma.activity.create({
          data: { leadId: msg.leadId, type: 'email_sent', payload: { messageId } },
        })
      } catch (e) {
        await prisma.message.update({
          where: { id: msg.id },
          data: { status: 'failed', errorMsg: String(e) },
        })
        return err(`Send failed: ${e}`, 500)
      }
    }
  } else if (body.action === 'edit') {
    await prisma.message.update({
      where: { id: msg.id },
      data:  { body: body.body, subject: body.subject },
    })
  } else if (body.action === 'discard') {
    await prisma.message.update({ where: { id: msg.id }, data: { status: 'failed' } })
  }

  const updated = await prisma.message.findUnique({ where: { id: msg.id } })
  return ok(updated)
}

// Draft a personalized message
export async function POST(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const body = await req.json()
  if (!body.leadId) return err('leadId required')

  const lead = await prisma.lead.findFirst({ where: { id: body.leadId, orgId: orgId! } })
  if (!lead) return err('Lead not found', 404)

  const icp = await prisma.icpProfile.findFirst({ where: { orgId: orgId!, isActive: true } })

  let msgBody = body.template || ''
  if (body.aiPersonalize && icp) {
    try {
      msgBody = await draftOutreachMessage({
        leadName:       `${lead.firstName || ''} ${lead.lastName || ''}`.trim() || lead.email || '',
        leadTitle:      lead.title    || undefined,
        leadCompany:    lead.company  || undefined,
        senderName:     'The Team',
        icpDescription: icp.description,
        channel:        body.channel  || 'email',
        template:       body.template || '',
        stepNumber:     body.stepNumber || 1,
      })
    } catch {
      // fall back to template
    }
  }

  const message = await prisma.message.create({
    data: {
      leadId:     body.leadId,
      campaignId: body.campaignId || null,
      stepId:     body.stepId     || null,
      channel:    body.channel    || 'email',
      direction:  'out',
      subject:    body.subject    || '',
      body:       msgBody,
      status:     'draft',
    },
  })
  return ok(message, 201)
}
