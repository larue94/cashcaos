import type { LlmProvider, LlmMessage } from '@/types/integrations'
import Anthropic from '@anthropic-ai/sdk'

export class AnthropicAdapter implements LlmProvider {
  name = 'anthropic'
  private client: Anthropic
  private model: string

  constructor() {
    const key = process.env.ANTHROPIC_API_KEY
    if (!key) throw new Error('ANTHROPIC_API_KEY is not set')
    this.client = new Anthropic({ apiKey: key })
    this.model  = process.env.ANTHROPIC_MODEL || 'claude-sonnet-4-6'
  }

  async complete(
    messages: LlmMessage[],
    opts?: { maxTokens?: number; temperature?: number }
  ): Promise<string> {
    const system = messages.find((m) => m.role === 'system')?.content
    const turns  = messages.filter((m) => m.role !== 'system').map((m) => ({
      role:    m.role as 'user' | 'assistant',
      content: m.content,
    }))

    const res = await this.client.messages.create({
      model:      this.model,
      max_tokens: opts?.maxTokens || 1024,
      system,
      messages:   turns,
    })

    return res.content
      .filter((b) => b.type === 'text')
      .map((b) => (b as { type: 'text'; text: string }).text)
      .join('')
  }
}
