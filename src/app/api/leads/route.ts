import { NextRequest } from 'next/server'
import { prisma } from '@/lib/db'
import { requireOrg, ok, err } from '@/lib/api-helpers'
import { enrichQueue, scoreQueue } from '@/lib/queue'

export async function GET(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const { searchParams } = new URL(req.url)
  const tier   = searchParams.get('tier')
  const status = searchParams.get('status')
  const search = searchParams.get('search')
  const page   = Number(searchParams.get('page') || '1')
  const limit  = Math.min(Number(searchParams.get('limit') || '50'), 200)
  const skip   = (page - 1) * limit

  const where: Record<string, unknown> = { orgId }
  if (tier)   where.tier   = tier
  if (status) where.status = status
  if (search) {
    where.OR = [
      { firstName: { contains: search, mode: 'insensitive' } },
      { lastName:  { contains: search, mode: 'insensitive' } },
      { email:     { contains: search, mode: 'insensitive' } },
      { company:   { contains: search, mode: 'insensitive' } },
    ]
  }

  const [leads, total] = await Promise.all([
    prisma.lead.findMany({
      where,
      orderBy: { totalScore: 'desc' },
      skip,
      take: limit,
      include: { signals: { orderBy: { occurredAt: 'desc' }, take: 5 } },
    }),
    prisma.lead.count({ where }),
  ])

  return ok({ leads, total, page, limit })
}

export async function POST(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const body = await req.json()

  // Bulk CSV import
  if (Array.isArray(body)) {
    const created = await prisma.$transaction(
      (body as Record<string, string>[]).map((row) =>
        prisma.lead.create({
          data: {
            orgId: orgId!,
            firstName: row.firstName || row.first_name || '',
            lastName:  row.lastName  || row.last_name  || '',
            email:     row.email     || '',
            title:     row.title     || row.job_title   || '',
            company:   row.company   || '',
            domain:    row.domain    || row.email?.split('@')[1] || '',
            linkedinUrl: row.linkedinUrl || row.linkedin_url || '',
            source:    'csv',
          },
        })
      )
    )
    // Queue scoring for all
    await Promise.all(
      created.map((l) => scoreQueue.add('score', { leadId: l.id }))
    )
    return ok({ created: created.length }, 201)
  }

  // Single lead
  const lead = await prisma.lead.create({
    data: {
      orgId:       orgId!,
      firstName:   body.firstName   || '',
      lastName:    body.lastName    || '',
      email:       body.email       || '',
      title:       body.title       || '',
      company:     body.company     || '',
      domain:      body.domain      || body.email?.split('@')[1] || '',
      linkedinUrl: body.linkedinUrl || '',
      phone:       body.phone       || '',
      location:    body.location    || '',
      industry:    body.industry    || '',
      companySize: body.companySize || '',
      source:      body.source      || 'manual',
      tags:        body.tags        || [],
    },
  })

  await enrichQueue.add('enrich', { leadId: lead.id })
  await scoreQueue.add('score',   { leadId: lead.id })

  return ok(lead, 201)
}
