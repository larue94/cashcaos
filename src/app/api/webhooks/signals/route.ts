import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/db'
import { scoreQueue } from '@/lib/queue'
import { createHmac } from 'crypto'

// POST /api/webhooks/signals
// Body: { secret, leadId | email, type, source, payload, weight?, occurredAt? }
export async function POST(req: NextRequest) {
  const body = await req.json()

  // Verify shared secret
  const secret = process.env.WEBHOOK_SIGNAL_SECRET
  if (secret) {
    const provided = req.headers.get('x-webhook-secret') || body.secret
    if (provided !== secret) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
  }

  // Resolve lead
  let leadId: string | null = body.leadId || null
  if (!leadId && body.email) {
    const lead = await prisma.lead.findFirst({ where: { email: body.email } })
    leadId = lead?.id || null
  }
  if (!leadId) {
    return NextResponse.json({ error: 'Lead not found' }, { status: 404 })
  }

  const signal = await prisma.signal.create({
    data: {
      leadId,
      type:       body.type       || 'webhook',
      source:     body.source     || 'webhook',
      payload:    body.payload    || {},
      weight:     body.weight     ?? 1.0,
      occurredAt: body.occurredAt ? new Date(body.occurredAt) : new Date(),
    },
  })

  await scoreQueue.add('score', { leadId })

  return NextResponse.json({ ok: true, signalId: signal.id })
}
