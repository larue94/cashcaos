import { NextRequest } from 'next/server'
import { requireOrg, ok } from '@/lib/api-helpers'
import { socialChannels } from '@/adapters/email'

export async function GET() {
  const { error } = await requireOrg()
  if (error) return error

  return ok({
    providers: {
      email:      process.env.EMAIL_PROVIDER      || 'mock',
      enrichment: process.env.ENRICHMENT_PROVIDER || 'mock',
      crm:        process.env.CRM_PROVIDER        || 'mock',
      llm:        process.env.LLM_PROVIDER        || 'anthropic',
    },
    socialChannels,
    models: {
      anthropic: process.env.ANTHROPIC_MODEL || 'claude-sonnet-4-6',
      openai:    process.env.OPENAI_MODEL    || 'gpt-4o',
    },
  })
}
