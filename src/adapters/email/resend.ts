import type { EmailChannel, SendEmailParams, EmailMessage } from '@/types/integrations'
import { randomUUID } from 'crypto'

export class ResendEmailAdapter implements EmailChannel {
  name = 'resend'
  private apiKey: string
  private from: string

  constructor() {
    this.apiKey = process.env.RESEND_API_KEY || ''
    this.from   = process.env.RESEND_FROM_ADDRESS || ''
    if (!this.apiKey) throw new Error('RESEND_API_KEY is not set')
  }

  async send(params: SendEmailParams): Promise<{ messageId: string; threadId?: string }> {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        from:    this.from,
        to:      [params.to],
        subject: params.subject,
        html:    params.body,
        reply_to: params.replyTo,
      }),
    })
    if (!res.ok) {
      const err = await res.text()
      throw new Error(`Resend error ${res.status}: ${err}`)
    }
    const data = await res.json() as { id: string }
    return { messageId: data.id, threadId: params.threadId }
  }

  async listReplies(_since: Date): Promise<EmailMessage[]> {
    // Resend doesn't support inbound parsing in all plans — use webhook adapter
    return []
  }
}
