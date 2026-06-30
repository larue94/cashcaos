import { NextRequest } from 'next/server'
import { prisma } from '@/lib/db'
import { requireOrg, ok, err } from '@/lib/api-helpers'
import { getEnrichmentProvider } from '@/adapters/enrichment'
import { scoreQueue } from '@/lib/queue'

export async function POST(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const { leadId } = await req.json()
  if (!leadId) return err('leadId required')

  const lead = await prisma.lead.findFirst({ where: { id: leadId, orgId: orgId! } })
  if (!lead) return err('Lead not found', 404)

  const enricher = getEnrichmentProvider()
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
    },
  })

  await scoreQueue.add('score', { leadId })

  return ok({ enriched: true, result })
}
