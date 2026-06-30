import { NextRequest } from 'next/server'
import { prisma } from '@/lib/db'
import { requireOrg, ok, err } from '@/lib/api-helpers'
import { extractIcpFromWebsite } from '@/adapters/llm'

export async function GET() {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const profiles = await prisma.icpProfile.findMany({
    where: { orgId: orgId! },
    orderBy: { createdAt: 'desc' },
  })
  return ok(profiles)
}

export async function POST(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const body = await req.json()

  // LLM-assisted extraction from URL
  if (body.websiteUrl && !body.description) {
    try {
      const raw = await extractIcpFromWebsite(body.websiteUrl)
      const parsed = JSON.parse(raw)
      body.description      = parsed.description      || ''
      body.targetTitles     = parsed.targetTitles     || []
      body.targetIndustries = parsed.targetIndustries || []
      body.companySizeMin   = parsed.companySizeMin   || null
      body.companySizeMax   = parsed.companySizeMax   || null
      body.keywords         = parsed.keywords         || []
    } catch {
      // fall through with partial data
    }
  }

  const profile = await prisma.icpProfile.create({
    data: {
      orgId:            orgId!,
      name:             body.name             || 'Default ICP',
      description:      body.description      || '',
      targetTitles:     body.targetTitles     || [],
      targetIndustries: body.targetIndustries || [],
      companySizeMin:   body.companySizeMin   || null,
      companySizeMax:   body.companySizeMax   || null,
      keywords:         body.keywords         || [],
      websiteUrl:       body.websiteUrl       || null,
      scoringWeights:   body.scoringWeights   || { fit: 60, intent: 40 },
    },
  })
  return ok(profile, 201)
}

export async function PUT(req: NextRequest) {
  const { error, orgId } = await requireOrg()
  if (error) return error

  const body = await req.json()
  if (!body.id) return err('id required')

  const profile = await prisma.icpProfile.updateMany({
    where: { id: body.id, orgId: orgId! },
    data: {
      name:             body.name,
      description:      body.description,
      targetTitles:     body.targetTitles,
      targetIndustries: body.targetIndustries,
      companySizeMin:   body.companySizeMin,
      companySizeMax:   body.companySizeMax,
      keywords:         body.keywords,
      scoringWeights:   body.scoringWeights,
      isActive:         body.isActive,
    },
  })
  return ok(profile)
}
