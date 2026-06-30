import type { LlmProvider } from '@/types/integrations'
import { AnthropicAdapter } from './anthropic'
import { OpenAIAdapter }    from './openai'

export function getLlmProvider(): LlmProvider {
  switch (process.env.LLM_PROVIDER) {
    case 'openai': return new OpenAIAdapter()
    default:       return new AnthropicAdapter()
  }
}

// High-level helpers ─────────────────────────────────────────────────────────

export async function extractIcpFromWebsite(url: string, rawText?: string): Promise<string> {
  const llm = getLlmProvider()
  const content = rawText
    ? `Website content:\n${rawText}`
    : `Website URL: ${url}\n(No content fetched — describe based on the URL and domain.)`

  return llm.complete([
    {
      role: 'system',
      content: `You are a B2B sales strategist. Given a company's website, extract an Ideal Customer Profile (ICP).
Return a JSON object with:
- description: string (what they sell, 2–3 sentences)
- targetTitles: string[] (job titles they sell to)
- targetIndustries: string[] (industries)
- companySizeMin: number | null
- companySizeMax: number | null
- keywords: string[] (5-10 keywords describing their buyer)
Respond with ONLY valid JSON, no markdown.`,
    },
    { role: 'user', content },
  ])
}

export async function draftOutreachMessage(params: {
  leadName: string
  leadTitle?: string
  leadCompany?: string
  senderName: string
  icpDescription: string
  channel: string
  template: string
  stepNumber: number
}): Promise<string> {
  const llm = getLlmProvider()
  return llm.complete([
    {
      role: 'system',
      content: `You are an expert outbound sales copywriter. Write personalized, human, concise outreach messages.
Never be pushy or spammy. Keep emails under 150 words. Never use generic openers like "Hope this finds you well."`,
    },
    {
      role: 'user',
      content: `Personalize this ${params.channel} outreach template for the prospect below.

PROSPECT:
- Name: ${params.leadName}
- Title: ${params.leadTitle || 'Unknown'}
- Company: ${params.leadCompany || 'Unknown'}

SENDER CONTEXT (what we sell / ICP):
${params.icpDescription}

TEMPLATE (step ${params.stepNumber}):
${params.template}

Return only the final message body. No subject line. No preamble.`,
    },
  ])
}

export async function draftReply(params: {
  threadSummary: string
  icpDescription: string
  tone: string
}): Promise<string> {
  const llm = getLlmProvider()
  return llm.complete([
    {
      role: 'system',
      content: `You are an expert sales rep drafting a reply to an inbound email. Be helpful, brief, and move toward booking a call.`,
    },
    {
      role: 'user',
      content: `Context of our product/ICP:
${params.icpDescription}

Email thread so far:
${params.threadSummary}

Draft a reply. Tone: ${params.tone}. Max 100 words.`,
    },
  ])
}

export async function generateScoreRationale(params: {
  lead: Record<string, unknown>
  fitScore: number
  intentScore: number
  totalScore: number
  tier: string
  icpDescription: string
}): Promise<string> {
  const llm = getLlmProvider()
  return llm.complete([
    {
      role: 'system',
      content: `You are an AI sales analyst. Explain a lead's score in 2–3 sentences. Be specific about why they are Hot/Warm/Cold.`,
    },
    {
      role: 'user',
      content: `ICP: ${params.icpDescription}

Lead:
${JSON.stringify(params.lead, null, 2)}

Scores: Fit=${params.fitScore}, Intent=${params.intentScore}, Total=${params.totalScore}, Tier=${params.tier}

Explain the score concisely.`,
    },
  ])
}
