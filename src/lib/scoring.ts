import { prisma } from './db'
// Types inlined to avoid requiring generated Prisma client at type-check time
type Lead = { title?: string | null; company?: string | null; industry?: string | null; companySize?: string | null }
type Signal = { type: string; weight: number; occurredAt: Date }
type IcpProfile = {
  targetTitles: string[]; targetIndustries: string[]; companySizeMin?: number | null;
  companySizeMax?: number | null; keywords: string[]; scoringWeights: unknown; description: string
}

export type ScoredResult = {
  fitScore: number
  intentScore: number
  totalScore: number
  tier: 'Hot' | 'Warm' | 'Cold'
}

export function computeFitScore(lead: Lead, icp: IcpProfile): number {
  let score = 0
  let checks = 0

  const titleMatch =
    icp.targetTitles.length === 0 ||
    icp.targetTitles.some((tt: string) =>
      lead.title?.toLowerCase().includes(tt.toLowerCase())
    )
  score += titleMatch ? 25 : 0
  checks++

  const industryMatch =
    icp.targetIndustries.length === 0 ||
    icp.targetIndustries.some((ind: string) =>
      lead.industry?.toLowerCase().includes(ind.toLowerCase())
    )
  score += industryMatch ? 25 : 0
  checks++

  const kwMatch =
    icp.keywords.length === 0 ||
    icp.keywords.some(
      (kw: string) =>
        lead.company?.toLowerCase().includes(kw.toLowerCase()) ||
        lead.title?.toLowerCase().includes(kw.toLowerCase())
    )
  score += kwMatch ? 25 : 0
  checks++

  // Company size
  if (icp.companySizeMin || icp.companySizeMax) {
    const sizeMap: Record<string, number> = {
      '1-10': 5, '11-50': 30, '51-200': 125, '201-500': 350,
      '501-1000': 750, '1001-5000': 3000, '5001-10000': 7500, '10001+': 20000,
    }
    const emp = sizeMap[lead.companySize || ''] || 0
    const minOk = !icp.companySizeMin || emp >= icp.companySizeMin
    const maxOk = !icp.companySizeMax || emp <= icp.companySizeMax
    score += minOk && maxOk ? 25 : 0
  } else {
    score += 25
  }

  return Math.min(100, Math.round(score))
}

export function computeIntentScore(signals: Signal[], weights: Record<string, number>): number {
  if (signals.length === 0) return 0

  const defaultWeights: Record<string, number> = {
    website_visit:         20,
    competitor_engagement: 25,
    follows_company:       15,
    hiring:                20,
    tech_stack:            15,
    manual:                10,
    webhook:               10,
    ...weights,
  }

  let raw = 0
  for (const sig of signals) {
    raw += (defaultWeights[sig.type] || 10) * sig.weight
  }
  return Math.min(100, Math.round(raw))
}

export function compositeScore(
  fitScore: number,
  intentScore: number,
  scoringWeights: Record<string, number>
): number {
  const fw = (scoringWeights.fit ?? 60) / 100
  const iw = (scoringWeights.intent ?? 40) / 100
  return Math.min(100, Math.round(fitScore * fw + intentScore * iw))
}

export function toTier(total: number): 'Hot' | 'Warm' | 'Cold' {
  if (total >= 70) return 'Hot'
  if (total >= 40) return 'Warm'
  return 'Cold'
}

export async function scoreLead(leadId: string): Promise<ScoredResult> {
  const lead = await prisma.lead.findUniqueOrThrow({
    where: { id: leadId },
    include: { signals: true, org: { include: { icpProfiles: { where: { isActive: true } } } } },
  })

  const icp = lead.org.icpProfiles[0]
  if (!icp) {
    return { fitScore: 0, intentScore: 0, totalScore: 0, tier: 'Cold' }
  }

  const sw = icp.scoringWeights as Record<string, unknown> as Record<string, number>
  const signalWeights = sw.signals as unknown as Record<string, number> | undefined

  const fitScore    = computeFitScore(lead, icp)
  const intentScore = computeIntentScore(lead.signals, signalWeights || {})
  const totalScore  = compositeScore(fitScore, intentScore, sw)
  const tier        = toTier(totalScore)

  await prisma.lead.update({
    where: { id: leadId },
    data: { fitScore, intentScore, totalScore, tier },
  })

  return { fitScore, intentScore, totalScore, tier }
}
