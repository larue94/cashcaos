import type { LlmProvider, LlmMessage } from '@/types/integrations'
import OpenAI from 'openai'

export class OpenAIAdapter implements LlmProvider {
  name = 'openai'
  private client: OpenAI
  private model: string

  constructor() {
    const key = process.env.OPENAI_API_KEY
    if (!key) throw new Error('OPENAI_API_KEY is not set')
    this.client = new OpenAI({ apiKey: key })
    this.model  = process.env.OPENAI_MODEL || 'gpt-4o'
  }

  async complete(
    messages: LlmMessage[],
    opts?: { maxTokens?: number; temperature?: number }
  ): Promise<string> {
    const res = await this.client.chat.completions.create({
      model:       this.model,
      max_tokens:  opts?.maxTokens || 1024,
      temperature: opts?.temperature ?? 0.7,
      messages:    messages.map((m) => ({ role: m.role, content: m.content })),
    })
    return res.choices[0]?.message?.content || ''
  }
}
