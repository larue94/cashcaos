import 'dotenv/config'
import { Worker, Job } from 'bullmq'
import { QUEUE_SEQUENCE, QUEUE_SCORE, QUEUE_ENRICH, SequenceJobData, ScoreJobData, EnrichJobData } from '@/lib/queue'
import { prisma } from '@/lib/db'
import { scoreLead } from '@/lib/scoring'
import { getEnrichmentProvider } from '@/adapters/enrichment'
import { getEmailChannel } from '@/adapters/email'
import { draftOutreachMessage } from '@/adapters/llm'

const connection = { host: process.env.REDIS_HOST || '127.0.0.1', port: Number(process.env.REDIS_PORT) || 6379 }

// ─── Sequence Step Worker ─────────────────────────────────────────────────────

const sequenceWorker = new Worker<SequenceJobData>(
  QUEUE_SEQUENCE,
  async (job: Job<SequenceJobData>) => {
    const { enrollmentId, stepIndex, leadId, campaignId } = job.data
    console.log(`[Worker] sequence step enrollmentId=${enrollmentId} step=${stepIndex}`)

    const enrollment = await prisma.enrollment.findUnique({ where: { id: enrollmentId } })
    if (!enrollment || enrollment.status !== 'active') return

    const campaign = await prisma.campaign.findUnique({
      where:   { id: campaignId },
      include: { steps: { orderBy: { order: 'asc' } } },
    })
    if (!campaign) return

    const step = campaign.steps[stepIndex]
    if (!step) {
      await prisma.enrollment.update({ where: { id: enrollmentId }, data: { status: 'completed' } })
      return
    }

    const lead = await prisma.lead.findUnique({ where: { id: leadId } })
    if (!lead || lead.unsubscribed) return

    const icp = await prisma.icpProfile.findFirst({
      where: { orgId: campaign.orgId, isActive: true },
    })

    let body = step.template
    if (step.aiPersonalize && icp) {
      try {
        body = await draftOutreachMessage({
          leadName:       `${lead.firstName || ''} ${lead.lastName || ''}`.trim() || lead.email || 'there',
          leadTitle:      lead.title   || undefined,
          leadCompany:    lead.company || undefined,
          senderName:     'The Team',
          icpDescription: icp.description,
          channel:        step.channel,
          template:       step.template,
          stepNumber:     stepIndex + 1,
        })
      } catch (e) {
        console.error('[Worker] LLM draft failed, using template', e)
      }
    }

    if (campaign.mode === 'auto') {
      // Send immediately
      if (step.channel === 'email') {
        const emailCh = getEmailChannel()
        try {
          const { messageId, threadId } = await emailCh.send({
            to:      lead.email || '',
            subject: step.subject || '(no subject)',
            body,
          })
          await prisma.message.create({
            data: {
              leadId,
              campaignId,
              stepId:    step.id,
              channel:   step.channel,
              direction: 'out',
              subject:   step.subject || '',
              body,
              status:    'sent',
              sentAt:    new Date(),
              externalId: messageId,
              threadId,
            },
          })
          await prisma.activity.create({
            data: { leadId, type: 'email_sent', payload: { stepIndex, campaignId } },
          })
        } catch (e) {
          console.error('[Worker] Send failed', e)
        }
      }
    } else {
      // Copilot: create a draft for approval
      await prisma.message.create({
        data: {
          leadId,
          campaignId,
          stepId:    step.id,
          channel:   step.channel,
          direction: 'out',
          subject:   step.subject || '',
          body,
          status:    'draft',
        },
      })
    }

    // Schedule next step
    const nextStep = campaign.steps[stepIndex + 1]
    if (nextStep) {
      const delay = nextStep.delayDays * 24 * 60 * 60 * 1000
      const { sequenceQueue } = await import('@/lib/queue')
      await sequenceQueue.add(
        'send-step',
        { enrollmentId, stepIndex: stepIndex + 1, leadId, campaignId },
        { delay }
      )
      await prisma.enrollment.update({
        where: { id: enrollmentId },
        data: {
          stepIndex:  stepIndex + 1,
          nextSendAt: new Date(Date.now() + delay),
        },
      })
    } else {
      await prisma.enrollment.update({ where: { id: enrollmentId }, data: { status: 'completed' } })
    }
  },
  { connection, concurrency: 5 }
)

// ─── Score Worker ─────────────────────────────────────────────────────────────

const scoreWorker = new Worker<ScoreJobData>(
  QUEUE_SCORE,
  async (job: Job<ScoreJobData>) => {
    const { leadId } = job.data
    await scoreLead(leadId)
    console.log(`[Worker] scored lead ${leadId}`)
  },
  { connection, concurrency: 10 }
)

// ─── Enrich Worker ────────────────────────────────────────────────────────────

const enrichWorker = new Worker<EnrichJobData>(
  QUEUE_ENRICH,
  async (job: Job<EnrichJobData>) => {
    const { leadId } = job.data
    const lead = await prisma.lead.findUnique({ where: { id: leadId } })
    if (!lead) return

    const enricher = getEnrichmentProvider()
    try {
      const result = await enricher.enrich({
        email:  lead.email  || undefined,
        domain: lead.domain || undefined,
      })
      await prisma.lead.update({
        where: { id: leadId },
        data: {
          firstName:    result.firstName   || lead.firstName,
          lastName:     result.lastName    || lead.lastName,
          title:        result.title       || lead.title,
          company:      result.company     || lead.company,
          domain:       result.domain      || lead.domain,
          industry:     result.industry    || lead.industry,
          companySize:  result.companySize || lead.companySize,
          linkedinUrl:  result.linkedinUrl || lead.linkedinUrl,
          location:     result.location    || lead.location,
          enrichmentRaw: result.raw as object || undefined,
          source:        lead.source,
        },
      })
      const { scoreQueue } = await import('@/lib/queue')
      await scoreQueue.add('score', { leadId })
      console.log(`[Worker] enriched lead ${leadId}`)
    } catch (e) {
      console.error(`[Worker] enrich failed for ${leadId}:`, e)
    }
  },
  { connection, concurrency: 5 }
)

// ─── Reply Poller (runs every 5 min via scheduler) ───────────────────────────

async function pollReplies() {
  const since = new Date(Date.now() - 6 * 60 * 1000) // last 6 min
  const emailCh = getEmailChannel()
  try {
    const replies = await emailCh.listReplies(since)
    for (const reply of replies) {
      // Match to existing thread
      const existing = await prisma.message.findFirst({
        where: { threadId: reply.threadId || reply.id },
      })
      if (existing) {
        await prisma.message.create({
          data: {
            leadId:     existing.leadId,
            campaignId: existing.campaignId || undefined,
            channel:    'email',
            direction:  'in',
            subject:    reply.subject,
            body:       reply.body,
            status:     'replied',
            threadId:   reply.threadId || reply.id,
            externalId: reply.id,
            repliedAt:  reply.receivedAt,
          },
        })
        await prisma.message.updateMany({
          where: { threadId: reply.threadId || reply.id, direction: 'out' },
          data:  { status: 'replied', repliedAt: reply.receivedAt },
        })
        await prisma.lead.update({
          where: { id: existing.leadId },
          data:  { status: 'replied' },
        })
        await prisma.activity.create({
          data: {
            leadId: existing.leadId,
            type:   'email_replied',
            payload: { subject: reply.subject },
          },
        })
      }
    }
  } catch (e) {
    console.error('[Worker] pollReplies failed:', e)
  }
}

// Poll replies every 5 minutes
setInterval(pollReplies, 5 * 60 * 1000)

console.log('[Worker] Started — sequence, score, enrich workers + reply poller active')

process.on('SIGTERM', async () => {
  await sequenceWorker.close()
  await scoreWorker.close()
  await enrichWorker.close()
  process.exit(0)
})
